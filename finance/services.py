from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db import transaction
from properties.models import Lease
from django.db.models import Sum
from finance.models import RentObligation, Payment, PaymentAllocation

def generate_rent_obligations_for_lease(lease: Lease, horizon_months: int = 12):
    """
    Generate rent obligations for a given lease up to a certain horizon from the start date
    or up to the lease end date, whichever is earlier.
    Assumes monthly, weekly, or fortnightly.
    """
    current_date = lease.start_date
    end_date = min(lease.end_date, lease.start_date + relativedelta(months=horizon_months))
    
    obligations = []
    
    # Simple logic: iterate and create dates.
    while current_date <= end_date:
        # Check if obligation already exists to avoid duplicates
        if not RentObligation.objects.filter(lease=lease, due_date=current_date).exists():
            obligations.append(
                RentObligation(
                    lease=lease,
                    due_date=current_date,
                    expected_amount=lease.rent_amount,
                    status='unpaid'
                )
            )
            
        # increment date based on frequency
        if lease.rent_frequency == 'weekly':
            current_date += relativedelta(weeks=1)
        elif lease.rent_frequency == 'fortnightly':
            current_date += relativedelta(weeks=2)
        elif lease.rent_frequency == 'monthly':
            # Optionally use lease.due_day if defined
            current_date += relativedelta(months=1)
        else:
            break
            
    if obligations:
        RentObligation.objects.bulk_create(obligations)

@transaction.atomic
def allocate_payment(payment: Payment, target_obligation: RentObligation = None):
    """
    Allocate a payment. If target_obligation is provided, allocate to it first.
    Then automatically allocate any remainder chronologically to the oldest unpaid/partial rent obligations.
    Prevents double allocation by dynamically computing total allocated amount.
    """
    allocated_total = payment.allocations.aggregate(total=Sum('amount_allocated'))['total'] or Decimal('0.00')
    remaining_payment = payment.amount - allocated_total

    if remaining_payment <= 0:
        return

    # Helper to allocate to a specific obligation
    def _allocate_to_obs(obs, current_remaining):
        if current_remaining <= 0:
            return current_remaining
            
        outstanding = obs.outstanding_amount
        if outstanding <= 0:
            return current_remaining
            
        allocation_amount = min(outstanding, current_remaining)
        
        # Create allocation
        PaymentAllocation.objects.create(
            payment=payment,
            obligation=obs,
            amount_allocated=allocation_amount
        )
        
        # Update obligation
        obs.amount_paid += allocation_amount
        if obs.amount_paid >= obs.expected_amount:
            obs.status = 'paid'
        else:
            obs.status = 'partial'
        obs.save()
        
        return current_remaining - allocation_amount

    # Allocate to target first if specified
    if target_obligation:
        if target_obligation.status in ['unpaid', 'partial']:
            remaining_payment = _allocate_to_obs(target_obligation, remaining_payment)

    if remaining_payment > 0:
        # Find active unpaid or partial obligations for this lease, ordered by due_date
        obligations = RentObligation.objects.filter(
            lease=payment.lease,
            status__in=['unpaid', 'partial']
        ).order_by('due_date')

        for obs in obligations:
            if remaining_payment <= 0:
                break
            remaining_payment = _allocate_to_obs(obs, remaining_payment)

    # Save any unallocated balance
    payment.unallocated_balance = remaining_payment
    payment.save()
