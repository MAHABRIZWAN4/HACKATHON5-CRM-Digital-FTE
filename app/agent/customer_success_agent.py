"""Customer Success Agent using OpenAI SDK."""

import os
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

from app.agent.prompts import SYSTEM_PROMPT, get_channel_instructions
from app.agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response
)
from app.agent.formatters import detect_escalation_triggers

logger = logging.getLogger(__name__)


class CustomerSuccessAgent:
    """Customer Success Digital FTE Agent."""

    def __init__(self):
        """Initialize the agent."""
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        self.base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.agent_name = "Customer Success FTE"

        # Tool definitions for OpenAI function calling
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the knowledge base for relevant articles and documentation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for knowledge base"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (1-20)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_ticket",
                    "description": "Create a support ticket. MUST be called first before any other action.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {
                                "type": "string",
                                "description": "Customer identifier (email or phone)"
                            },
                            "issue": {
                                "type": "string",
                                "description": "Description of the issue"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                                "description": "Priority level"
                            },
                            "channel": {
                                "type": "string",
                                "enum": ["gmail", "whatsapp", "web_form"],
                                "description": "Communication channel"
                            }
                        },
                        "required": ["customer_id", "issue", "priority", "channel"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_customer_history",
                    "description": "Get customer's support history and previous tickets",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {
                                "type": "string",
                                "description": "Customer identifier (email or phone)"
                            }
                        },
                        "required": ["customer_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "escalate_to_human",
                    "description": "Escalate ticket to a human agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID to escalate"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for escalation"
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Urgency level"
                            }
                        },
                        "required": ["ticket_id", "reason", "urgency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_response",
                    "description": "Send response to customer. MUST be called to send final response.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID"
                            },
                            "message": {
                                "type": "string",
                                "description": "Response message to send"
                            },
                            "channel": {
                                "type": "string",
                                "enum": ["gmail", "whatsapp", "web_form"],
                                "description": "Communication channel"
                            }
                        },
                        "required": ["ticket_id", "message", "channel"]
                    }
                }
            }
        ]

        logger.info(f"Initialized {self.agent_name} with model {self.model}")

    async def handle_customer_inquiry(
        self,
        customer_id: str,
        message: str,
        channel: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a customer inquiry.

        Args:
            customer_id: Customer identifier
            message: Customer message
            channel: Communication channel
            customer_name: Customer name (optional)

        Returns:
            Dict with response and metadata
        """
        try:
            logger.info(f"Handling inquiry from {customer_id} via {channel}")

            # Check for escalation triggers
            escalation_check = detect_escalation_triggers(message)
            if escalation_check["should_escalate"]:
                logger.warning(f"Escalation trigger detected: {escalation_check['reason']}")

            # Build system prompt with channel instructions
            system_prompt = SYSTEM_PROMPT + get_channel_instructions(channel)

            # Create conversation messages
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Customer ID: {customer_id}\nCustomer Name: {customer_name or 'Not provided'}\nChannel: {channel}\nMessage: {message}"
                }
            ]

            # Track ticket_id for later use
            ticket_id = None
            final_response = None

            # Call Groq API WITH function calling enabled
            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Agent iteration {iteration}")

                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto",
                        temperature=0.7
                    )

                    assistant_message = response.choices[0].message

                except Exception as api_error:
                    # Handle Groq 400 errors - fallback to simple completion
                    error_str = str(api_error)
                    if "400" in error_str or "tool_use_failed" in error_str.lower():
                        logger.warning(f"Groq API error (likely 400), using fallback mode: {api_error}")
                        return await self._fallback_response(customer_id, message, channel, customer_name)
                    else:
                        # Re-raise other errors
                        raise

                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in (assistant_message.tool_calls or [])
                    ] if assistant_message.tool_calls else None
                })

                # Check if agent wants to use tools
                if not assistant_message.tool_calls:
                    # No tools called - agent gave direct response
                    logger.warning("Agent responded without using tools - this shouldn't happen")
                    final_response = assistant_message.content or "I've processed your request."
                    break

                # Process tool calls
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    import json
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute the tool
                    result = await self._execute_tool(tool_name, tool_args)

                    # Track ticket_id
                    if tool_name == "create_ticket" and result.get("success"):
                        ticket_id = result.get("ticket_id")
                        logger.info(f"Ticket created: {ticket_id}")

                    # Check if send_response was called
                    if tool_name == "send_response" and result.get("success"):
                        final_response = result.get("formatted_message")
                        logger.info("Response sent to customer")

                    tool_results.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # If send_response was called, we're done
                if any(tr["tool"] == "send_response" for tr in tool_results):
                    logger.info("Agent completed workflow with send_response")
                    break

            # If no response was sent, create a fallback
            if not final_response:
                logger.warning("Agent didn't call send_response - creating fallback")
                final_response = "Thank you for contacting us. Your request has been received and we'll get back to you shortly."

            return {
                "success": True,
                "customer_id": customer_id,
                "channel": channel,
                "ticket_id": ticket_id,
                "escalation_triggered": escalation_check["should_escalate"],
                "escalation_reason": escalation_check.get("reason"),
                "response": final_response,
                "iterations": iteration,
                "tools_used": len(tool_results) if 'tool_results' in locals() else 0
            }

        except Exception as e:
            logger.error(f"Error handling customer inquiry: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "We encountered an error processing your request. Please try again."
            }

    async def _fallback_response(
        self,
        customer_id: str,
        message: str,
        channel: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fallback response when Groq API fails with 400 error.
        Creates ticket and sends response using simple completion (no tools).
        """
        try:
            logger.info("Using fallback mode - creating ticket and response directly")

            # Determine priority based on message content
            priority = "medium"
            if any(word in message.lower() for word in ["urgent", "critical", "emergency", "asap"]):
                priority = "high"
            elif any(word in message.lower() for word in ["lawyer", "legal", "sue", "refund"]):
                priority = "urgent"

            # Create ticket directly
            ticket_result = await create_ticket(
                customer_id=customer_id,
                issue=message,
                priority=priority,
                channel=channel
            )

            if not ticket_result.get("success"):
                raise Exception(f"Failed to create ticket: {ticket_result.get('error')}")

            ticket_id = ticket_result.get("ticket_id")
            logger.info(f"Fallback: Created ticket {ticket_id}")

            # Generate intelligent response using Groq simple completion (no tools)
            try:
                response_message = await self._generate_groq_fallback_response(message, customer_name, channel)
            except Exception as groq_error:
                logger.warning(f"Groq fallback failed, using simple response: {groq_error}")
                response_message = self._generate_fallback_message(message, customer_name, channel)

            # Send response directly
            send_result = await send_response(
                ticket_id=ticket_id,
                message=response_message,
                channel=channel
            )

            if not send_result.get("success"):
                logger.error(f"Failed to send response: {send_result.get('error')}")

            return {
                "success": True,
                "customer_id": customer_id,
                "channel": channel,
                "ticket_id": ticket_id,
                "escalation_triggered": False,
                "response": send_result.get("formatted_message", response_message),
                "iterations": 0,
                "tools_used": 2,
                "fallback_mode": True
            }

        except Exception as e:
            logger.error(f"Error in fallback response: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "We encountered an error processing your request. Please try again."
            }

    async def _generate_groq_fallback_response(
        self,
        message: str,
        customer_name: Optional[str],
        channel: str
    ) -> str:
        """Generate intelligent response using Groq simple completion (no tools)."""
        name = customer_name or "there"

        # Create a simple prompt for generating a helpful response
        prompt = f"""You are a helpful customer support agent. A customer named {name} sent this message via {channel}:

"{message}"

Generate a brief, helpful response that:
- Acknowledges their issue
- Provides helpful guidance if possible
- Assures them their ticket has been created
- Is professional and friendly
- Is 2-3 sentences maximum

Response:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )

            generated_response = response.choices[0].message.content.strip()
            logger.info(f"Groq fallback generated response: {generated_response[:100]}...")
            return generated_response

        except Exception as e:
            logger.error(f"Error generating Groq fallback response: {e}")
            raise

    def _generate_fallback_message(
        self,
        message: str,
        customer_name: Optional[str],
        channel: str
    ) -> str:
        """Generate a simple intelligent response without LLM."""
        name = customer_name or "there"

        # Check for common keywords
        if any(word in message.lower() for word in ["login", "sign in", "password", "access"]):
            response = f"Hello {name}! I've received your login issue. Please try resetting your password using the 'Forgot Password' link. If that doesn't work, our team will assist you shortly."
        elif any(word in message.lower() for word in ["refund", "billing", "payment", "charge"]):
            response = f"Hello {name}! I've escalated your billing inquiry to our finance team. They will review your request and respond within 24 hours."
        elif any(word in message.lower() for word in ["bug", "error", "broken", "not working"]):
            response = f"Hello {name}! Thank you for reporting this issue. Our technical team has been notified and will investigate. We'll update you as soon as we have more information."
        else:
            response = f"Hello {name}! Thank you for contacting us. I've created a ticket for your inquiry and our team will respond shortly. We appreciate your patience."

        # Adjust for channel
        if channel == "whatsapp":
            # Shorten for WhatsApp
            response = response.replace("Hello ", "Hi ").replace("Thank you for contacting us. ", "")

        return response

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if tool_name == "search_knowledge_base":
            return await search_knowledge_base(**args)
        elif tool_name == "create_ticket":
            return await create_ticket(**args)
        elif tool_name == "get_customer_history":
            return await get_customer_history(**args)
        elif tool_name == "escalate_to_human":
            return await escalate_to_human(**args)
        elif tool_name == "send_response":
            return await send_response(**args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


# Singleton instance
_agent_instance: Optional[CustomerSuccessAgent] = None


def get_agent() -> CustomerSuccessAgent:
    """Get or create agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CustomerSuccessAgent()
    return _agent_instance
