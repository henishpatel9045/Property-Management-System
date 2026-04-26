import openpyxl
import csv
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.core.paginator import Paginator
from django.core.mail import send_mail
from communications.email_service import send_styled_email
from django.conf import settings
from django.db.models import Q, Sum, F
from django.db import transaction
from django.http import StreamingHttpResponse
from propertymaps.gdrive_service import (
    upload_file_to_drive, download_file_stream, delete_file_from_drive,
    get_file_thumbnail_link, DriveQuotaExceededError, GoogleAuthRevokedError
)
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseRedirect

# ... (middle of file)

@login_required
def financial_attachment_thumbnail_view(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk, property__owner=request.user)
    if not record.drive_file_id:
        return redirect('static/img/default-file-icon.png')
        
    thumbnail_link = get_file_thumbnail_link(request.user, record.drive_file_id)
    if thumbnail_link:
        return HttpResponseRedirect(thumbnail_link)
    
    return redirect('static/img/default-file-icon.png')


from finance.models import RentObligation, Payment, PaymentAllocation, FinancialRecord, BondAccount
from properties.models import Lease, Property
from finance.forms import (
    PaymentForm, RentObligationAdjustmentForm,
    MarkRentPaidForm, FinancialRecordForm,
)
from finance.services import allocate_payment


# ─────────────────────────────────────────────
# LEDGER (Rent Obligations)
# ─────────────────────────────────────────────

@login_required
def ledger(request):
    qs = RentObligation.objects.filter(
        lease__property__owner=request.user,
        due_date__lte=date.today() + timedelta(days=28)
    ).select_related('lease__property', 'lease__tenant').order_by('-due_date')

    # Filters
    filter_property = request.GET.get('property', '')
    filter_status = request.GET.get('status', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')

    if filter_property:
        qs = qs.filter(lease__property__id=filter_property)
    if filter_status:
        qs = qs.filter(status=filter_status)
    if filter_date_from:
        qs = qs.filter(due_date__gte=filter_date_from)
    if filter_date_to:
        qs = qs.filter(due_date__lte=filter_date_to)

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    properties = Property.objects.filter(owner=request.user)
    status_choices = RentObligation.STATUS_CHOICES

    context = {
        'page_obj': page_obj,
        'obligations': page_obj,
        'properties': properties,
        'status_choices': status_choices,
        'filter_property': filter_property,
        'filter_status': filter_status,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
    }
    return render(request, 'finance/ledger.html', context)


@login_required
def export_ledger_excel(request):
    owner = request.user
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Rent Ledger"
    headers = [
        "Property", "Tenant First Name", "Tenant Last Name",
        "Due Date", "Expected Amount", "Amount Paid",
        "Outstanding", "Status", "Notes"
    ]
    sheet.append(headers)
    obligations = RentObligation.objects.filter(
        lease__property__owner=owner
    ).order_by('-due_date')
    for obs in obligations:
        sheet.append([
            obs.lease.property.name,
            obs.lease.tenant.first_name,
            obs.lease.tenant.last_name,
            obs.due_date.strftime("%Y-%m-%d"),
            float(obs.expected_amount),
            float(obs.amount_paid),
            float(obs.outstanding_amount),
            obs.get_status_display(),
            obs.notes,
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="rent_ledger.xlsx"'
    workbook.save(response)
    return response


class RentObligationAdjustmentView(LoginRequiredMixin, UpdateView):
    model = RentObligation
    form_class = RentObligationAdjustmentForm
    template_name = 'finance/obligation_adjustment_form.html'
    success_url = reverse_lazy('ledger')

    def get_queryset(self):
        return RentObligation.objects.filter(lease__property__owner=self.request.user)

    def form_valid(self, form):
        if form.instance.status == 'unpaid':
            form.instance.status = 'adjusted'
        return super().form_valid(form)


# ─────────────────────────────────────────────
# MARK RENT AS PAID
# ─────────────────────────────────────────────

@login_required
def mark_rent_paid(request, pk):
    obligation = get_object_or_404(
        RentObligation, pk=pk, lease__property__owner=request.user
    )
    if request.method == 'POST':
        form = MarkRentPaidForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount_paid']
            date_paid = form.cleaned_data['date_paid']
            payment_method = form.cleaned_data.get('payment_method', '')
            reference = form.cleaned_data.get('reference', '')
            notes = form.cleaned_data.get('notes', '')

            # Create the Payment record and allocate it
            payment = Payment.objects.create(
                lease=obligation.lease,
                tenant=obligation.lease.tenant,
                date_paid=date_paid,
                amount=amount,
                payment_method=payment_method,
                reference=reference,
            )
            allocate_payment(payment, target_obligation=obligation)

            # Create a linked FinancialRecord (incoming)
            FinancialRecord.objects.create(
                transaction_type='incoming',
                property=obligation.lease.property,
                lease=obligation.lease,
                rent_obligation=obligation,
                category='rent_payment',
                date=date_paid,
                amount=amount,
                description=f'Rent payment for period due {obligation.due_date.strftime("%d %b %Y")}',
                notes=notes,
                is_paid=True,
            )

            messages.success(request, f'Payment of ${amount} recorded successfully.')
            return redirect('ledger')
    else:
        form = MarkRentPaidForm(
            initial={
                'amount_paid': obligation.expected_amount,
                'date_paid': date.today().isoformat(),
            }
        )

    return render(request, 'finance/mark_rent_paid.html', {
        'form': form,
        'obligation': obligation,
    })


@login_required
@transaction.atomic
def revert_payment(request, pk):
    obligation = get_object_or_404(
        RentObligation, pk=pk, lease__property__owner=request.user
    )
    
    # Find the most recent allocation for this obligation
    last_allocation = obligation.allocations.select_related('payment').order_by('-created_at').first()
    
    if not last_allocation:
        messages.error(request, "No payments found for this obligation to revert.")
        return redirect('ledger')
        
    payment = last_allocation.payment
    
    if request.method == 'POST':
        # 1. Identify all obligations affected by this payment
        affected_obligations = list(RentObligation.objects.filter(allocations__payment=payment).distinct())
        
        # 2. Find and delete the matching FinancialRecord
        # We must filter by rent_obligation to avoid deleting other records 
        # with the same date/amount on the same lease.
        FinancialRecord.objects.filter(
            rent_obligation=obligation,
            lease=payment.lease,
            date=payment.date_paid,
            amount=payment.amount,
            transaction_type='incoming',
            category='rent_payment'
        ).delete()
        
        # 3. Delete the Payment (Allocations will cascade delete)
        payment.delete()
        
        # 4. Recalculate each affected obligation's amount_paid and status
        for obs in affected_obligations:
            # Re-fetch from DB to ensure it is fresh
            obs.refresh_from_db()
            total_allocated = obs.allocations.aggregate(total=Sum('amount_allocated'))['total'] or 0
            obs.amount_paid = total_allocated
            
            if obs.amount_paid <= 0:
                obs.status = 'unpaid'
            elif obs.amount_paid < obs.expected_amount:
                obs.status = 'partial'
            else:
                obs.status = 'paid'
            obs.save()
            
        messages.success(request, f"Payment of ${payment.amount} has been reverted.")
        return redirect('ledger')
        
    return render(request, 'finance/revert_confirm.html', {
        'obligation': obligation,
        'payment': payment,
    })


# ─────────────────────────────────────────────
# PAYMENT CREATE (legacy - kept for compatibility)
# ─────────────────────────────────────────────

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payment_form.html'
    success_url = reverse_lazy('ledger')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        allocate_payment(self.object)
        return response

@login_required
@transaction.atomic
def revert_financial_record(request, pk):
    record = get_object_or_404(
        FinancialRecord, pk=pk, property__owner=request.user
    )
    
    # If this is a rent payment linked to an obligation, we use the ledger revert logic
    obligation = record.rent_obligation
    
    if request.method == 'POST':
        if obligation:
            # 1. Find the payment that created this record
            # We look for a payment on the same date/amount for this lease
            payment = Payment.objects.filter(
                lease=record.lease,
                date_paid=record.date,
                amount=record.amount
            ).order_by('-created_at').first()
            
            if payment:
                affected_obligations = list(RentObligation.objects.filter(allocations__payment=payment).distinct())
                
                # Delete Payment (Allocations will cascade)
                payment.delete()
                
                # Recalculate affected obligations
                for obs in affected_obligations:
                    obs.refresh_from_db()
                    total_allocated = obs.allocations.aggregate(total=Sum('amount_allocated'))['total'] or 0
                    obs.amount_paid = total_allocated
                    
                    if obs.amount_paid <= 0:
                        obs.status = 'unpaid'
                    elif obs.amount_paid < obs.expected_amount:
                        obs.status = 'partial'
                    else:
                        obs.status = 'paid'
                    obs.save()

        # 2. Handle Google Drive Attachment deletion if exists
        if record.drive_file_id:
            try:
                delete_file_from_drive(request.user, record.drive_file_id)
            except Exception:
                pass

        # 3. Delete the financial record itself
        record.delete()
        
        messages.success(request, f"Financial record '{record.category}' for ${record.amount} has been reverted.")
        return redirect('financial_list')
        
    return render(request, 'finance/revert_financial_confirm.html', {
        'record': record,
        'is_rent_payment': obligation is not None
    })

# ─────────────────────────────────────────────
# FINANCIAL RECORDS (Unified Income + Expense)
# ─────────────────────────────────────────────

@login_required
def financial_list(request):
    qs = FinancialRecord.objects.filter(
        property__owner=request.user
    ).select_related('property', 'lease__tenant')

    # Filters
    filter_type = request.GET.get('type', '')
    filter_property = request.GET.get('property', '')
    filter_paid = request.GET.get('paid', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')

    if filter_type:
        qs = qs.filter(transaction_type=filter_type)
    if filter_property:
        qs = qs.filter(property__id=filter_property)
    if filter_paid == 'yes':
        qs = qs.filter(is_paid=True)
    elif filter_paid == 'no':
        qs = qs.filter(is_paid=False)
    if filter_date_from:
        qs = qs.filter(date__gte=filter_date_from)
    if filter_date_to:
        qs = qs.filter(date__lte=filter_date_to)

    # Totals (on filtered set, before pagination)
    total_incoming = qs.filter(transaction_type='incoming').aggregate(Sum('amount'))['amount__sum'] or 0
    total_outgoing = qs.filter(transaction_type='outgoing').aggregate(Sum('amount'))['amount__sum'] or 0

    # Export to CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_records.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Property', 'Category', 'Amount', 'Description', 'Paid', 'Notes'])
        for rec in qs:
            writer.writerow([
                rec.date, rec.get_transaction_type_display(),
                rec.property.name, rec.category,
                float(rec.amount), rec.description,
                'Yes' if rec.is_paid else 'No', rec.notes,
            ])
        return response

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    properties = Property.objects.filter(owner=request.user)
    context = {
        'page_obj': page_obj,
        'records': page_obj,
        'properties': properties,
        'filter_type': filter_type,
        'filter_property': filter_property,
        'filter_paid': filter_paid,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'total_incoming': total_incoming,
        'total_outgoing': total_outgoing,
        'net': total_incoming - total_outgoing,
    }
    return render(request, 'finance/financial_list.html', context)


@login_required
def financial_record_detail(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk, property__owner=request.user)
    return render(request, 'finance/financial_record_detail.html', {'record': record})


@login_required
def financial_record_create(request):
    if request.method == 'POST':
        form = FinancialRecordForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            record = form.save(commit=False)
            uploaded_file = request.FILES.get('upload_attachment')
            if uploaded_file:
                try:
                    file_id = upload_file_to_drive(
                        user=request.user,
                        file_obj=uploaded_file,
                        display_name=uploaded_file.name,
                        mime_type=uploaded_file.content_type
                    )
                    record.drive_file_id = file_id
                    record.drive_file_name = uploaded_file.name
                except DriveQuotaExceededError as e:
                    form.add_error('upload_attachment', str(e))
                    return render(request, 'finance/financial_record_form.html', {'form': form, 'action': 'Add'})
                except GoogleAuthRevokedError:
                    return redirect('google_required')
                except Exception as e:
                    form.add_error('upload_attachment', f"Upload failed: {str(e)}")
                    return render(request, 'finance/financial_record_form.html', {'form': form, 'action': 'Add'})
            record.save()
            messages.success(request, 'Financial record added successfully.')
            return redirect('financial_list')
    else:
        form = FinancialRecordForm(owner=request.user)

    return render(request, 'finance/financial_record_form.html', {
        'form': form,
        'action': 'Add',
    })


@login_required
def financial_record_update(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk, property__owner=request.user)
    old_file_id = record.drive_file_id
    
    if request.method == 'POST':
        form = FinancialRecordForm(request.POST, request.FILES, instance=record, owner=request.user)
        if form.is_valid():
            record_instance = form.save(commit=False)
            uploaded_file = request.FILES.get('upload_attachment')
            clear_attachment = form.cleaned_data.get('clear_attachment')
            
            if uploaded_file:
                try:
                    file_id = upload_file_to_drive(
                        user=request.user,
                        file_obj=uploaded_file,
                        display_name=uploaded_file.name,
                        mime_type=uploaded_file.content_type
                    )
                    
                    # Delete old file if a new one is taking its place
                    if old_file_id:
                        try:
                            delete_file_from_drive(request.user, old_file_id)
                        except Exception:
                            pass # We shouldn't fail the upload just because delete failed

                    record_instance.drive_file_id = file_id
                    record_instance.drive_file_name = uploaded_file.name
                except DriveQuotaExceededError as e:
                    form.add_error('upload_attachment', str(e))
                    return render(request, 'finance/financial_record_form.html', {'form': form, 'action': 'Edit', 'record': record})
                except GoogleAuthRevokedError:
                    return redirect('google_required')
                except Exception as e:
                    form.add_error('upload_attachment', f"Upload failed: {str(e)}")
                    return render(request, 'finance/financial_record_form.html', {'form': form, 'action': 'Edit', 'record': record})
            elif clear_attachment and old_file_id:
                try:
                    delete_file_from_drive(request.user, old_file_id)
                    record_instance.drive_file_id = None
                    record_instance.drive_file_name = None
                except GoogleAuthRevokedError:
                    return redirect('google_required')
                except Exception as e:
                    messages.error(request, f"Failed to delete old attachment: {str(e)}")

            record_instance.save()
            messages.success(request, 'Financial record updated.')
            return redirect('financial_record_detail', pk=pk)
    else:
        form = FinancialRecordForm(instance=record, owner=request.user)

    return render(request, 'finance/financial_record_form.html', {
        'form': form,
        'action': 'Edit',
        'record': record,
    })

@login_required
def financial_record_delete(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk, property__owner=request.user)
    if request.method == 'POST':
        if record.drive_file_id:
            try:
                delete_file_from_drive(request.user, record.drive_file_id)
            except GoogleAuthRevokedError:
                return redirect('google_required')
            except Exception as e:
                # We log it or just let them delete the record anyway
                pass
                
        record.delete()
        messages.success(request, 'Financial record successfully deleted.')
        return redirect('financial_list')
        
    return render(request, 'finance/financial_record_confirm_delete.html', {'record': record})

@login_required
def download_financial_attachment(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk, property__owner=request.user)
    if not record.drive_file_id:
        messages.error(request, 'No attachment found for this record.')
        return redirect('financial_record_detail', pk=pk)
        
    try:
        fh, filename, mime_type = download_file_stream(request.user, record.drive_file_id)
        response = StreamingHttpResponse(fh, content_type=mime_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except GoogleAuthRevokedError:
        return redirect('google_required')
    except Exception as e:
        messages.error(request, f"Failed to gracefully download file: {str(e)}")
        return redirect('financial_record_detail', pk=pk)


# ─────────────────────────────────────────────
# SETTLEMENT
# ─────────────────────────────────────────────

@login_required
def lease_settlement(request, pk):
    lease = get_object_or_404(Lease, pk=pk, property__owner=request.user)

    unpaid_obligations = RentObligation.objects.filter(
        lease=lease, 
        status__in=['unpaid', 'partial', 'adjusted'],
        due_date__lte=date.today()
    )
    total_arrears = sum(obs.outstanding_amount for obs in unpaid_obligations)

    # Outgoing financial records marked to deduct from bond
    deductible_records = FinancialRecord.objects.filter(
        lease=lease, transaction_type='outgoing', deduct_from_bond=True
    )
    total_deductions = sum(r.amount for r in deductible_records)

    bond_account = getattr(lease, 'bond_account', None)
    initial_bond = bond_account.bond_received if bond_account else lease.bond_required
    final_balance = initial_bond - total_arrears - total_deductions

    context = {
        'lease': lease,
        'unpaid_obligations': unpaid_obligations,
        'total_arrears': total_arrears,
        'deductible_records': deductible_records,
        'total_deductions': total_deductions,
        'initial_bond': initial_bond,
        'final_balance': final_balance,
        'bond_account': bond_account,
    }
    return render(request, 'finance/settlement.html', context)


@login_required
def finalize_settlement(request, pk):
    if request.method == 'POST':
        lease = get_object_or_404(Lease, pk=pk, property__owner=request.user)

        # Recalculate final balance
        unpaid_obligations = RentObligation.objects.filter(
            lease=lease, 
            status__in=['unpaid', 'partial', 'adjusted'],
            due_date__lte=date.today()
        )
        total_arrears = sum(obs.outstanding_amount for obs in unpaid_obligations)
        deductible_records = FinancialRecord.objects.filter(
            lease=lease, transaction_type='outgoing', deduct_from_bond=True
        )
        total_deductions = sum(r.amount for r in deductible_records)
        bond_account = getattr(lease, 'bond_account', None)
        initial_bond = bond_account.bond_received if bond_account else lease.bond_required
        final_balance = initial_bond - total_arrears - total_deductions

        # Mark lease as ended
        lease.status = 'ended'
        lease.save()

        # Close bond account
        if bond_account:
            bond_account.is_closed = True
            bond_account.final_settlement_amount = final_balance
            bond_account.save()

        messages.success(
            request,
            f'Settlement finalised. Lease marked as ended. '
            f'{"Bond refund" if final_balance >= 0 else "Tenant owes"}: ${abs(final_balance):.2f}'
        )
    return redirect('lease_settlement', pk=pk)


@login_required
def send_settlement_email(request, pk):
    if request.method == 'POST':
        lease = get_object_or_404(Lease, pk=pk, property__owner=request.user)
        tenant_email = lease.tenant.email

        if not tenant_email:
            messages.error(request, 'Tenant has no email address on record. Please update the tenant profile first.')
            return redirect('lease_settlement', pk=pk)

        # Recalculate for email
        unpaid_obligations = RentObligation.objects.filter(
            lease=lease, 
            status__in=['unpaid', 'partial', 'adjusted'],
            due_date__lte=date.today()
        )
        total_arrears = sum(obs.outstanding_amount for obs in unpaid_obligations)
        deductible_records = FinancialRecord.objects.filter(
            lease=lease, transaction_type='outgoing', deduct_from_bond=True
        )
        total_deductions = sum(r.amount for r in deductible_records)
        bond_account = getattr(lease, 'bond_account', None)
        initial_bond = bond_account.bond_received if bond_account else lease.bond_required
        final_balance = initial_bond - total_arrears - total_deductions

        subject = f'Lease End Settlement – {lease.property.name}'
        if final_balance >= 0:
            outcome = f'Bond Refund Due to You: ${final_balance:.2f}'
        else:
            outcome = f'Outstanding Amount Owed: ${abs(final_balance):.2f}'

        body = (
            f'Dear {lease.tenant.first_name},\n\n'
            f'Your lease for {lease.property.name} has been finalised.\n\n'
            f'Settlement Summary\n'
            f'──────────────────────\n'
            f'Bond Held:              ${initial_bond:.2f}\n'
            f'Rent Arrears Deducted:  -${total_arrears:.2f}\n'
            f'Expense Deductions:     -${total_deductions:.2f}\n'
            f'──────────────────────\n'
            f'{outcome}\n\n'
            f'Please contact your property manager if you have any questions.\n\n'
            f'Regards,\nPropRMS'
        )

        try:
            send_styled_email(
                subject=subject,
                text_body=body,
                recipient_list=[tenant_email]
            )
            messages.success(request, f'Settlement summary email sent to {tenant_email}.')
        except Exception as e:
            messages.error(request, f'Email could not be sent: {str(e)}')

    return redirect('lease_settlement', pk=pk)


@login_required
def send_rent_reminder_email(request, pk):
    """Send a pre-filled rent reminder email to the tenant for the given lease."""
    lease = get_object_or_404(Lease, pk=pk, property__owner=request.user)

    if request.method == 'POST':
        tenant_email = lease.tenant.email
        if not tenant_email:
            messages.error(request, 'Tenant has no email address on record.')
            return redirect('lease_detail', pk=pk)

        # Find the most recent unpaid/partial obligation
        next_due = RentObligation.objects.filter(
            lease=lease, status__in=['unpaid', 'partial']
        ).order_by('due_date').first()

        subject = f'Rent Reminder – {lease.property.name}'
        if next_due:
            due_info = (
                f'Your next rent payment is due on {next_due.due_date.strftime("%d %b %Y")}.\n'
                f'Amount Due: ${next_due.outstanding_amount:.2f}\n'
                f'(Expected: ${next_due.expected_amount:.2f}, Already Paid: ${next_due.amount_paid:.2f})\n'
            )
        else:
            due_info = 'Your rent account is up to date. Thank you!\n'

        body = (
            f'Dear {lease.tenant.first_name},\n\n'
            f'This is a friendly reminder regarding your tenancy at {lease.property.name}.\n\n'
            f'{due_info}\n'
            f'Please ensure payment is made by the due date to avoid any late fees.\n\n'
            f'Payment frequency: {lease.get_rent_frequency_display()}\n'
            f'Regular rent amount: ${lease.rent_amount:.2f}\n\n'
            f'If you have already made payment, please disregard this notice.\n\n'
            f'Regards,\nYour Property Manager'
        )

        try:
            send_styled_email(
                subject=subject,
                text_body=body,
                recipient_list=[tenant_email]
            )
            
            # --- TELEGRAM NOTIFICATION ---
            if lease.tenant.telegram_chat_id:
                from communications.telegram_service import send_telegram_message, format_styled_telegram_message
                
                tg_body = (
                    f"Dear {lease.tenant.first_name},\n\n"
                    f"This is a friendly reminder regarding your tenancy at <b>{lease.property.name}</b>.\n\n"
                    f"{due_info}\n"
                    f"Please ensure payment is made by the due date.\n\n"
                    f"If you've already paid, please disregard this notice."
                )
                
                styled_tg_msg = format_styled_telegram_message(
                    title="Rent Reminder",
                    body=tg_body
                )
                send_telegram_message(lease.tenant.telegram_chat_id, styled_tg_msg)

            messages.success(request, f'Rent reminder sent to {tenant_email} (and Telegram if linked).')
        except Exception as e:
            messages.error(request, f'Email could not be sent: {str(e)}')

        return redirect('lease_detail', pk=pk)

    # GET — show confirmation page
    return render(request, 'finance/send_reminder_confirm.html', {'lease': lease})
