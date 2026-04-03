from django.contrib import admin

from .models import Reminder, AuditLog
# Register your models here.

class ReminderAdmin(admin.ModelAdmin):
    list_display = ('lease', 'reminder_type', 'scheduled_send_time', 'status', 'sent_time')
    list_filter = ('status', 'reminder_type', 'sent_time')
    search_fields = ('lease__property__address', 'recipient_email')
    readonly_fields = ('sent_time',)

class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'description')
    readonly_fields = ('timestamp',)

admin.site.register(Reminder, ReminderAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
