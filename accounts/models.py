from django.contrib.auth.models import AbstractUser
from django.db import models

class Owner(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    notification_preferences = models.JSONField(default=dict, blank=True, help_text="e.g. {'email_reminders': True}")
    google_credentials = models.JSONField(null=True, blank=True, help_text="Stored OAuth credentials for Google Drive")

    def __str__(self):
        return self.get_full_name() or self.username
