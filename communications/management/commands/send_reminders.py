from django.core.management.base import BasePageCommand, BaseCommand
from django.utils import timezone
from communications.models import Reminder, AuditLog
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends pending email reminders that are scheduled for now or in the past.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        reminders = Reminder.objects.filter(
            status='pending',
            scheduled_send_time__lte=now
        )

        sent_count = 0
        failed_count = 0

        for reminder in reminders:
            try:
                # In a real app we'd configure actual SMTP settings.
                # Here we just print if console backend is used, or attempt to send.
                send_mail(
                    subject=reminder.subject,
                    message=reminder.body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@propertymaps.local'),
                    recipient_list=[reminder.recipient_email],
                    fail_silently=False,
                )
                
                reminder.status = 'sent'
                reminder.sent_time = now
                reminder.save()

                AuditLog.objects.create(
                    action='reminder_sent',
                    description=f"Sent {reminder.get_reminder_type_display()} reminder to {reminder.recipient_email}"
                )
                sent_count += 1
            except Exception as e:
                reminder.status = 'failed'
                reminder.error_message = str(e)
                reminder.save()
                failed_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Successfully processed reminders. {sent_count} sent, {failed_count} failed."))
