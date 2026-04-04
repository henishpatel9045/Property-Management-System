from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Owner
# Register your models here.

class OwnerAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Profile Settings', {'fields': ('phone_number', 'notification_preferences', 'google_credentials',)}),
    )
admin.site.register(Owner, OwnerAdmin)