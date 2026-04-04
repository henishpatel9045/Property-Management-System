from django.urls import path
from . import views

urlpatterns = [
    path('properties/', views.PropertyListView.as_view(), name='property_list'),
    path('properties/add/', views.PropertyCreateView.as_view(), name='property_create'),
    path('properties/<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('properties/<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_update'),

    path('tenants/', views.TenantListView.as_view(), name='tenant_list'),
    path('tenants/add/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('tenants/<int:pk>/edit/', views.TenantUpdateView.as_view(), name='tenant_update'),

    path('leases/', views.LeaseListView.as_view(), name='lease_list'),
    path('leases/add/', views.LeaseCreateView.as_view(), name='lease_create'),
    path('leases/<int:pk>/', views.LeaseDetailView.as_view(), name='lease_detail'),
    path('leases/<int:pk>/edit/', views.LeaseUpdateView.as_view(), name='lease_update'),

    path('documents/<int:pk>/download/', views.download_lease_document, name='download_lease_document'),
    path('documents/<int:pk>/delete/', views.delete_lease_document, name='delete_lease_document'),
]
