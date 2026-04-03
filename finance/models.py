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

class Expense(models.Model):
    PAYER_CHOICES = [
        ('owner', 'Owner'),
        ('tenant', 'Tenant'),
        ('shared', 'Shared')
    ]
    
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    date_incurred = models.DateField()
    category = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payer = models.CharField(max_length=20, choices=PAYER_CHOICES, default='owner')
    is_recoverable = models.BooleanField(default=False)
    deduct_from_bond = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False, help_text="Has the owner paid this expense?")
    is_recovered = models.BooleanField(default=False, help_text="Has the tenant reimbursed the owner?")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.description} (${self.amount})"

class BondAccount(models.Model):
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name='bond_account')
    bond_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_received = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    final_settlement_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
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
    expense = models.ForeignKey(Expense, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    date = models.DateField()
    approved_by_owner = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} - {self.reason}"
