from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from .models import Property, Tenant, Lease
from .forms import PropertyForm, TenantForm, LeaseForm
from finance.models import FinancialRecord, RentObligation
from django.db.models import Sum

# --- Property Views ---
class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

class PropertyDetailView(LoginRequiredMixin, DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property_obj = self.get_object()
        
        # Financials for this property
        financial_records = FinancialRecord.objects.filter(property=property_obj)
        context['total_income'] = financial_records.filter(transaction_type='incoming').aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_expenses'] = financial_records.filter(transaction_type='outgoing').aggregate(Sum('amount'))['amount__sum'] or 0
        context['unpaid_expenses'] = financial_records.filter(transaction_type='outgoing', is_paid=False).count()
        
        obligations = RentObligation.objects.filter(lease__property=property_obj, status__in=['unpaid', 'partial', 'adjusted'])
        context['total_arrears'] = sum(obs.outstanding_amount for obs in obligations)
        context['overdue_count'] = obligations.count()
        
        return context

class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

# --- Tenant Views ---
class TenantListView(LoginRequiredMixin, ListView):
    model = Tenant
    template_name = 'properties/tenant_list.html'
    context_object_name = 'tenants'

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

class TenantDetailView(LoginRequiredMixin, DetailView):
    model = Tenant
    template_name = 'properties/tenant_detail.html'
    context_object_name = 'tenant'

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

class TenantCreateView(LoginRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class TenantUpdateView(LoginRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user)

# --- Lease Views ---
class LeaseListView(LoginRequiredMixin, ListView):
    model = Lease
    template_name = 'properties/lease_list.html'
    context_object_name = 'leases'

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user).select_related('property', 'tenant')

class LeaseDetailView(LoginRequiredMixin, DetailView):
    model = Lease
    template_name = 'properties/lease_detail.html'
    context_object_name = 'lease'

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user)

class LeaseCreateView(LoginRequiredMixin, CreateView):
    model = Lease
    form_class = LeaseForm
    template_name = 'properties/lease_form.html'
    success_url = reverse_lazy('lease_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

class LeaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Lease
    form_class = LeaseForm
    template_name = 'properties/lease_form.html'
    success_url = reverse_lazy('lease_list')

    def get_queryset(self):
        return Lease.objects.filter(property__owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs
