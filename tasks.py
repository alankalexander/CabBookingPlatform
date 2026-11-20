import smtplib, threading
from email.message import EmailMessage
from pathlib import Path
from celery import Celery
from sqlmodel import Session
from .config import settings
from .db import engine
from .models import Ride, User

RECEIPTS = Path(__file__).resolve().parent.parent / "receipts"
celery_app = Celery("cab", broker=settings.redis_url or "memory://")

def build_receipt(ride_id: int) -> str:
    """PDF via WeasyPrint; falls back to an HTML file if its system libraries are missing."""
    RECEIPTS.mkdir(exist_ok=True)
    with Session(engine) as s:
        ride = s.get(Ride, ride_id)
    html = f"""<html><body style="font-family:sans-serif">
    <h1>CabGo - Ride Receipt #{ride.id}</h1>
    <p>Date: {ride.created_at:%d %b %Y %H:%M}</p>
    <p>Distance: {ride.distance_meters / 1000:.1f} km</p>
    <p><b>Total paid: &#8377;{ride.fare_actual}</b></p></body></html>"""
    try:
        from weasyprint import HTML
        path = RECEIPTS / f"receipt_{ride_id}.pdf"
        HTML(string=html).write_pdf(str(path))
    except Exception:
        path = RECEIPTS / f"receipt_{ride_id}.html"
        path.write_text(html, encoding="utf-8")
    return str(path)

def send_email(to: str, subject: str, body: str):
    """Real email if SMTP is set, otherwise the message is printed in the backend terminal."""
    try:
        if not settings.smtp_host:
            print(f"\n=== EMAIL (SMTP not configured) ===\nTo: {to}\nSubject: {subject}\n{body}\n===================================\n")
            return
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, settings.smtp_user, to
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, 587) as smtp:
            smtp.starttls(); smtp.login(settings.smtp_user, settings.smtp_pass); smtp.send_message(msg)
    except Exception as e:
        print("Email error:", e)

def queue_email(to: str, subject: str, body: str):
    threading.Thread(target=send_email, args=(to, subject, body), daemon=True).start()

def email_receipt(ride_id: int):
    try:
        path = Path(build_receipt(ride_id))
        if not settings.smtp_host:
            return                      # no SMTP: receipt just stays in backend/receipts
        with Session(engine) as s:
            rider = s.get(User, s.get(Ride, ride_id).rider_id)
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = f"Receipt for ride #{ride_id}", settings.smtp_user, rider.email
        msg.set_content("Thanks for riding with CabGo. Receipt attached.")
        sub = "pdf" if path.suffix == ".pdf" else "html"
        msg.add_attachment(path.read_bytes(), maintype="application", subtype=sub, filename=path.name)
        with smtplib.SMTP(settings.smtp_host, 587) as smtp:
            smtp.starttls(); smtp.login(settings.smtp_user, settings.smtp_pass); smtp.send_message(msg)
    except Exception as e:
        print("Receipt error:", e)

@celery_app.task
def send_receipt(ride_id: int):
    email_receipt(ride_id)

def dispatch_receipt(ride_id: int):
    if settings.use_celery:
        send_receipt.delay(ride_id)
    else:
        threading.Thread(target=email_receipt, args=(ride_id,), daemon=True).start()