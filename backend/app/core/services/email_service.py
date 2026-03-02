"""Email service for sending transactional emails."""

import logging
from email.message import EmailMessage
from typing import Optional

from aiosmtplib import SMTP

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails using SMTP."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email asynchronously.
        
        Args:
            to_email: Full recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Optional plain text body content
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Se as credenciais não estiverem configuradas, simular no ambiente de dev.
        # Mas avisando no console.
        if not settings.smtp_username or not settings.smtp_password:
            logger.warning(
                "SMTP credentials not configured. Skipping actual email send. "
                f"Would have sent to: {to_email} | Subject: {subject}"
            )
            return True

        message = EmailMessage()
        message["From"] = settings.mailer_sender_email
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add contents
        if text_content:
            message.set_content(text_content)
        
        # Add HTML version (if both are provided, this becomes the alternative)
        message.add_alternative(html_content, subtype="html")

        try:
            smtp_client = SMTP(
                hostname=settings.smtp_address,
                port=settings.smtp_port,
                use_tls=False,
            )
            
            await smtp_client.connect()
            
            # Start TLS if enabled and available
            if settings.smtp_enable_starttls_auto:
                await smtp_client.starttls()
            
            await smtp_client.login(
                settings.smtp_username,
                settings.smtp_password
            )
            
            await smtp_client.send_message(message)
            await smtp_client.quit()
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    async def send_verification_email(name: str, email: str, token: str) -> bool:
        """
        Send verification email during registration.
        
        Args:
            name: User's full name
            email: User's email
            token: Verification token
            
        Returns:
            Success status
        """
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        
        subject = "Confirme seu cadastro no JusMonitorIA"
        
        text_content = f"""
        Olá {name},
        
        Obrigado por se cadastrar no JusMonitorIA. Para concluir seu registro, \
        por favor acesse o link abaixo para verificar seu e-mail:
        
        {verify_url}
        
        Se você não criou esta conta, simplesmente ignore este e-mail.
        """
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <h2 style="color: #D4AF37;">Bem-vindo ao JusMonitorIA!</h2>
            <p>Olá <strong>{name}</strong>,</p>
            <p>Obrigado por escolher nossa plataforma jurídica premium. Para podermos liberar seu acesso completo, por favor, clique no botão abaixo para confirmar seu endereço de e-mail.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" style="background-color: #D4AF37; color: #0B0F19; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">
                    Confirmar meu E-mail
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666;">
                Ou copie e cole o seguinte link no seu navegador:<br>
                <a href="{verify_url}" style="color: #D4AF37;">{verify_url}</a>
            </p>
            
            <hr style="border: 1px solid #eee; margin: 30px 0;">
            <p style="font-size: 12px; color: #999;">
                Se você não solicitou esta criação de conta, por favor ignore este e-mail.
            </p>
        </div>
        """
        
        return await EmailService.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
