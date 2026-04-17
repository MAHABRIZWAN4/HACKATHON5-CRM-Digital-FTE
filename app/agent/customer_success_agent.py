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
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
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
                    "content": f"Customer ID: {customer_id}\nChannel: {channel}\nMessage: {message}"
                }
            ]

            # Call OpenAI API WITHOUT function calling (free models don't support tools)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

            # Process tool calls (disabled for free models)
            tool_results = []
            # Free OpenRouter models don't support tool use
            # if response.choices[0].message.tool_calls:
            #     for tool_call in response.choices[0].message.tool_calls:
            #         tool_name = tool_call.function.name
            #         tool_args = eval(tool_call.function.arguments)
            #
            #         logger.info(f"Executing tool: {tool_name}")
            #
            #         # Execute the tool
            #         result = await self._execute_tool(tool_name, tool_args)
            #         tool_results.append({
            #             "tool": tool_name,
            #             "result": result
            #         })

            return {
                "success": True,
                "customer_id": customer_id,
                "channel": channel,
                "escalation_triggered": escalation_check["should_escalate"],
                "escalation_reason": escalation_check.get("reason"),
                "tool_calls": tool_results,
                "response": response.choices[0].message.content
            }

        except Exception as e:
            logger.error(f"Error handling customer inquiry: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
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
