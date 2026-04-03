from django.db import models
from django.conf import settings
from properties.models import Property, Tenant, Lease


class RentObligation(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
        ('adjusted', 'Adjusted'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='rent_obligations')
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    notes = models.TextField(blank=True)
    manual_override_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def outstanding_amount(self):
        return self.expected_amount - self.amount_paid

    def __str__(self):
        return f"{self.lease} - Due {self.due_date} (${self.expected_amount})"


class Payment(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='payments')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    date_paid = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    unallocated_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} from {self.tenant} on {self.date_paid}"


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    obligation = models.ForeignKey(RentObligation, on_delete=models.CASCADE, related_name='allocations')
    amount_allocated = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class FinancialRecord(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ]

    CATEGORY_CHOICES = [
        # Incoming
        ('rent_payment', 'Rent Payment'),
        ('bond_receipt', 'Bond Receipt'),
        ('reimbursement', 'Reimbursement from Tenant'),
        ('other_incoming', 'Other Income'),
        # Outgoing
        ('council_rates', 'Council Rates / Property Tax'),
        ('insurance', 'Insurance'),
        ('maintenance', 'Maintenance & Repairs'),
        ('strata_fees', 'Strata / Body Corporate Fees'),
        ('agency_fees', 'Agency / Management Fees'),
        ('water_rates', 'Water Rates'),
        ('cleaning', 'Cleaning'),
        ('other_outgoing', 'Other Expense'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='financial_records')
    lease = models.ForeignKey(
        Lease, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_records'
    )
    rent_obligation = models.ForeignKey(
        RentObligation, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_records'
    )
    category = models.CharField(max_length=100)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='financial_records/', null=True, blank=True)
    is_paid = models.BooleanField(
        default=False,
        help_text="For outgoing: has the owner paid this? For incoming: has payment been received?"
    )
    deduct_from_bond = models.BooleanField(
        default=False,
        help_text="Outgoing only: deduct this amount from bond at lease end settlement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} – {self.category} – ${self.amount}"


class BondAccount(models.Model):
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name='bond_account')
    bond_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_received = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    final_settlement_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_deductions_total(self):
        return sum(d.amount for d in self.deductions.all())

    @property
    def current_balance(self):
        return self.bond_received - self.get_deductions_total

    def __str__(self):
        return f"Bond for {self.lease}"


class BondDeduction(models.Model):
    bond_account = models.ForeignKey(BondAccount, on_delete=models.CASCADE, related_name='deductions')
    financial_record = models.ForeignKey(
        FinancialRecord, on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    date = models.DateField()
    approved_by_owner = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} – {self.reason}"
