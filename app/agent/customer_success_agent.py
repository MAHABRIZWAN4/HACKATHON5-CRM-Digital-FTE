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

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.7
                )

                assistant_message = response.choices[0].message

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
