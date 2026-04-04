from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.urls import reverse
from django.conf import settings
from properties.models import Property, Tenant
from finance.models import RentObligation, FinancialRecord
from communications.models import Reminder
from django.db.models import Sum
from .models import Owner
import os
import requests
import google_auth_oauthlib.flow
@login_required
def dashboard(request):
    owner = request.user
    
    if not owner.google_credentials:
        return redirect('google_required')
        
    # Stats
    total_properties = Property.objects.filter(owner=owner).count()
    active_tenants = Tenant.objects.filter(owner=owner).count()
    
    # Financials
    obligations = RentObligation.objects.filter(lease__property__owner=owner)
    
    total_expected = obligations.aggregate(Sum('expected_amount'))['expected_amount__sum'] or 0
    total_paid = obligations.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_overdue = total_expected - total_paid

    # Reminders
    pending_reminders = Reminder.objects.filter(lease__property__owner=owner, status='pending').count()

    # Get recent unpaid/partial rents for a quick view
    overdue_rents = obligations.filter(status__in=['unpaid', 'partial', 'adjusted']).order_by('due_date')[:5]

    # Unified Financial Records Stats
    financial_records = FinancialRecord.objects.filter(property__owner=owner)
    total_incoming = financial_records.filter(transaction_type='incoming').aggregate(Sum('amount'))['amount__sum'] or 0
    total_outgoing = financial_records.filter(transaction_type='outgoing').aggregate(Sum('amount'))['amount__sum'] or 0
    
    unpaid_outgoing_count = financial_records.filter(transaction_type='outgoing', is_paid=False).count()
    bond_deductible_count = financial_records.filter(deduct_from_bond=True).count()

    context = {
        'total_properties': total_properties,
        'active_tenants': active_tenants,
        'total_expected': total_expected,
        'total_overdue': total_overdue,
        'pending_reminders': pending_reminders,
        'overdue_rents': overdue_rents,
        'total_incoming': total_incoming,
        'total_outgoing': total_outgoing,
        'unpaid_expenses_count': unpaid_outgoing_count,
        'bond_deductible_count': bond_deductible_count,
    }
    return render(request, 'accounts/dashboard.html', context)


def get_google_oauth_flow(request):
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "project_id": settings.GOOGLE_OAUTH_PROJECT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET
        }
    }
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive"
    ]
    flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config, scopes=scopes)
    return flow

@login_required
def google_required(request):
    # If they already connected, redirect back to dashboard
    if request.user.google_credentials:
        return redirect('dashboard')
    return render(request, 'accounts/google_required.html')

@login_required
def google_login(request):
    if settings.DEBUG:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    flow = get_google_oauth_flow(request)
    flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    request.session['state'] = state
    request.session['code_verifier'] = flow.code_verifier
    return redirect(authorization_url)

@login_required
def google_callback(request):
    if settings.DEBUG:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
    state = request.session.get('state')
    flow = get_google_oauth_flow(request)
    flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    
    # Needs the code_verifier we generated in the first step
    code_verifier = request.session.get('code_verifier')
    if code_verifier:
        flow.code_verifier = code_verifier
    
    authorization_response = request.build_absolute_uri()
    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        # For debugging: let us see the actual error instead of hiding it
        from django.http import HttpResponse
        return HttpResponse(f"OAuth fetch failure: {str(e)}")
        
    credentials = flow.credentials
    
    # Get user email and profile info via googleapis
    session = requests.Session()
    response = session.get(
        'https://www.googleapis.com/oauth2/v1/userinfo',
        params={'access_token': credentials.token, 'alt': 'json'}
    )
    
    if response.status_code == 200:
        user_info = response.json()
        
        # Update user if fields are missing
        user_updated = False
        if not request.user.email and user_info.get('email'):
            request.user.email = user_info.get('email')
            user_updated = True
        
        if not request.user.first_name and user_info.get('given_name'):
            request.user.first_name = user_info.get('given_name')
            user_updated = True
            
        if not request.user.last_name and user_info.get('family_name'):
            request.user.last_name = user_info.get('family_name')
            user_updated = True
            
        if user_updated:
            request.user.save()
    
    # Associate the credentials directly with the currently logged-in user
    request.user.google_credentials = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes)
    }
    request.user.save()
    
    return redirect('dashboard')
