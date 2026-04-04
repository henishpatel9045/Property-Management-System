import logging
from django.utils import timezone
from django.conf import settings
from .models import Reminder, AuditLog
from .email_service import send_styled_email


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
            # DYNAMIC RE-CALCULATION FOR RENT REMINDERS
            if reminder.reminder_type in ['rent_due', 'rent_overdue'] and reminder.lease:
                from finance.models import RentObligation
                import datetime
                
                target_date = timezone.localtime().date() + datetime.timedelta(days=2)
                past_obligations = RentObligation.objects.filter(
                    lease=reminder.lease,
                    status__in=['unpaid', 'partial', 'adjusted'],
                    due_date__lte=target_date
                )
                
                total_due = sum(past.outstanding_amount for past in past_obligations)
                
                if total_due <= 0:
                    # Cancel the reminder dynamically!
                    reminder.status = 'sent'
                    reminder.error_message = "Cancelled implicitly: tenant has balance of 0 securely verified at sending time."
                    reminder.save()
                    continue
                    
                # Rebuild subject and body entirely so we completely ignore any stale text in the database
                tenant = reminder.lease.tenant
                next_due_obs = past_obligations.last()
                current_due = next_due_obs.outstanding_amount if next_due_obs else 0
                due_date_str = next_due_obs.due_date.strftime('%b %d, %Y') if next_due_obs else ""
                missed_count = past_obligations.count() - 1
                
                if missed_count >= 5:
                    reminder.subject = f"URGENT: Rent Notice & Overdue Arrears for {reminder.lease.property.name}"
                    reminder.body = (
                        f"Dear {tenant.first_name},\n\nThis is an urgent notice regarding your tenancy.\n"
                        f"Your rent of ${current_due} is due on {due_date_str}.\n\n"
                        f"Our records indicate {missed_count} missed payment cycles.\n"
                        f"Your verified TOTAL AMOUNT DUE is: ${total_due:.2f}.\n\n"
                        f"Failure to address this immediately may result in lease termination."
                    )
                elif missed_count > 0:
                    reminder.subject = f"Rent Reminder & Arrears Notice - {reminder.lease.property.name}"
                    reminder.body = (
                        f"Dear {tenant.first_name},\n\nThis is a friendly reminder that your upcoming rent of ${current_due} is due on {due_date_str}.\n"
                        f"You also have a past-due balance.\n\n"
                        f"Your verified TOTAL AMOUNT DUE is: ${total_due:.2f}.\n\n"
                        f"Please arrange payment promptly."
                    )
                else:
                    reminder.subject = f"Upcoming Rent Reminder - {reminder.lease.property.name}"
                    reminder.body = (
                        f"Dear {tenant.first_name},\n\nThis is a friendly reminder that your rent of ${current_due} is due on {due_date_str}.\n\n"
                        f"Your verified TOTAL AMOUNT DUE is: ${total_due:.2f}.\n\n"
                        f"Thank you for being a great tenant!"
                    )

            # Send the styled email
            send_styled_email(
                subject=reminder.subject,
                text_body=reminder.body,
                recipient_list=[reminder.recipient_email]
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
