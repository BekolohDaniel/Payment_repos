from django.urls import path
from payments.views import PaymentVerificationView, PaymentView, PaymentListAllTransactionView, PaymentIdView

urlpatterns = [
    path('payment/', PaymentView.as_view(), name='payment-initiate'),
    path('payment/verify/<str:reference>/', PaymentVerificationView.as_view(), name='payment-verify'),
    path('payments/', PaymentListAllTransactionView.as_view(), name='payment-list'),
    path('payment/<str:id>/', PaymentIdView.as_view(), name='payment-id')
]