import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from properties.models import Tenant
from .utils import process_pending_reminders, run_all_dynamic_rent_reminders
from .telegram_service import send_telegram_message

logger = logging.getLogger(__name__)

@csrf_exempt
def register_telegram_user(request):
    """
    Endpoint to receive chat_id and phone_number from the home server listener.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        chat_id = data.get('chat_id')
        phone_number = str(data.get('phone_number', '')).replace('+', '').strip()
        secret = data.get('secret')

        if not chat_id or not phone_number or not secret:
            return JsonResponse({'error': 'Missing required fields.'}, status=400)

        # Authenticate request
        if secret != settings.TELEGRAM_INTERNAL_SECRET:
            logger.warning(f"Unauthorized registration attempt for chat_id: {chat_id}")
            return JsonResponse({'error': 'Unauthorized.'}, status=403)

        # Normalize phone number for matching (last 10 digits as a heuristic)
        # matching_tenant = Tenant.objects.filter(phone_number__icontains=phone_number[-10:]).first()
        # More robust match: try exact first, then suffix
        matching_tenant = Tenant.objects.filter(phone_number__icontains=phone_number[-10:]).first()

        if not matching_tenant:
            print("Tenant not found", phone_number)
            return JsonResponse({'error': 'Tenant not found.'}, status=404)

        # Update chat_id
        matching_tenant.telegram_chat_id = chat_id
        matching_tenant.save()

        # Send confirmation via Telegram
        success_msg = (
            f"🎉 Success! <b>{matching_tenant.first_name}</b>, your Telegram account is now linked to your PropRMS profile. "
            "You will receive rent reminders here automatically."
        )
        send_telegram_message(chat_id, success_msg)

        return JsonResponse({'status': 'success', 'message': f'Telegram linked for {matching_tenant.first_name}'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)
    except Exception as e:
        logger.error(f"Error in telegram registration view: {str(e)}")
        return JsonResponse({'error': 'Internal server error.'}, status=500)

@csrf_exempt
def cron_trigger_reminders(request):
    """
    Web-triggered view to run the pending reminders process.
    Requires a POST request with 'cron_key' and 'cron_secret'.
    """
    print("cron_trigger_reminders called")
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
