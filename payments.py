import razorpay
from .config import settings

def client():
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

def create_order(amount_inr: float, receipt: str) -> dict:
    return client().order.create({"amount": int(amount_inr * 100), "currency": "INR",
                                  "receipt": receipt})

def verify_payment(order_id: str, payment_id: str, signature: str) -> bool:
    try:
        client().utility.verify_payment_signature({
            "razorpay_order_id": order_id, "razorpay_payment_id": payment_id,
            "razorpay_signature": signature})
        return True
    except razorpay.errors.SignatureVerificationError:
        return False

def verify_webhook(body: str, signature: str) -> bool:
    try:
        client().utility.verify_webhook_signature(body, signature, settings.razorpay_webhook_secret)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False