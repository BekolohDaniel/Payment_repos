from decimal import Decimal, ROUND_HALF_UP
from ipware import get_client_ip
import os
import requests
from rest_framework import serializers
from payments.models import Payment
from dotenv import load_dotenv
from .conversions import get_live_exchange_rate

load_dotenv()  # Load environment variables from a .env file if present

# Allowed email domains
ALLOWED_EMAIL_DOMAINS = ('company.com', 'gmail.com', 'yahoo.com')

# Country codes → currencies and names
COUNTRY_CURRENCY = {
    'NG': ('NGN', 'NIGERIA'),
    'US': ('USD', 'UNITED STATES'),
    'GB': ('GBP', 'UNITED KINGDOM'),
    'ZA': ('ZAR', 'SOUTH AFRICA'),
    'EU': ('EUR', 'EUROPEAN UNION'),
    'GH': ('GHS', 'GHANA'),
    'KE': ('KES', 'KENYA'),
    'CM': ('XAF', 'CAMEROON'),
}

# Rates for conversion to NGN
CURRENCY_RATES_TO_NGN = {
    'NGN': Decimal('1'),
    'USD': Decimal('1535'),
    'GBP': Decimal('1020'),
    'ZAR': Decimal('55'),
    'EUR': Decimal('900'),
    'GHS': Decimal('100'),
    'KES': Decimal('7'),
    'XAF': Decimal('2.78'),
}

PAYSTACK_SUPPORTED_CURRENCIES = set(CURRENCY_RATES_TO_NGN.keys())


class PaymentSerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField()
    amount_ngn = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'name', 'email', 'phone_number',
            'amount', 'currency', 'amount_ngn',
            'state', 'country',
            'status', 'created_at', 'reference'
        ]
        read_only_fields = ['status', 'created_at', 'id', 'currency', 'amount_ngn', 'reference']
        extra_kwargs = {'amount': {'min_value': 1}}

    # ---------- Validators ----------
    def validate_email(self, value):
        if not any(value.endswith(f"@{d}") for d in ALLOWED_EMAIL_DOMAINS):
            raise serializers.ValidationError(
                f"Email must be from the domains: {', '.join(ALLOWED_EMAIL_DOMAINS)}"
            )
        return value

    def validate_phone_number(self, value):
        if not value.isdigit() or not 9 <= len(value) <= 15:
            raise serializers.ValidationError("Phone number must be between 9 and 15 digits.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')

        # Normalize country input
        country_input = (attrs.get('country') or '').strip().upper()

        

        if country_input:
            # Match against known country codes or names
            match = None
            for code, (currency, name) in COUNTRY_CURRENCY.items():
                if country_input == code or country_input.lower() == name.lower():
                    match = code
                    break
            if not match:
                valid_countries = [f"{cur}: {name}" for cur, name in COUNTRY_CURRENCY.values()]
                raise serializers.ValidationError({
                    'country': f"Payments from '{attrs.get('country')}' are not supported. Supported countries are: {', '.join(valid_countries)}"
                })
            country_code = match
        else:
            # Try to detect via IP
            ip, _ = get_client_ip(request)
            country_code = 'NG'  # fallback
            try:
                if ip:
                    resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=3).json()
                    code = (resp.get('country') or '').upper()
                    if code in COUNTRY_CURRENCY:
                        country_code = code
            except requests.RequestException:
                pass


        currency, country_name = COUNTRY_CURRENCY[country_code]
        attrs['country'] = country_name
        attrs['currency'] = currency

        # Required basics
        for f in ['name', 'state', 'amount']:
            if not attrs.get(f):
                raise serializers.ValidationError({f: f"{f.capitalize()} is required."})
            
        
        # --- Live conversion to NGN ---
        amount = Decimal(attrs['amount'])
        # Try live rate first
        rate = get_live_exchange_rate(from_currency=currency, to_currency='NGN')
        if rate is None:
            # fallback to hardcoded rate
            rate = CURRENCY_RATES_TO_NGN.get(currency.upper(), Decimal('1'))
            attrs['amount_ngn'] = (amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            attrs['amount_ngn'] = amount
        
        attrs['amount_ngn'] = (amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return attrs

   # ---------- Representation helpers ----------
    def get_amount_ngn(self, obj):
        try:
            amount = Decimal(obj.amount)
            currency = (obj.currency or 'NGN').upper()
    
            if currency != 'NGN':
                # Try live rate first
                rate = get_live_exchange_rate(from_currency=currency, to_currency='NGN')
                if not rate:
                    # fallback to hardcoded rate
                    rate = CURRENCY_RATES_TO_NGN.get(currency, Decimal('1'))
            else:
                rate = Decimal('1')
    
            ngn = (amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return str(ngn)
    
        except Exception as e:
            print(f"⚠️ Error in get_amount_ngn: {e}")
            return None

    # ---------- Create ----------
    def create(self, validated_data):
        # Create payment record
        payment = Payment.objects.create(
            name=validated_data['name'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            amount=validated_data['amount'],
            currency=validated_data['currency'],
            state=validated_data['state'],
            country=validated_data['country'],
        )

        amount_ngn = Decimal(self.get_amount_ngn(payment))

        if payment.currency not in PAYSTACK_SUPPORTED_CURRENCIES:
            payment.status = 'failed'
            raise serializers.ValidationError({
                'currency': f"Currency '{payment.currency}' is not supported."
            })

        # Call Paystack initialize endpoint
        headers = {
            'Authorization': f'Bearer {os.getenv("TEST_SECRET_KEY")}',
            'Content-Type': 'application/json',
        }
        payload = {
            'email': payment.email,
            'amount': int(amount_ngn * 100),  # in kobo
            'reference': payment.reference,
            'currency': 'NGN',  # Paystack only accepts NGN for now
            'callback_url': f'https://payment-repos.onrender.com/api/v1/payment/verify/',  # Replace with your actual callback URL
            'metadata': {
                'name': payment.name,
                'phone_number': payment.phone_number,
                'original_amount': str(payment.amount),
                'original_currency': payment.currency,
                'country': payment.country,
                'state': payment.state,
            }
        }
        try:
            response = requests.post(
                os.getenv('URL'),
                json=payload,
                headers=headers,
                timeout=10
            )
            response_data = response.json()
            if response.status_code != 200 or not response_data.get('status'):
                raise Exception(response_data.get('message', 'Failed to initialize transaction with Paystack.'))

            auth_url = response_data['data'].get('authorization_url')
            if not auth_url:
                raise Exception("No authorization URL returned from Paystack.")

            # Store authorization URL for later use
            self._authorization_url = auth_url

            paystack_data = response_data['data']
            paystack_ref = paystack_data.get('reference')
            payment.reference = paystack_ref
            payment.amount_received = amount_ngn
            payment.save()

        except requests.RequestException as e:
            raise serializers.ValidationError(f"Error communicating with payment gateway: {str(e)}")
        except Exception as e:
            raise serializers.ValidationError(str(e))

        return payment


class PaymentVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['reference', 'status']
        read_only_fields = ['status']


    def validate_reference(self, value):
        if not Payment.objects.filter(reference=value).exists():
            raise serializers.ValidationError("Invalid reference. No such payment found.")
        return value

class PaymentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'name', 'country', 'state', 'reference', 'status', 'amount', 'amount_received', 'created_at']
        read_only_fields = ['id', 'name', 'country', 'state', 'reference', 'status', 'amount_received', 'created_at']


