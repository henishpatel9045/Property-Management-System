from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import linebreaks

def send_styled_email(subject, text_body, recipient_list, title=None, template_name='communications/emails/base_email.html', extra_context=None):
    if title is None:
        title = subject
        
    html_body = linebreaks(text_body)
    
    context = {
        'title': title,
        'body': html_body,
        'company_name': getattr(settings, 'COMPANY_NAME', 'PropRMS'),
    }
    if extra_context:
        context.update(extra_context)
    
    html_message = render_to_string(template_name, context)
    
    send_mail(
        subject=subject,
        message=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proprms.com'),
        recipient_list=recipient_list,
        fail_silently=False,
        html_message=html_message
    )
