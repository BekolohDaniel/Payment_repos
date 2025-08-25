**README section** 

---

# 💳 Django Payment Gateway API

Django REST API for processing and verifying payments, handling user payment creation, listing, and status checks with external payment gateway integration.

## 🚀 Features

* Create and manage payment requests.
* Verify payment status with external providers (e.g., Paystack, Flutterwave, etc.).
* Secure API endpoints with Django REST Framework.
* PostgreSQL database support.
* Automated testing via GitHub Actions.

## 📂 API Endpoints

| Method | Endpoint                | Description                  |
| ------ | ----------------------- | ---------------------------- |
| `POST` | `/api/payments/`        | Create a new payment request |
| `GET`  | `/api/payments/`        | List all payments            |
| `GET`  | `/api/payments/{id}/`   | Retrieve payment details     |
| `POST` | `/api/payments/verify/` | Verify payment status        |

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2️⃣ Create & Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file in the project root:

```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/testdb
PAYMENT_GATEWAY_API_KEY=your_gateway_api_key
```

### 5️⃣ Run Migrations

```bash
python manage.py migrate
```

### 6️⃣ Start Development Server

```bash
python manage.py runserver
```

Visit 👉 `http://127.0.0.1:8000/api/payments/`

## 🧪 Running Tests

```bash
python manage.py test
```

## ☁️ Deployment

This project is set up for deployment on **Render**.

* Add your environment variables in Render dashboard.
* Connect your GitHub repo.
* Deploy and test.

## 📜 License

MIT License © 2025
