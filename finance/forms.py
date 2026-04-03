from django import forms
from .models import Payment, Expense, RentObligation
from properties.models import Lease, Tenant

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['lease', 'tenant', 'date_paid', 'amount', 'payment_method', 'reference']
        widgets = {
            'lease': forms.Select(attrs={'class': 'form-select'}),
            'tenant': forms.Select(attrs={'class': 'form-select'}),
            'date_paid': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if owner:
            self.fields['lease'].queryset = Lease.objects.filter(property__owner=owner)
            self.fields['tenant'].queryset = Tenant.objects.filter(owner=owner)

class RentObligationAdjustmentForm(forms.ModelForm):
    class Meta:
        model = RentObligation
        fields = ['expected_amount', 'manual_override_reason']
        widgets = {
            'expected_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'manual_override_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for adjustment (e.g. hardship discount)'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['property', 'lease', 'date_incurred', 'category', 'description', 'amount', 'payer', 'is_recoverable', 'deduct_from_bond', 'is_paid', 'is_recovered', 'notes']
        widgets = {
            'property': forms.Select(attrs={'class': 'form-select'}),
            'lease': forms.Select(attrs={'class': 'form-select'}),
            'date_incurred': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payer': forms.Select(attrs={'class': 'form-select'}),
            'is_recoverable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deduct_from_bond': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_recovered': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if owner:
            self.fields['property'].queryset = owner.properties.all()
            self.fields['lease'].queryset = Lease.objects.filter(property__owner=owner)

