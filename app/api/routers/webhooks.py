"""Webhook endpoints for Gmail and WhatsApp."""

import os
from fastapi import APIRouter, Request, Header, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.handlers.gmail import gmail_handler
from app.handlers.whatsapp import whatsapp_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/gmail", status_code=status.HTTP_200_OK)
async def gmail_webhook(request: Request):
    """Handle incoming Gmail webhook events."""
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "channel": "gmail",
                "message": "Demo mode: Webhook received but not processed",
                "demo_mode": True
            }
        )

    try:
        body = await request.json()
        result = await gmail_handler.process_webhook(body)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
    except Exception as e:
        logger.error(f"Error processing Gmail webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "channel": "gmail",
                "message": str(e)
            }
        )


@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None)
):
    """Handle incoming WhatsApp webhook events."""
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "channel": "whatsapp",
                "message": "Demo mode: Webhook received but not processed",
                "demo_mode": True
            }
        )

    try:
        # Get form data (Twilio sends form-encoded data)
        body = await request.form()
        body_dict = dict(body)

        # Get full URL for signature validation
        url = str(request.url)

        result = await whatsapp_handler.process_webhook(
            body_dict,
            signature=x_twilio_signature,
            url=url
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "channel": "whatsapp",
                "message": str(e)
            }
        )
