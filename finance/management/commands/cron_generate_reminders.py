from django.core.management.base import BaseCommand
from django.utils import timezone
from properties.models import Lease
from finance.models import RentObligation
from communications.models import AuditLog
from communications.utils import run_all_dynamic_rent_reminders

class Command(BaseCommand):
    help = 'Sends dynamic rent status emails to tenants for all outstanding rent amount till today.'

    def handle(self, *args, **kwargs):
        sent_count, skipped_count, error_count = run_all_dynamic_rent_reminders()
            
        self.stdout.write(self.style.SUCCESS(
            f"Cron complete. Sent: {sent_count}, Skipped: {skipped_count}, Errors: {error_count}"
        ))
