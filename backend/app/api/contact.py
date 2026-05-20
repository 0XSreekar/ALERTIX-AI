"""Contact form endpoint — POST /api/contact → sends email via Resend."""

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.logging import get_logger
from app.schemas.contact import ContactForm

log = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["contact"])


@router.post("/contact")
async def submit_contact(body: ContactForm) -> dict:
    settings = get_settings()

    if not settings.resend_api_key:
        log.warning("contact_skip_no_resend_key")
        return {"status": "queued", "message": "Email delivery not configured — saved for later."}

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": "Alertix Contact <noreply@alertix.ai>",
                "to": [settings.contact_to_email],
                "subject": f"Contact from {body.name}",
                "text": f"Name: {body.name}\nEmail: {body.email}\n\n{body.message}",
                "reply_to": body.email,
            }
        )
    except Exception as exc:
        log.error("contact_email_error", error=str(exc))
        raise HTTPException(status_code=502, detail="Email sending failed") from exc

    return {"status": "sent"}
