import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailService:
    """Service for sending emails via SMTP"""

    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email using SMTP.
        Returns True if successful, False otherwise.
        """
        # Get SMTP configuration from environment
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
        from_name = os.getenv("SMTP_FROM_NAME", "Coastline")

        # Check if SMTP is configured
        if not all([smtp_host, smtp_user, smtp_password]):
            print("⚠️  SMTP not configured - email not sent. Configure SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{from_name} <{from_email}>"
            message["To"] = to_email

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Connect to SMTP server and send
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(smtp_user, smtp_password)
                server.send_message(message)

            print(f"✅ Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def send_verification_email(email: str, token: str) -> bool:
        """Send email verification email"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        verify_link = f"{frontend_url}/verify-email?token={token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0f172a;">Welcome to Coastline!</h2>
                <p>Thank you for signing up. Please verify your email address to get the most out of your account.</p>
                <p style="margin: 30px 0;">
                    <a href="{verify_link}"
                       style="background-color: #0f172a; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Verify Email
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="color: #64748b; word-break: break-all; font-size: 14px;">{verify_link}</p>
                <p style="color: #64748b; font-size: 14px; margin-top: 32px;">
                    This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.
                </p>
            </body>
        </html>
        """

        return EmailService._send_email(email, "Verify Your Coastline Account", html_content)

    @staticmethod
    def send_password_reset_email(email: str, token: str) -> bool:
        """Send password reset email"""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0f172a;">Reset Your Password</h2>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_link}"
                       style="background-color: #0f172a; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Reset Password
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="color: #64748b; word-break: break-all; font-size: 14px;">{reset_link}</p>
                <p style="color: #64748b; font-size: 14px; margin-top: 32px;">
                    This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                </p>
            </body>
        </html>
        """

        return EmailService._send_email(email, "Reset Your Coastline Password", html_content)
