from django.contrib import admin
from .models import RentObligation, Payment, PaymentAllocation, Expense, BondAccount, BondDeduction

@admin.register(RentObligation)
class RentObligationAdmin(admin.ModelAdmin):
    list_display = ('lease', 'due_date', 'expected_amount', 'amount_paid', 'status')
    list_filter = ('status',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'amount', 'date_paid', 'unallocated_balance')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'payer', 'is_recoverable', 'is_paid')
    list_filter = ('payer', 'is_recoverable')

admin.site.register(BondAccount)
admin.site.register(BondDeduction)
admin.site.register(PaymentAllocation)
