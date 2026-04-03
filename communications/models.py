from django.db import models
from django.conf import settings
from properties.models import Lease

class Reminder(models.Model):
    RECIPIENT_CHOICES = [
        ('tenant', 'Tenant'),
        ('owner', 'Owner'),
    ]
    
    TYPE_CHOICES = [
        ('rent_due', 'Rent Due'),
        ('rent_overdue', 'Rent Overdue'),
        ('lease_expiry', 'Lease Expiry'),
        ('bond_deduction', 'Bond Deduction Summary'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='reminders', blank=True, null=True)
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_CHOICES)
    recipient_email = models.EmailField()
    reminder_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    scheduled_send_time = models.DateTimeField()
    sent_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_reminder_type_display()} for {self.recipient_email} at {self.scheduled_send_time}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('rent_adjustment', 'Rent Adjustment'),
        ('partial_payment', 'Partial Payment'),
        ('bond_deduction', 'Bond Deduction'),
        ('lease_termination', 'Lease Termination'),
        ('expense_update', 'Expense Update'),
        ('document_upload', 'Document Upload'),
        ('reminder_sent', 'Reminder Sent'),
        ('manual_status_change', 'Manual Status Change'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} perform {self.get_action_display()} on {self.timestamp}"
