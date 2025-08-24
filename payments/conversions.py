import requests
from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv()

def get_live_exchange_rate(to_currency='NGN', from_currency='USD'):
    """
    Fetch live conversion rate from `from_currency` to `to_currency`.
    Uses exchangerate-api.com free endpoint.
    """
    api_key = os.getenv('EXCHANGE_RATE_API_KEY')  # store your key in .env
    url = f"{os.getenv('CONVERSION_URL')}/{api_key}/pair/{from_currency}/{to_currency}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['result'] == 'success':
            print(Decimal(str(data['conversion_rate'])))
            return Decimal(str(data['conversion_rate']))
        else:
            # fallback
            return Decimal('1')
    except requests.RequestException:

        return Decimal('1')
