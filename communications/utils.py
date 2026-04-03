import logging
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Reminder, AuditLog

logger = logging.getLogger(__name__)

def process_pending_reminders():
    """
    Finds all pending reminders that are scheduled for now or in the past
    and sends them using the configured email backend.
    """
    now = timezone.now()
    reminders = Reminder.objects.filter(
        status='pending',
        scheduled_send_time__lte=now
    )

    sent_count = 0
    failed_count = 0

    for reminder in reminders:
        try:
            # Send the email
            send_mail(
                subject=reminder.subject,
                message=reminder.body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proprms.com'),
                recipient_list=[reminder.recipient_email],
                fail_silently=False,
            )
            
            # Update reminder status
            reminder.status = 'sent'
            reminder.sent_time = now
            reminder.save()

            # Log the action
            AuditLog.objects.create(
                action='reminder_sent',
                description=f"Sent {reminder.get_reminder_type_display()} reminder to {reminder.recipient_email}"
            )
            sent_count += 1
            logger.info(f"Successfully sent reminder ID {reminder.id} to {reminder.recipient_email}")
            
        except Exception as e:
            reminder.status = 'failed'
            reminder.error_message = str(e)
            reminder.save()
            failed_count += 1
            logger.error(f"Failed to send reminder ID {reminder.id}: {str(e)}")
            
    return sent_count, failed_count
