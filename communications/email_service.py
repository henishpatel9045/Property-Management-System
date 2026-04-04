from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import linebreaks

def send_styled_email(subject, text_body, recipient_list, title=None):
    if title is None:
        title = subject
        
    html_body = linebreaks(text_body)
    
    context = {
        'title': title,
        'body': html_body,
        'company_name': getattr(settings, 'COMPANY_NAME', 'PropRMS'),
    }
    
    html_message = render_to_string('communications/emails/base_email.html', context)
    
    send_mail(
        subject=subject,
        message=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proprms.com'),
        recipient_list=recipient_list,
        fail_silently=False,
        html_message=html_message
    )
