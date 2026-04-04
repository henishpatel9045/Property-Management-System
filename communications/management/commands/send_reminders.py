from django.core.management.base import BaseCommand
from communications.utils import process_pending_reminders

class Command(BaseCommand):
    help = 'Sends pending email reminders that are scheduled for now or in the past.'

    def handle(self, *args, **kwargs):
        sent_count, failed_count = process_pending_reminders()
        self.stdout.write(self.style.SUCCESS(f"Successfully processed reminders. {sent_count} sent, {failed_count} failed."))
