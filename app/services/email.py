from abc import ABC, abstractmethod
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self, to_email: str, subject: str, message: str
    ) -> tuple[bool, Optional[str]]:
        pass


class GmailProvider(EmailProvider):
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM

    def send(
        self, to_email: str, subject: str, message: str
    ) -> tuple[bool, Optional[str]]:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(message, "html", "utf-8"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True, None
        except Exception as e:
            return False, str(e)


class AWSSESSMTPProvider(EmailProvider):
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM

    def send(
        self, to_email: str, subject: str, message: str
    ) -> tuple[bool, Optional[str]]:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(message, "html", "utf-8"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True, None
        except Exception as e:
            return False, str(e)


class AWSSESProvider(EmailProvider):
    def __init__(self):
        self.region = settings.AWS_REGION
        self.from_email = settings.SMTP_FROM

    def send(
        self, to_email: str, subject: str, message: str
    ) -> tuple[bool, Optional[str]]:
        try:
            ses_client = boto3.client(
                "ses",
                region_name=self.region,
                aws_access_key_id=settings.AWS_SES_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SES_SECRET_KEY,
            )

            response = ses_client.send_email(
                Source=self.from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": message, "Charset": "UTF-8"}},
                },
            )

            return True, None
        except ClientError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)


class ConsoleProvider(EmailProvider):
    def send(
        self, to_email: str, subject: str, message: str
    ) -> tuple[bool, Optional[str]]:
        print(f"\n=== EMAIL ===")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Message: {message[:200]}...")
        print(f"============\n")
        return True, None


def get_email_provider() -> EmailProvider:
    provider = settings.EMAIL_PROVIDER.lower()

    if provider == "gmail":
        return GmailProvider()
    elif provider == "aws_ses_smtp":
        return AWSSESSMTPProvider()
    elif provider == "aws_ses":
        return AWSSESProvider()
    elif provider == "console":
        return ConsoleProvider()
    else:
        return GmailProvider()


def send_notification(
    db: Session,
    notification_type: str,
    recipient_email: str,
    recipient_phone: Optional[str],
    subject: str,
    message: str,
    scheduled_at: Optional = None,
) -> int:
    from app.models.models import NotificationQueue

    notification = NotificationQueue(
        notification_type=notification_type,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        subject=subject,
        message=message,
        provider=settings.EMAIL_PROVIDER,
        scheduled_at=scheduled_at,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification.id


def process_queue(db: Session, limit: int = 10) -> dict:
    from app.models.models import NotificationQueue

    pending = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.status == "pending",
            NotificationQueue.attempts < NotificationQueue.max_attempts,
        )
        .order_by(NotificationQueue.created_at)
        .limit(limit)
        .all()
    )

    provider = get_email_provider()
    processed = 0
    failed = 0

    for notif in pending:
        success, error = provider.send(
            notif.recipient_email,
            notif.subject or "ZenParking Notification",
            notif.message,
        )

        notif.attempts += 1

        if success:
            notif.status = "sent"
            notif.sent_at = func.now()
            processed += 1
        else:
            notif.last_error = error
            if notif.attempts >= notif.max_attempts:
                notif.status = "failed"
            failed += 1

        db.commit()

    return {"processed": processed, "failed": failed}
