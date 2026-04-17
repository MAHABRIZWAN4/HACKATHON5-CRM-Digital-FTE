"""Support web form endpoint."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
import logging

from app.handlers.web_form import web_form_handler, WebFormRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_support_request(support_request: WebFormRequest):
    """Handle support form submission."""
    try:
        result = await web_form_handler.process_submission(support_request)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result
        )
    except Exception as e:
        logger.error(f"Error processing support request: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "channel": "web_form",
                "message": str(e)
            }
        )


@router.get("/test-db")
async def test_database():
    """Test database connectivity and query tickets."""
    from app.db.connection import get_db_pool
    
    db_pool = get_db_pool()
    
    ticket_count = await db_pool.fetchval('SELECT COUNT(*) FROM tickets')
    customer_count = await db_pool.fetchval('SELECT COUNT(*) FROM customers')
    
    result = {
        "tickets": ticket_count,
        "customers": customer_count
    }
    
    if ticket_count > 0:
        last_ticket = await db_pool.fetchrow(
            'SELECT id, title, status, created_at FROM tickets ORDER BY created_at DESC LIMIT 1'
        )
        result["last_ticket"] = {
            "id": str(last_ticket['id']),
            "title": last_ticket['title'],
            "status": last_ticket['status'],
            "created_at": str(last_ticket['created_at'])
        }
    
    return result
