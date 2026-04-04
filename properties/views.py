from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from .models import Property, Tenant, Lease, Document
from .forms import PropertyForm, TenantForm, LeaseForm
from finance.models import FinancialRecord, RentObligation
from django.db.models import Sum
from propertymaps.gdrive_service import (
    upload_file_to_drive, download_file_stream, delete_file_from_drive,
    DriveQuotaExceededError, GoogleAuthRevokedError
)
from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# --- Property Views ---
class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

class PropertyDetailView(LoginRequiredMixin, DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property_obj = self.get_object()
        
        # Financials for this property
        financial_records = FinancialRecord.objects.filter(property=property_obj)
        context['total_income'] = financial_records.filter(transaction_type='incoming').aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_expenses'] = financial_records.filter(transaction_type='outgoing').aggregate(Sum('amount'))['amount__sum'] or 0
        context['unpaid_expenses'] = financial_records.filter(transaction_type='outgoing', is_paid=False).count()
        
        obligations = RentObligation.objects.filter(lease__property=property_obj, status__in=['unpaid', 'partial', 'adjusted'])
        context['total_arrears'] = sum(obs.outstanding_amount for obs in obligations)
        context['overdue_count'] = obligations.count()
        
        return context

class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

# --- Tenant Views ---
class TenantListView(LoginRequiredMixin, ListView):
    model = Tenant
    template_name = 'properties/tenant_list.html'
    context_object_name = 'tenants'

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

class TenantDetailView(LoginRequiredMixin, DetailView):
    model = Tenant
    template_name = 'properties/tenant_detail.html'
    context_object_name = 'tenant'

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

class TenantCreateView(LoginRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class TenantUpdateView(LoginRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

# --- Lease Views ---
class LeaseListView(LoginRequiredMixin, ListView):
    model = Lease
    template_name = 'properties/lease_list.html'
    context_object_name = 'leases'

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user).select_related('property', 'tenant')

class LeaseDetailView(LoginRequiredMixin, DetailView):
    model = Lease
    template_name = 'properties/lease_detail.html'
    context_object_name = 'lease'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all().order_by('-uploaded_at')
        return context

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user)

class LeaseCreateView(LoginRequiredMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    template_name = 'properties/lease_form.html'
    success_url = reverse_lazy('lease_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        lease = self.object
        files = self.request.FILES.getlist('lease_documents')
        
        if files:
            path_array = ["PropertyMaps", lease.property.name, f"{lease.tenant.first_name} {lease.tenant.last_name}"]
            for f in files:
                try:
                    file_id = upload_file_to_drive(
                        user=self.request.user,
                        file_obj=f,
                        display_name=f.name,
                        mime_type=f.content_type,
                        path_array=path_array
                    )
                    Document.objects.create(
                        lease=lease,
                        property=lease.property,
                        title=f.name,
                        drive_file_id=file_id,
                        drive_file_name=f.name
                    )
                except DriveQuotaExceededError:
                    messages.error(self.request, "Google Drive full. Skipping remaining.")
                    break
                except GoogleAuthRevokedError:
                    messages.error(self.request, "Google Auth revoked.")
                    break
                except Exception as e:
                    messages.error(self.request, f"Upload error: {str(e)}")
                    
        return response

class LeaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Lease
    form_class = LeaseForm
    template_name = 'properties/lease_form.html'
    success_url = reverse_lazy('lease_list')

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        lease = self.object
        files = self.request.FILES.getlist('lease_documents')
        
        if files:
            path_array = ["PropertyMaps", lease.property.name, f"{lease.tenant.first_name} {lease.tenant.last_name}"]
            for f in files:
                try:
                    file_id = upload_file_to_drive(
                        user=self.request.user,
                        file_obj=f,
                        display_name=f.name,
                        mime_type=f.content_type,
                        path_array=path_array
                    )
                    Document.objects.create(
                        lease=lease,
                        property=lease.property,
                        title=f.name,
                        drive_file_id=file_id,
                        drive_file_name=f.name
                    )
                except DriveQuotaExceededError:
                    messages.error(self.request, "Google Drive full. Skipping remaining.")
                    break
                except GoogleAuthRevokedError:
                    messages.error(self.request, "Google Auth revoked.")
                    break
                except Exception as e:
                    messages.error(self.request, f"Upload error: {str(e)}")
                    
        return response

# --- Document File Views ---
@login_required
def download_lease_document(request, pk):
    doc = get_object_or_404(Document, pk=pk, lease__property__owner=request.user)
    if not doc.drive_file_id:
        messages.error(request, 'No attachment found.')
        return redirect('lease_detail', pk=doc.lease.id)
        
    try:
        fh, filename, mime_type = download_file_stream(request.user, doc.drive_file_id)
        response = StreamingHttpResponse(fh, content_type=mime_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except GoogleAuthRevokedError:
        return redirect('google_required')
    except Exception as e:
        messages.error(request, f"Failed to download file: {str(e)}")
        return redirect('lease_detail', pk=doc.lease.id)

@login_required
def delete_lease_document(request, pk):
    doc = get_object_or_404(Document, pk=pk, lease__property__owner=request.user)
    lease_id = doc.lease.id
    
    if request.method == 'POST':
        if doc.drive_file_id:
            try:
                delete_file_from_drive(request.user, doc.drive_file_id)
            except GoogleAuthRevokedError:
                return redirect('google_required')
            except Exception as e:
                pass
        doc.delete()
        messages.success(request, 'Document successfully deleted.')
        
    return redirect('lease_detail', pk=lease_id)
