from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db import transaction
from properties.models import Lease
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
def allocate_payment(payment: Payment):
    """
    Allocate a payment automatically to the oldest unpaid/partial rent obligations.
    """
    # Find active unpaid or partial obligations for this lease, ordered by due_date
    obligations = RentObligation.objects.filter(
        lease=payment.lease,
        status__in=['unpaid', 'partial']
    ).order_by('due_date')

    remaining_payment = payment.amount
    
    for obs in obligations:
        if remaining_payment <= 0:
            break
            
        outstanding = obs.outstanding_amount
        if outstanding <= 0:
            continue
            
        allocation_amount = min(outstanding, remaining_payment)
        
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
        
        remaining_payment -= allocation_amount

    # Save any unallocated balance
    payment.unallocated_balance = remaining_payment
    payment.save()
