from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings

def home(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject', 'New Contact Form Submission')
        message = request.POST.get('message')
        
        if name and email and message:
            full_message = f"Message from {name} ({email}):\n\n{message}"
            try:
                send_mail(
                    subject=f"PropRMS Contact: {subject}",
                    message=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['henish.patel.au@gmail.com'],
                    fail_silently=False,
                )
                messages.success(request, "Your message has been sent successfully. We will get in touch with you shortly.")
            except Exception as e:
                messages.error(request, "An error occurred while sending your message. Please try again later.")
        else:
            messages.error(request, "Please fill in all required fields.")
            
        return redirect('home')
        
    return render(request, 'home.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_conditions(request):
    return render(request, 'terms.html')
