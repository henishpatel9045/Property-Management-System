from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from properties.models import Property, Tenant
from finance.models import RentObligation, Expense
from communications.models import Reminder
from django.db.models import Sum

@login_required
def dashboard(request):
    owner = request.user
    
    # Stats
    total_properties = Property.objects.filter(owner=owner).count()
    active_tenants = Tenant.objects.filter(owner=owner).count()
    
    # Financials
    # In a real app we'd filter by this month, etc.
    obligations = RentObligation.objects.filter(lease__property__owner=owner)
    
    total_expected = obligations.aggregate(Sum('expected_amount'))['expected_amount__sum'] or 0
    total_paid = obligations.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_overdue = total_expected - total_paid

    # Reminders
    pending_reminders = Reminder.objects.filter(lease__property__owner=owner, status='pending').count()

    # Get recent unpaid/partial rents for a quick view
    overdue_rents = obligations.filter(status__in=['unpaid', 'partial', 'adjusted']).order_by('due_date')[:5]

    # Expenses
    owner_expenses = Expense.objects.filter(property__owner=owner)
    total_expenses = owner_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    unpaid_expenses_count = owner_expenses.filter(is_paid=False).count()
    bond_deductible_count = owner_expenses.filter(deduct_from_bond=True).count()

    context = {
        'total_properties': total_properties,
        'active_tenants': active_tenants,
        'total_expected': total_expected,
        'total_overdue': total_overdue,
        'pending_reminders': pending_reminders,
        'overdue_rents': overdue_rents,
        'total_expenses': total_expenses,
        'unpaid_expenses_count': unpaid_expenses_count,
        'bond_deductible_count': bond_deductible_count,
    }
    return render(request, 'accounts/dashboard.html', context)
