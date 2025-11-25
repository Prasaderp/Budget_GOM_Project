import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Tuple
import logging
import re
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else False


class EmailService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_smtp_config(self):
        return {
            'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL', ''),
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        }
    
    @contextmanager
    def _get_smtp_connection(self):
        config = self._get_smtp_config()
        if not all([config['host'], config['user'], config['password'], config['from_email']]):
            raise ValueError("SMTP configuration incomplete")
        
        server = smtplib.SMTP(config['host'], config['port'])
        try:
            if config['use_tls']:
                server.starttls()
            server.login(config['user'], config['password'])
            yield server
        finally:
            server.quit()
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        if not validate_email(to_email):
            logger.warning(f"Invalid email address: {to_email}")
            return False
        
        try:
            config = self._get_smtp_config()
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config['from_email']
            msg['To'] = to_email
            
            if text_body:
                part1 = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(part1)
            
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part2)
            
            with self._get_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused for {to_email}: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}", exc_info=True)
            return False
    
    def send_batch_emails(
        self,
        recipients: List[Tuple[str, str, str, Optional[str]]]
    ) -> Tuple[int, int]:
        """
        Send batch emails using single SMTP connection.
        Returns (success_count, failure_count)
        recipients: List of (email, subject, html_body, text_body) tuples
        """
        if not recipients:
            return (0, 0)
        
        valid_recipients = [
            (email, subject, html_body, text_body)
            for email, subject, html_body, text_body in recipients
            if validate_email(email)
        ]
        
        if not valid_recipients:
            logger.warning("No valid email addresses in batch")
            return (0, len(recipients))
        
        success_count = 0
        failure_count = 0
        
        try:
            config = self._get_smtp_config()
            with self._get_smtp_connection() as server:
                for email, subject, html_body, text_body in valid_recipients:
                    try:
                        msg = MIMEMultipart('alternative')
                        msg['Subject'] = subject
                        msg['From'] = config['from_email']
                        msg['To'] = email
                        
                        if text_body:
                            part1 = MIMEText(text_body, 'plain', 'utf-8')
                            msg.attach(part1)
                        
                        part2 = MIMEText(html_body, 'html', 'utf-8')
                        msg.attach(part2)
                        
                        server.send_message(msg)
                        success_count += 1
                        logger.debug(f"Email sent to {email}")
                    except Exception as e:
                        failure_count += 1
                        logger.error(f"Failed to send email to {email}: {e}")
            
            logger.info(f"Batch email send complete: {success_count} succeeded, {failure_count} failed")
            return (success_count, failure_count)
            
        except Exception as e:
            logger.error(f"Batch email send failed: {e}", exc_info=True)
            return (success_count, failure_count + len(valid_recipients) - success_count)


def get_default_notification_preferences():
    return {
        "data_filling_period": True,
        "taluka_activation": True,
        "fiscal_year_changes": True
    }
