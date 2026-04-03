from django import forms
from .models import Payment, FinancialRecord, RentObligation
from properties.models import Lease, Tenant, Property
from datetime import date


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
            'manual_override_reason': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3,
                       'placeholder': 'Reason for adjustment (e.g. hardship discount)'}
            ),
        }


class MarkRentPaidForm(forms.Form):
    amount_paid = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    date_paid = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    payment_method = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bank Transfer, Cash'})
    )
    reference = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BSB/Account, receipt #'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                     'placeholder': 'Any notes about this payment (optional)'})
    )


class FinancialRecordForm(forms.ModelForm):
    class Meta:
        model = FinancialRecord
        fields = [
            'transaction_type', 'property', 'lease', 'rent_obligation',
            'category', 'date', 'amount', 'description',
            'notes', 'attachment', 'is_paid', 'deduct_from_bond',
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type'}),
            'property': forms.Select(attrs={'class': 'form-select', 'id': 'id_property'}),
            'lease': forms.Select(attrs={'class': 'form-select', 'id': 'id_lease'}),
            'rent_obligation': forms.Select(attrs={'class': 'form-select', 'id': 'id_rent_obligation'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                                  'placeholder': 'Brief description of this record'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                           'placeholder': 'Additional notes (optional)'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deduct_from_bond': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        # Override category with the model's static choices
        self.fields['category'] = forms.ChoiceField(
            choices=FinancialRecord.CATEGORY_CHOICES,
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_category'})
        )
        self.fields['lease'].required = False
        self.fields['lease'].empty_label = '— No specific lease —'
        self.fields['rent_obligation'].required = False
        self.fields['rent_obligation'].empty_label = '— No linked obligation —'
        if owner:
            self.fields['property'].queryset = Property.objects.filter(owner=owner)
            self.fields['lease'].queryset = Lease.objects.filter(property__owner=owner)
            self.fields['rent_obligation'].queryset = RentObligation.objects.filter(
                lease__property__owner=owner
            ).select_related('lease__property', 'lease__tenant').order_by('-due_date')
        else:
            self.fields['property'].queryset = Property.objects.none()
            self.fields['lease'].queryset = Lease.objects.none()
            self.fields['rent_obligation'].queryset = RentObligation.objects.none()
