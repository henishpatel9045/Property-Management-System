from django import forms
from .models import Property, Tenant, Lease

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'address', 'property_type', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'property_type': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'emergency_contact', 'notes']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ['property', 'tenant', 'start_date', 'end_date', 'rent_amount', 'rent_frequency', 'due_day', 'grace_period_days', 'bond_required', 'status', 'terms', 'expenses_owner_paid_default']
        widgets = {
            'property': forms.Select(attrs={'class': 'form-select'}),
            'tenant': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'rent_frequency': forms.Select(attrs={'class': 'form-select'}),
            'due_day': forms.NumberInput(attrs={'class': 'form-control'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'bond_required': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expenses_owner_paid_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if owner:
            self.fields['property'].queryset = Property.objects.filter(owner=owner)
            self.fields['tenant'].queryset = Tenant.objects.filter(owner=owner)
