import openpyxl
from django.shortcuts import render
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, ListView
from django.shortcuts import render, get_object_or_404
from finance.models import RentObligation, Payment, Expense, BondAccount, BondDeduction
from properties.models import Lease
from finance.forms import PaymentForm, RentObligationAdjustmentForm, ExpenseForm

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payment_form.html'
    success_url = reverse_lazy('ledger')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

@login_required
def ledger(request):
    obligations = RentObligation.objects.filter(lease__property__owner=request.user).order_by('due_date')
    return render(request, 'finance/ledger.html', {'obligations': obligations})

@login_required
def export_ledger_excel(request):
    owner = request.user
    
    # Create an in-memory workbook
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Rent Ledger"

    # Define headers
    headers = [
        "Property", "Tenant First Name", "Tenant Last Name", 
        "Due Date", "Expected Amount", "Amount Paid", 
        "Outstanding", "Status", "Notes"
    ]
    sheet.append(headers)

    # Fetch data
    obligations = RentObligation.objects.filter(lease__property__owner=owner).order_by('-due_date')

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
            obs.notes
        ])

    # Save to HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'finance/expense_list.html'
    context_object_name = 'expenses'

    def get_queryset(self):
        return Expense.objects.filter(property__owner=self.request.user).order_by('-date_incurred')

class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense_form.html'
    success_url = reverse_lazy('expense_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

@login_required
def lease_settlement(request, pk):
    lease = get_object_or_404(Lease, pk=pk, property__owner=request.user)
    
    # Arrears
    unpaid_obligations = RentObligation.objects.filter(
        lease=lease,
        status__in=['unpaid', 'partial', 'adjusted']
    )
    total_arrears = sum(obs.outstanding_amount for obs in unpaid_obligations)

    # Expenses to deduct
    deductible_expenses = Expense.objects.filter(
        lease=lease,
        deduct_from_bond=True
    )
    total_deductions = sum(exp.amount for exp in deductible_expenses)

    bond_account = getattr(lease, 'bond_account', None)
    initial_bond = bond_account.bond_received if bond_account else lease.bond_required

    final_balance = initial_bond - total_arrears - total_deductions

    context = {
        'lease': lease,
        'unpaid_obligations': unpaid_obligations,
        'total_arrears': total_arrears,
        'deductible_expenses': deductible_expenses,
        'total_deductions': total_deductions,
        'initial_bond': initial_bond,
        'final_balance': final_balance,
        'bond_account': bond_account,
    }
    return render(request, 'finance/settlement.html', context)

