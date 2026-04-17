"""Channel-specific response formatters."""

from typing import Dict, Any


class ResponseFormatter:
    """Format responses based on channel."""

    @staticmethod
    def format_for_email(message: str, customer_name: str = None) -> str:
        """Format response for email channel."""
        greeting = f"Dear {customer_name},\n\n" if customer_name else "Hello,\n\n"

        signature = """

Best regards,
Customer Success Team
Support Portal"""

        return f"{greeting}{message}{signature}"

    @staticmethod
    def format_for_whatsapp(message: str) -> str:
        """Format response for WhatsApp channel (max 300 chars)."""
        # Truncate if too long
        if len(message) > 300:
            message = message[:297] + "..."

        return message

    @staticmethod
    def format_for_web_form(message: str) -> str:
        """Format response for web form channel."""
        # Semi-formal, no special formatting needed
        return message

    @staticmethod
    def format_response(message: str, channel: str, customer_name: str = None) -> str:
        """
        Format response based on channel.

        Args:
            message: The message to format
            channel: Channel type (gmail, whatsapp, web_form)
            customer_name: Customer name for personalization

        Returns:
            Formatted message
        """
        if channel == "gmail":
            return ResponseFormatter.format_for_email(message, customer_name)
        elif channel == "whatsapp":
            return ResponseFormatter.format_for_whatsapp(message)
        elif channel == "web_form":
            return ResponseFormatter.format_for_web_form(message)
        else:
            return message


def detect_escalation_triggers(message: str) -> Dict[str, Any]:
    """
    Detect if message contains escalation triggers.

    Args:
        message: Customer message to analyze

    Returns:
        Dict with should_escalate flag and reason
    """
    message_lower = message.lower()

    # Pricing/billing - check FIRST before legal (to avoid false positives)
    pricing_keywords = ["price", "pricing", "cost", "billing", "refund", "payment", "charge"]
    if any(keyword in message_lower for keyword in pricing_keywords):
        return {
            "should_escalate": True,
            "reason": "Pricing/billing inquiry - requires human",
            "urgency": "low"
        }

    # Legal threats
    legal_keywords = ["lawyer", "legal", "sue", "court", "attorney", "litigation"]
    if any(keyword in message_lower for keyword in legal_keywords):
        return {
            "should_escalate": True,
            "reason": "Legal threat detected",
            "urgency": "high"
        }

    # Aggressive language
    aggressive_keywords = ["fuck", "shit", "damn", "stupid", "idiot", "useless"]
    if any(keyword in message_lower for keyword in aggressive_keywords):
        return {
            "should_escalate": True,
            "reason": "Aggressive language detected",
            "urgency": "medium"
        }

    # Human request
    human_keywords = ["speak to", "talk to", "real person", "human agent", "human help", "manager"]
    human_phrases = ["speak to a human", "talk to a person", "need a human", "want a human"]
    if any(keyword in message_lower for keyword in human_keywords + human_phrases):
        # Make sure it's actually about humans, not just contains these words
        if "human" in message_lower or "person" in message_lower or "manager" in message_lower:
            return {
                "should_escalate": True,
                "reason": "Customer requested human agent",
                "urgency": "medium"
            }

    # WhatsApp specific
    if message_lower.strip() in ["human", "agent"]:
        return {
            "should_escalate": True,
            "reason": "Customer requested human agent (WhatsApp)",
            "urgency": "medium"
        }

    return {
        "should_escalate": False,
        "reason": None,
        "urgency": None
    }
