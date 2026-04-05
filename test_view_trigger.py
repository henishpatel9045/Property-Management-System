import os
import django
import json
from django.test import RequestFactory
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'propertymaps.settings')
django.setup()

from communications.views import cron_trigger_reminders

def test_view_trigger():
    factory = RequestFactory()
    
    # Prepare mock data
    data = {
        'cron_key': settings.CRON_TRIGGER_KEY,
        'cron_secret': settings.CRON_TRIGGER_SECRET
    }
    
    # Create a POST request
    request = factory.post('/communications/email-reminders-cron', data=data)
    
    print("Triggering view...")
    response = cron_trigger_reminders(request)
    
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(json.loads(response.content), indent=2))

if __name__ == "__main__":
    test_view_trigger()
