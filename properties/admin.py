from django.contrib import admin
from .models import Property, Tenant, Lease, Document

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'property_type', 'is_active')
    list_filter = ('is_active',)

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'owner', 'email')

@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('property', 'tenant', 'status', 'start_date', 'end_date', 'rent_amount')
    list_filter = ('status', 'rent_frequency')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'lease', 'uploaded_at')
