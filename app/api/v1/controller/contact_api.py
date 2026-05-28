"""POST /contact — public waitlist / contact form on the marketing site.

No JWT — anyone visiting the page can submit. The handler:
  1. validates the payload via Pydantic (`name`, `email`, `subject`, `message`)
  2. checks the waitlist table for an existing row with this email
  3. if found → returns 200 with a friendly already-on-list message
  4. otherwise → inserts a new row and returns 201 with a welcome message

Email is the unique key; the lookup + insert are case-insensitive
(normalized at the repository boundary).
"""

import logging
import random

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.contact_request import ContactRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.db.repository.waitlist_repository import WaitlistRepository
from app.db.session import get_db
from app.model.waitlist_model import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter(tags=[Tags.Contact])

# Pool of one-liner responses used when the submitter is already on the
# list. Picked at random so a polite re-submitter doesn't see the same
# canned line twice in a row.
_ALREADY_ON_LIST_MESSAGES = (
    "You're already part of something great. We'll be in touch soon.",
    "Good things happen to those who wait — you're on the list.",
    "We've already got you on the list. Sit tight.",
    "Already signed up — thanks for the enthusiasm! We'll reach out shortly.",
)


@router.post("/contact", response_model=BaseResponse[dict])
async def submit_contact(
    body: ContactRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = WaitlistRepository(db)
    existing = await repo.get_by_email(body.email)
    if existing is not None:
        # Re-submitter — don't 4xx (treat the form as idempotent from the
        # user's point of view) and pick a friendly nudge.
        logger.info("contact: dup submit email=%s existing_id=%s", body.email, existing.id)
        return success_response(
            {"received": True, "duplicate": True},
            random.choice(_ALREADY_ON_LIST_MESSAGES),
        )

    entry = WaitlistEntry(
        email=body.email,
        name=body.name,
        subject=body.subject,
        message=body.message,
        source="contact",
    )
    await repo.create(entry)
    await db.commit()
    logger.info(
        "contact: new signup id=%s email=%s subject=%r",
        entry.id, entry.email, body.subject,
    )
    return success_response(
        {"received": True, "duplicate": False},
        "Thanks — you're on the list. We'll get back to you within a day or two.",
    )
