import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(to_email, subject, body):
    """
    Sends an email using SMTP.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Skipping email to {to_email} (No credentials): {subject}")
        return False

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8')) # utf-8 for Hebrew

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_daily_flash(user_email, summary_text):
    subject = "FinanceAI: עדכון יומי"
    return send_email(user_email, subject, summary_text)

def send_weekly_deep_dive(user_email, summary_text):
    subject = "FinanceAI: סקירה שבועית מעמיקה"
    return send_email(user_email, subject, summary_text)
