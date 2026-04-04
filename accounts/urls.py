from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('login/google/', views.google_login, name='google_login'),
    path('login/google/callback/', views.google_callback, name='google_callback'),
    path('login/google/required/', views.google_required, name='google_required'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/accounts/login/'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
