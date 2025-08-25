from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch
from decimal import Decimal
from payments.models import Payment

class PaymentAPITest(APITestCase):
    def setUp(self):
        self.valid_data = {
            'name': 'John Doe',
            'email': 'john@gmail.com',
            'phone_number': '08012345678',
            'amount': '100.00',       # as string
            'currency': 'USD',
            'amount_ngn': '153468',   # as string
            'country': 'United States',
            'state': 'NY',
            'reference':'test-ref-1234',
        }

    @patch('payments.conversions.get_live_exchange_rate')
    def test_create_payment_live_rate(self, mock_rate):
        mock_rate.return_value = Decimal('1500')
        url = reverse('payment-initiate')
        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.amount_received, Decimal('153545.10'))

    @patch('payments.serializers.get_live_exchange_rate')
    def test_create_payment_fallback_rate(self, mock_rate):
        mock_rate.return_value = None  # force fallback
        url = reverse('payment-initiate')
        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.first()
        # fallback rate from CURRENCY_RATES_TO_NGN
        self.assertEqual(payment.amount_received, Decimal('153500'))

    @patch('payments.views.requests.post')
    def test_paystack_initialization_mocked(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "status": True,
            "message": "Authorization URL",
            "data": {
                "authorization_url": "https://paystack.com/pay/1234",
                "reference": "test-ref-1234"
            }
}
        url = reverse('payment-initiate')
        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('payment_link', response.data)

    @patch('payments.views.requests.get')
    def test_paystack_verification_mocked(self, mock_get):
        # 1️⃣ Create a Payment object in the DB
        reference = 'test-ref-1234'
        Payment.objects.create(
            name='John Doe',
            email='john@gmail.com',
            phone_number='08012345678',
            amount=100,
            currency='USD',
            reference=reference,
            amount_received=Decimal('150000')
        )

        # 2️⃣ Mock the Paystack GET request
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": True,
            "data": {"status": "success", "amount": 10000, "currency": "NGN"}
        }

        # 3️⃣ Call the verification endpoint
        url = reverse('payment-verify', kwargs={'reference': reference})
        response = self.client.get(url)

        # 4️⃣ Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'successful')

    def test_list_payments(self):
        # create one payment manually
        Payment.objects.create(
            name='Jane Doe',
            email='jane@gmail.com',
            phone_number='08098765432',
            amount=100,
            currency='USD',
            amount_received=Decimal('150000')
        )
        url = reverse('payment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_payment_by_id(self):
        payment = Payment.objects.create(
            name='Jane Doe',
            email='jane@gmail.com',
            phone_number='08098765432',
            amount=100,
            currency='USD',
            amount_received=Decimal('150000')
        )
        url = reverse('payment-id', kwargs={'id': payment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Jane Doe')
