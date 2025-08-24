from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
import os
import requests
from decimal import Decimal
from dotenv import load_dotenv

from payments.models import Payment
from .serializers import PaymentSerializer, PaymentVerificationSerializer, PaymentListSerializer

load_dotenv()  # Load environment variables from a .env file if present

class PaymentView(CreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        payment = serializer.save()  # Serializer handles Paystack call

        payment_data = PaymentSerializer(payment).data
        # Return payment data + authorization URL
        return Response(
            {
                "payment": payment_data,
                "payment_link": getattr(serializer, '_authorization_url', None)
            },
            status=status.HTTP_201_CREATED
        )
    

class PaymentVerificationView(RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentVerificationSerializer
    lookup_field = "reference"
    lookup_url_kwarg = "reference"


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()  # fetch payment by reference

        # Call Paystack verify endpoint
        headers = {
            'Authorization': f'Bearer {os.getenv("TEST_SECRET_KEY")}',
        }
        response = requests.get(
            f"{os.getenv('VERIFY_URL')}/{instance.reference}",
            headers=headers,
            timeout=10
        )

        response_data = response.json()
        if response.status_code != 200 or not response_data.get('status'):
            return Response(
                {"detail": "Failed to verify transaction with Paystack."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update payment status
        data = response_data.get('data', {})
        if data.get('status') == 'success':
            instance.status = 'successful'
            amount_paid = Decimal(data.get('amount', 0)) / 100  # kobo → naira
            instance.amount_received = amount_paid
        else:
            instance.status = 'failed'

        instance.save(update_fields=['status', 'amount_received'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentListAllTransactionView(ListAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentListSerializer

class PaymentIdView(RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentListSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'


