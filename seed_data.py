import os
import django
from datetime import date, timedelta
import random
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'propertymaps.settings')
django.setup()

from accounts.models import Owner
from properties.models import Property, Tenant, Lease
from finance.models import Payment, RentObligation, Expense
from communications.models import Reminder

def seed():
    # Make sure we have our admin owner
    owner, _ = Owner.objects.get_or_create(username='admin')
    if not _:
        owner.set_password('admin123')
        owner.save()

    print("Clearing old data...")
    Property.objects.all().delete()

    print("Creating properties and tenants...")
    p1 = Property.objects.create(owner=owner, name="Sunset Apartments - Unit 101", address="123 Sunset Blvd", property_type="Apartment")
    p2 = Property.objects.create(owner=owner, name="Oakwood House", address="456 Oakwood Avenue", property_type="Single Family")
    
    t1 = Tenant.objects.create(owner=owner, first_name="John", last_name="Doe", email="john.doe@example.com", phone_number="555-0100")
    t2 = Tenant.objects.create(owner=owner, first_name="Alice", last_name="Smith", email="alice.smith@example.com", phone_number="555-0200")

    print("Creating leases...")
    # Lease 1: Monthly rent
    l1 = Lease.objects.create(
        property=p1,
        tenant=t1,
        start_date=date.today() - timedelta(days=90),
        end_date=date.today() + timedelta(days=275),
        rent_amount=Decimal('1200.00'),
        rent_frequency='monthly',
        bond_required=Decimal('1200.00')
    )
    
    # Lease 2: Weekly rent
    l2 = Lease.objects.create(
        property=p2,
        tenant=t2,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=335),
        rent_amount=Decimal('500.00'),
        rent_frequency='weekly',
        bond_required=Decimal('2000.00')
    )

    print("Generating Rent Obligations via signals...")
    # The signals will auto-generate rent obligations.

    print("Creating payments...")
    Payment.objects.create(lease=l1, tenant=t1, date_paid=date.today() - timedelta(days=85), amount=Decimal('2400.00'), payment_method="Bank Transfer")
    Payment.objects.create(lease=l2, tenant=t2, date_paid=date.today() - timedelta(days=30), amount=Decimal('1000.00'), payment_method="Cash")

from finance.models import Payment, RentObligation, FinancialRecord

def run():
    # Existing code for Owner, Property, Tenant, Lease...
    # (Assuming the rest of the file is correct, just fixing context-based issue)
    
    # ... previous code ...
    
    print("Creating Financial Records...")
    FinancialRecord.objects.create(
        transaction_type='outgoing',
        property=p1,
        date=date.today()-timedelta(days=10),
        category="maintenance",
        description="Fix plumbing",
        amount=Decimal('150.00'),
        is_paid=True
    )
    
    print("Creating Reminder...")
    Reminder.objects.create(lease=l1, recipient_type='tenant', recipient_email=t1.email, reminder_type='rent_due', subject='Rent Due Tomorrow', body='Please pay your rent.', scheduled_send_time=django.utils.timezone.now())

    print("Seed complete.")

if __name__ == '__main__':
    seed()
