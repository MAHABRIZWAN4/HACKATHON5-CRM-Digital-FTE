"""Dashboard endpoint for escalated tickets."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import logging
import json

from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/escalations", status_code=status.HTTP_200_OK)
async def get_escalations():
    """Get all escalated tickets."""
    try:
        db_pool = get_db_pool()

        escalations = await db_pool.fetch(
            """
            SELECT
                t.id,
                t.title,
                t.status,
                t.priority,
                t.escalated_at,
                t.created_at,
                t.metadata,
                c.email as customer_email,
                c.name as customer_name
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.escalated = true
            ORDER BY t.escalated_at DESC
            """
        )

        result = []
        for row in escalations:
            # Handle metadata - it might be a string or dict
            metadata = row['metadata']
            if metadata is None:
                metadata = {}
            elif isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            result.append({
                "ticket_id": str(row['id']),
                "customer_email": row['customer_email'],
                "customer_name": row['customer_name'],
                "title": row['title'],
                "reason": metadata.get('escalation_reason', 'No reason provided'),
                "urgency": metadata.get('escalation_urgency', 'medium'),
                "status": row['status'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "escalated_at": row['escalated_at'].isoformat() if row['escalated_at'] else None
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "escalations": result,
                "count": len(result)
            }
        )

    except Exception as e:
        logger.error(f"Error fetching escalations: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e),
                "escalations": []
            }
        )


@router.post("/escalations/{ticket_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_escalation(ticket_id: str):
    """Mark an escalated ticket as resolved."""
    try:
        db_pool = get_db_pool()

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Update ticket status
                result = await conn.execute(
                    """
                    UPDATE tickets
                    SET status = 'resolved',
                        resolved_at = NOW()
                    WHERE id = $1::uuid AND escalated = true
                    """,
                    ticket_id
                )

                if result == "UPDATE 0":
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={
                            "success": False,
                            "error": "Ticket not found or not escalated"
                        }
                    )

        logger.info(f"Ticket {ticket_id} marked as resolved")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "ticket_id": ticket_id,
                "message": "Ticket marked as resolved"
            }
        )

    except Exception as e:
        logger.error(f"Error resolving ticket: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e)
            }
        )
