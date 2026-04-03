import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from properties.models import Lease
from finance.models import RentObligation
from communications.models import Reminder

class Command(BaseCommand):
    help = 'Generates rent reminders for obligations due in 2 days and calculates arrears.'

    def handle(self, *args, **kwargs):
        today = timezone.localtime().date()
        target_due_date = today + datetime.timedelta(days=2)
        
        # Find all unpaid/partial obligations due exactly in 2 days
        upcoming_obligations = RentObligation.objects.filter(
            due_date=target_due_date,
            status__in=['unpaid', 'partial', 'adjusted']
        )
        
        created_count = 0
        
        for obs in upcoming_obligations:
            lease = obs.lease
            tenant = lease.tenant
            
            # Check if tenant has an email
            if not tenant.email:
                continue
                
            # Filter past obligations to calculate arrears
            past_obligations = RentObligation.objects.filter(
                lease=lease,
                status__in=['unpaid', 'partial', 'adjusted'],
                due_date__lt=target_due_date
            ).order_by('due_date')
            
            arrears_amount = sum(past.outstanding_amount for past in past_obligations)
            missed_count = past_obligations.count()
            
            total_due = obs.outstanding_amount + arrears_amount
            
            # Build email subject and body
            if missed_count >= 5:
                subject = f"URGENT: Rent Notice & Overdue Arrears for {lease.property.name}"
                body = (
                    f"Dear {tenant.first_name},\n\n"
                    f"This is an urgent notice regarding your tenancy at {lease.property.name}.\n"
                    f"Your upcoming rent of ${obs.outstanding_amount} is due on {obs.due_date.strftime('%b %d, %Y')}.\n\n"
                    f"Our records indicate that you have missed {missed_count} previous payment cycles, "
                    f"resulting in an outstanding arrears balance of ${arrears_amount}.\n\n"
                    f"Your TOTAL AMOUNT DUE is: ${total_due}.\n\n"
                    f"Failure to address this immediately may result in lease termination. "
                    f"Please contact your property manager immediately."
                )
                reminder_type = 'rent_overdue'
            elif missed_count > 0:
                subject = f"Rent Reminder & Arrears Notice - {lease.property.name}"
                body = (
                    f"Dear {tenant.first_name},\n\n"
                    f"This is a friendly reminder that your upcoming rent of ${obs.outstanding_amount} is due on {obs.due_date.strftime('%b %d, %Y')}.\n\n"
                    f"You also have a past-due balance of ${arrears_amount}. "
                    f"Your TOTAL AMOUNT DUE is: ${total_due}.\n\n"
                    f"Please arrange payment promptly."
                )
                reminder_type = 'rent_overdue'
            else:
                subject = f"Upcoming Rent Reminder - {lease.property.name}"
                body = (
                    f"Dear {tenant.first_name},\n\n"
                    f"This is a friendly reminder that your rent of ${obs.outstanding_amount} is due on {obs.due_date.strftime('%b %d, %Y')}.\n\n"
                    f"Thank you for being a great tenant!"
                )
                reminder_type = 'rent_due'
                
            # Check if we already scheduled a reminder for this due date to prevent duplicate cron runs
            existing = Reminder.objects.filter(
                lease=lease, 
                reminder_type__in=['rent_due', 'rent_overdue'],
                scheduled_send_time__date=timezone.localtime().date()
            ).exists()
            
            if not existing:
                Reminder.objects.create(
                    lease=lease,
                    recipient_type='tenant',
                    recipient_email=tenant.email,
                    reminder_type=reminder_type,
                    subject=subject,
                    body=body,
                    scheduled_send_time=timezone.now()
                )
                created_count += 1
            
        self.stdout.write(self.style.SUCCESS(f"Generated {created_count} rent reminders."))
