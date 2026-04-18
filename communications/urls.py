from django.urls import path
from . import views

urlpatterns = [
    path('email-reminders-cron', views.cron_trigger_reminders),
    path('telegram/register/', views.register_telegram_user, name='telegram_register'),
]
