from django.contrib import admin
from .models import RentObligation, Payment, PaymentAllocation, FinancialRecord, BondAccount, BondDeduction


@admin.register(RentObligation)
class RentObligationAdmin(admin.ModelAdmin):
    list_display = ('lease', 'due_date', 'expected_amount', 'amount_paid', 'status')
    list_filter = ('status',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'amount', 'date_paid', 'unallocated_balance')


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'property', 'category', 'amount', 'date', 'is_paid')
    list_filter = ('transaction_type', 'is_paid', 'deduct_from_bond')
    search_fields = ('category', 'description', 'notes')


admin.site.register(BondAccount)
admin.site.register(BondDeduction)
admin.site.register(PaymentAllocation)
