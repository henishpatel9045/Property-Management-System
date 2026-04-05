import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .utils import process_pending_reminders, run_all_dynamic_rent_reminders

@csrf_exempt
def cron_trigger_reminders(request):
    """
    Web-triggered view to run the pending reminders process.
    Requires a POST request with 'cron_key' and 'cron_secret'.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    # Extract credentials from POST body
    cron_key = request.POST.get('cron_key')
    cron_secret = request.POST.get('cron_secret')

    # Fallback to check if the body is JSON
    if not cron_key or not cron_secret:
        try:
            data = json.loads(request.body)
            cron_key = data.get('cron_key')
            cron_secret = data.get('cron_secret')
        except (json.JSONDecodeError, AttributeError):
            pass

    # Basic credential validation
    if cron_key != settings.CRON_TRIGGER_KEY or cron_secret != settings.CRON_TRIGGER_SECRET:
        return JsonResponse({'error': 'Unauthorized: Invalid credentials.'}, status=403)

    # Process pending reminders (legacy/standard model)
    sent_count, failed_count = process_pending_reminders()
    
    # Process dynamic rent reminders (new system)
    dyn_sent, dyn_skipped, dyn_error = run_all_dynamic_rent_reminders()

    return JsonResponse({
        'status': 'success',
        'message': 'Reminder processing complete.',
        'standard_reminders': {
            'sent_count': sent_count,
            'failed_count': failed_count,
        },
        'dynamic_rent_reminders': {
            'sent_count': dyn_sent,
            'skipped_count': dyn_skipped,
            'error_count': dyn_error,
        },
        'total_sent': sent_count + dyn_sent
    })
