from django.urls import path
from . import views

urlpatterns = [
    # Ledger (rent obligations)
    path('ledger/', views.ledger, name='ledger'),
    path('ledger/export/', views.export_ledger_excel, name='export_ledger_excel'),
    path('obligation/<int:pk>/adjust/', views.RentObligationAdjustmentView.as_view(), name='obligation_adjust'),
    path('obligation/<int:pk>/mark-paid/', views.mark_rent_paid, name='mark_rent_paid'),

    # Payments (legacy)
    path('payments/add/', views.PaymentCreateView.as_view(), name='payment_create'),

    # Financial Records (unified)
    path('records/', views.financial_list, name='financial_list'),
    path('records/add/', views.financial_record_create, name='financial_record_create'),
    path('records/<int:pk>/', views.financial_record_detail, name='financial_record_detail'),
    path('records/<int:pk>/edit/', views.financial_record_update, name='financial_record_update'),

    # Settlement
    path('lease/<int:pk>/settlement/', views.lease_settlement, name='lease_settlement'),
    path('lease/<int:pk>/settlement/finalise/', views.finalize_settlement, name='finalize_settlement'),
    path('lease/<int:pk>/settlement/email/', views.send_settlement_email, name='send_settlement_email'),

    # Rent reminder email
    path('lease/<int:pk>/remind/', views.send_rent_reminder_email, name='send_rent_reminder'),
]
