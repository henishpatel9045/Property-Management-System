from django.urls import path
from . import views

urlpatterns = [
    path('ledger/', views.ledger, name='ledger'),
    path('payments/add/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('export/', views.export_ledger_excel, name='export_ledger_excel'),
    path('obligation/<int:pk>/adjust/', views.RentObligationAdjustmentView.as_view(), name='obligation_adjust'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('lease/<int:pk>/settlement/', views.lease_settlement, name='lease_settlement'),
]
