import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from config import get_config
from app.services.audit_service import log_event

config = get_config()
logger = logging.getLogger(__name__)

# Set up native Jinja2 environment pointing to absolute templates path
template_dir = os.path.join(config.BASE_DIR, "templates")
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def render_template(template_name, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)


def _send(subject, recipients, html, text=None, db: Session = None):
    if config.MAIL_SUPPRESS_SEND:
        logger.info("MAIL_SUPPRESS_SEND is on; not sending '%s' to %s", subject, recipients)
        return False, "mail_suppressed"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.MAIL_DEFAULT_SENDER
        msg["To"] = ", ".join(recipients)

        part1 = MIMEText(text or html, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)

        if config.MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(config.MAIL_SERVER, config.MAIL_PORT, timeout=10)
        else:
            server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=10)
            if config.MAIL_USE_TLS:
                server.starttls()

        if config.MAIL_USERNAME and config.MAIL_PASSWORD:
            server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)

        server.sendmail(config.MAIL_DEFAULT_SENDER, recipients, msg.as_string())
        server.quit()
        return True, None
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)
        if db is not None:
            log_event(db, "email_failed", metadata={"to": recipients, "subject": subject, "error": str(exc)})
        return False, str(exc)


def send_new_account_email(user, store, temp_password, db: Session = None):
    frontend = config.FRONTEND_URL
    html = render_template(
        "email/new_account.html",
        user=user,
        store=store,
        temp_password=temp_password,
        login_url=f"{frontend}/login",
    )
    text = (
        f"Hello {user.full_name},\n\n"
        f"An account has been created for you on Pairly to manage the store '{store.name}'.\n"
        f"Login URL: {frontend}/login\n"
        f"Email: {user.email}\n"
        f"Temporary password: {temp_password}\n\n"
        "You will be prompted to change this password after first login.\n"
    )
    return _send(f"Pairly: your account for {store.name} is ready", [user.email], html, text, db=db)


def send_password_reset_email(user, token, db: Session = None):
    frontend = config.FRONTEND_URL
    reset_url = f"{frontend}/reset-password?token={token}"
    html = render_template("email/password_reset.html", user=user, reset_url=reset_url)
    text = (
        f"Hello {user.full_name or user.email},\n\n"
        f"A password reset was requested for your account. Use the link below within "
        f"{config.PASSWORD_RESET_TTL_MINUTES} minutes:\n{reset_url}\n\n"
        "If you did not request this, ignore this email.\n"
    )
    return _send("Pairly: password reset request", [user.email], html, text, db=db)


def send_store_disabled_email(user, store, reason, db: Session = None):
    html = render_template("email/store_disabled.html", user=user, store=store, reason=reason)
    text = (
        f"Hello {user.full_name or user.email},\n\n"
        f"Your store '{store.name}' has been disabled. Reason: {reason or 'Not specified'}.\n"
        "Please contact the administrator for assistance.\n"
    )
    return _send(f"Pairly: store {store.name} has been disabled", [user.email], html, text, db=db)


def send_scheduled_summary_email(user, store, summary_payload, db: Session = None):
    html = render_template(
        "email/scheduled_summary.html",
        user=user,
        store=store,
        summary=summary_payload,
    )
    return _send(f"Pairly: scheduled summary for {store.name}", [user.email], html, db=db)
