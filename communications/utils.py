import logging
from django.utils import timezone
from django.conf import settings
from .models import Reminder, AuditLog
from .email_service import send_styled_email
from .telegram_service import send_telegram_message, format_styled_telegram_message


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

            # --- TELEGRAM NOTIFICATION ---
            if reminder.lease and reminder.lease.tenant and reminder.lease.tenant.telegram_chat_id:
                try:
                    tg_body = reminder.body
                    # Simple HTML conversion for body (bolding property if possible)
                    if reminder.lease.property:
                        tg_body = tg_body.replace(reminder.lease.property.name, f"<b>{reminder.lease.property.name}</b>")
                    
                    styled_tg_msg = format_styled_telegram_message(
                        title=f"{reminder.get_reminder_type_display()} Notice",
                        body=tg_body
                    )
                    send_telegram_message(reminder.lease.tenant.telegram_chat_id, styled_tg_msg)
                except Exception as tg_e:
                    logger.error(f"Telegram background send failed for reminder {reminder.id}: {str(tg_e)}")

            # Log the action
            AuditLog.objects.create(
                action='reminder_sent',
                description=f"Sent {reminder.get_reminder_type_display()} reminder (Email & TG if linked) to {reminder.recipient_email}"
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


def send_dynamic_rent_status_email(lease):
    """
    Calculates all outstanding rent for a lease till today 
    and sends a styled email with a table of details.
    Bypasses the Reminder model.
    """
    from finance.models import RentObligation
    from .email_service import send_styled_email
    import datetime

    today = timezone.localtime().date()
    
    # Get all unpaid or partial obligations due today or in the past
    unpaid_obligations = RentObligation.objects.filter(
        lease=lease,
        status__in=['unpaid', 'partial', 'adjusted'],
        due_date__lte=today
    ).order_by('due_date')

    if not unpaid_obligations.exists():
        return False, "No outstanding rent due till today."

    total_due = sum(obs.outstanding_amount for obs in unpaid_obligations)
    
    # Prepare email details
    tenant = lease.tenant
    subject = f"Rent Status Update - {lease.property.name}"
    
    # Text body fallback
    text_body = f"Dear {tenant.first_name},\n\nYou have an outstanding rent balance of ${total_due:.2f} for {lease.property.name}.\n"
    text_body += "Please see the detailed table in the HTML version of this email."

    extra_context = {
        'tenant_name': f"{tenant.first_name} {tenant.last_name}",
        'property_name': lease.property.name,
        'today_date': today.strftime('%B %d, %Y'),
        'obligations': unpaid_obligations,
        'total_due': f"{total_due:.2f}",
        'payment_instructions': getattr(settings, 'PAYMENT_INSTRUCTIONS', None)
    }

    try:
        send_styled_email(
            subject=subject,
            text_body=text_body,
            recipient_list=[tenant.email],
            template_name='communications/emails/rent_status_table.html',
            extra_context=extra_context
        )
        
        # --- TELEGRAM NOTIFICATION ---
        if tenant.telegram_chat_id:
            tg_body = f"Dear {tenant.first_name},\n"
            tg_body += f"This is your consolidated statement for <b>{lease.property.name}</b> as of {today.strftime('%b %d, %Y')}.\n\n"
            
            # Simple Table using Monospace (pre)
            tg_body += "<pre>"
            tg_body += f"{'Date':<12} {'Due':>8} {'Paid':>8} {'Bal':>8}\n"
            tg_body += "-" * 40 + "\n"
            for obs in unpaid_obligations:
                date_str = obs.due_date.strftime('%b %d')
                tg_body += f"{date_str:<12} {float(obs.expected_amount):>8.2f} {float(obs.amount_paid):>8.2f} {float(obs.outstanding_amount):>8.2f}\n"
            tg_body += "-" * 40 + "\n"
            tg_body += f"{'TOTAL DUE':<28} ${total_due:>8.2f}\n"
            tg_body += "</pre>\n\n"
            
            tg_body += "<i>Please arrange payment promptly. Thank you!</i>"
            
            styled_tg_msg = format_styled_telegram_message(
                title="Rent Status Update",
                body=tg_body
            )
            
            send_telegram_message(tenant.telegram_chat_id, styled_tg_msg)

        # Log the action
        AuditLog.objects.create(
            action='reminder_sent', # Still using this action code for consistency
            description=f"Sent Dynamic Rent Status Notification (Email & TG if applicable) to {tenant.email} (Total: ${total_due:.2f})"
        )
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)


def run_all_dynamic_rent_reminders():
    """
    Main loop to run all dynamic rent status calculation and sends.
    Checks for duplicates today using AuditLog.
    Returns: (sent_count, skipped_count, error_count)
    """
    from properties.models import Lease
    from .models import AuditLog

    today = timezone.localtime().date()
    active_leases = Lease.objects.filter(status='active')
    
    sent_count = 0
    skipped_count = 0
    error_count = 0
    
    for lease in active_leases:
        # Check if we already sent a rent status update today for this lease
        # sent_today = AuditLog.objects.filter(
        #     action='reminder_sent',
        #     description__icontains=f"Sent Dynamic Rent Status Email to {lease.tenant.email}",
        #     timestamp__date=today
        # ).exists()
        
        # if sent_today:
        #     skipped_count += 1
        #     continue
            
        success, message = send_dynamic_rent_status_email(lease)
        
        if success:
            sent_count += 1
        else:
            if message == "No outstanding rent due till today.":
                skipped_count += 1
            else:
                error_count += 1
                logger.error(f"Error sending dynamic rent to {lease.tenant.email}: {message}")

def format_styled_whatsapp_message(title, body, footer=None):
    """
    Formats a message for WhatsApp with consistent PropRMS styling.
    Uses WhatsApp markdown (*bold*, _italic_, ```monospace```).
    """
    company_name = getattr(settings, 'COMPANY_NAME', 'PropRMS')
    today = timezone.localtime().strftime('%b %d, %Y')
    
    msg = f"🏢 *{company_name} | {title}*\n"
    msg += f"📅 _{today}_\n"
    msg += "─" * 20 + "\n\n"
    msg += body + "\n\n"
    msg += "─" * 20 + "\n"
    
    if footer:
        msg += f"_{footer}_\n"
    else:
        msg += f"_Regards,_\n_{company_name} Management_"
        
    return msg


def get_pending_whatsapp_reminders():
    """
    Gather everything that needs sending via WhatsApp.
    Currently focused on dynamic rent status reminders.
    Returns: List of {"phone": str, "message": str}
    """
    from properties.models import Lease
    from finance.models import RentObligation
    import datetime

    today = timezone.localtime().date()
    active_leases = Lease.objects.filter(status='active').select_related('tenant', 'property')
    
    reminders = []
    
    for lease in active_leases:
        tenant = lease.tenant
        if not tenant.phone_number:
            continue
            
        unpaid_obligations = RentObligation.objects.filter(
            lease=lease,
            status__in=['unpaid', 'partial', 'adjusted'],
            due_date__lte=today
        ).order_by('due_date')

        if not unpaid_obligations.exists():
            continue

        total_due = sum(obs.outstanding_amount for obs in unpaid_obligations)
        
        # Build Body
        body = f"Dear {tenant.first_name},\n"
        body += f"This is your consolidated statement for *{lease.property.name}* as of {today.strftime('%b %d, %Y')}.\n\n"
        
        # WhatsApp Mobile-Friendly List (replacing strict table)
        for obs in unpaid_obligations:
            date_str = obs.due_date.strftime('%b %d, %Y')
            body += f"• *{date_str}*: ${float(obs.outstanding_amount):.2f} due "
            if obs.amount_paid > 0:
                body += f"_(Paid: ${float(obs.amount_paid):.2f})_\n"
            else:
                body += "\n"
        
        body += f"\n💰 *TOTAL OUTSTANDING: ${total_due:.2f}*\n\n"
        
        body += "_Please arrange payment promptly. Thank you!_"
        
        styled_msg = format_styled_whatsapp_message(
            title="Rent Status Update",
            body=body
        )
        
        # Clean phone number (remove +, spaces)
        clean_phone = str(tenant.phone_number).replace('+', '').replace(' ', '').strip()
        
        # Basic sanity check
        if len(clean_phone) >= 10:
            reminders.append({
                "phone": f"+{clean_phone}", # Ensure + is there for WhatsApp
                "message": styled_msg
            })
                
    return reminders
