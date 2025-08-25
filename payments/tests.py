from decimal import Decimal
from unittest.mock import patch, Mock
from django.urls import reverse
from rest_framework.test import APITestCase
from payments.models import Payment

class PaymentAPITest(APITestCase):
    def setUp(self):
        self.valid_data = {
            'name': 'John Doe',
            'email': 'john@gmail.com',
            'phone_number': '08012345678',
            'amount': '100.00',       # string to match serializer input
            'currency': 'USD',
            'amount_ngn': '153468',   # string
            'country': 'United States',
            'state': 'NY',
            'reference': 'test-ref-1234',
        }

    # Test creating payment using live exchange rate
    @patch('payments.serializers.get_live_exchange_rate')
    @patch('payments.serializers.requests.post')
    def test_create_payment_live_rate(self, mock_post, mock_rate):
        mock_rate.return_value = Decimal('1535.451')  # mocked live rate

        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": True, "data": {"authorization_url":"http://fake","reference":"TEST123"}}
        )

        url = reverse('payment-initiate')
        response = self.client.post(url, self.valid_data, format='json')

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.first()
        expected = Decimal(self.valid_data['amount']) * mock_rate.return_value
        self.assertEqual(payment.amount_received, expected)

    # Test creating payment using fallback exchange rate
    @patch('payments.serializers.get_live_exchange_rate')
    @patch('payments.serializers.requests.post')
    def test_create_payment_fallback_rate(self, mock_post, mock_rate):
        mock_rate.return_value = Decimal('1535.451')  # fallback rate

        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": True, "data": {"authorization_url":"http://fake","reference":"TEST456"}}
        )

        url = reverse('payment-initiate')
        response = self.client.post(url, self.valid_data, format='json')

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.first()
        expected = Decimal(self.valid_data['amount']) * mock_rate.return_value
        self.assertEqual(payment.amount_received, expected)

    # Test Paystack payment initialization
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

    # Test Paystack payment verification
    @patch('payments.views.requests.get')
    def test_paystack_verification_mocked(self, mock_get):
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

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": True,
            "data": {"status": "success", "amount": 10000, "currency": "NGN"}
        }

        url = reverse('payment-verify', kwargs={'reference': reference})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'successful')

    # Test listing all payments
    def test_list_payments(self):
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

    # Test getting a payment by ID
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
