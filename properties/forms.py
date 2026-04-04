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

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput
    
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
            # If all were empty strings/None, return empty list
            if not any(result):
                return []
            return result
        else:
            return single_file_clean(data, initial)

class LeaseForm(forms.ModelForm):
    lease_documents = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True}),
        label="Attach Documents / Photos (Multiple allowed)"
    )

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
