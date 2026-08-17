"""
Conversation service.

Orchestrates the full conversation flow:
1. Load chat history from database
2. Build message context for the LLM
3. Enrich with RAG context from vector store
4. Call OpenRouter API with tool specs
5. Handle tool call execution if LLM requests tools
6. Generate final response
7. Save AI response to database
8. Return response for sending back to user
"""

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.llm.client import llm_client
from app.repositories.chat import ChatRepository
from app.repositories.message import MessageRepository
from app.services.rag import rag_service
from app.tools.base import registry

# System prompt that defines the AI assistant's behavior
SYSTEM_PROMPT = (
    "You are an intelligent AI personal assistant. You help users with "
    "a wide range of tasks including answering questions, managing schedules, "
    "sending emails, and performing actions. "
    "You are concise, helpful, and accurate. "
    "You respond in the same language the user writes in. "
    "\n\nIMPORTANT: You have tools available. ALWAYS use them when the user asks about:\n"
    "- Calendar, schedule, events, meetings, appointments -> use list_calendar_events or create_calendar_event\n"
    "- Email, inbox, sending messages -> use list_inbox or send_email\n"
    "- Time, date -> use get_current_time\n"
    "- Math calculations -> use calculator\n"
    "- Weather -> use get_weather\n"
    "\nNEVER say you cannot check the calendar or email. ALWAYS use the tools first. "
    "The calendar and email tools connect to the user's real Google account when connected. "
    "Current date: {date}"
)

# Maximum number of messages to include in the LLM context window
MAX_CONTEXT_MESSAGES = 50

# Maximum number of tool call iterations (prevent infinite loops)
MAX_TOOL_ITERATIONS = 5


class ConversationService:
    """
    Service for managing AI conversations.

    Handles message history retrieval, LLM prompt construction,
    RAG context enrichment, tool calling, response generation,
    and storing AI responses.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._msg_repo = MessageRepository(session)
        self._chat_repo = ChatRepository(session)

    def _build_system_prompt(self, rag_context: str = "") -> str:
        """Build the system prompt with dynamic context and optional RAG context."""
        from datetime import datetime, timezone
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        prompt = SYSTEM_PROMPT.format(date=date_str)

        if rag_context:
            prompt += (
                "\n\nYou have the following information from the user's documents "
                "that may be relevant to their question:\n\n"
                f"{rag_context}\n\n"
                "Use this information if it helps answer the user's question. "
                "If the information is not relevant, ignore it."
            )

        return prompt

    async def _build_messages(
        self,
        chat_id: UUID,
        rag_context: str = "",
    ) -> list[dict]:
        """Build the complete message list for the LLM API call."""
        history = await self._msg_repo.get_chat_history(
            chat_id, limit=MAX_CONTEXT_MESSAGES
        )

        messages = []
        messages.append({
            "role": "system",
            "content": self._build_system_prompt(rag_context),
        })

        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        return messages

    async def _execute_tool_calls(
        self,
        messages: list[dict],
        tool_calls: list[dict],
        user_id: str = "",
    ) -> list[dict]:
        """
        Execute tool calls requested by the LLM and append results as messages.
        """
        from app.tools.base import _user_preferences

        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            try:
                arguments = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}

            # Inject user_id for tools that need it (e.g. Google Calendar)
            if user_id:
                arguments["user_id"] = user_id

            logger.info("Executing tool call: %s(%s)", tool_name, arguments)
            logger.debug(
                "Tool user_id='%s', in-memory prefs keys=%s",
                user_id, list(_user_preferences.keys()),
            )
            result = await registry.execute(tool_name, arguments)
            logger.info("Tool result: %s", result[:200])

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

        return messages

    async def generate_response(
        self,
        chat_id: UUID,
        user_message_id: UUID,
    ) -> str:
        """
        Generate an AI response for a chat with RAG and tool calling.

        Args:
            chat_id: The UUID of the chat.
            user_message_id: The UUID of the user's message.

        Returns:
            The AI response text.
        """
        # Get the user message to use as RAG query
        user_msg = await self._msg_repo.get(user_message_id)
        user_text = user_msg.content if user_msg else ""

        # Get the chat to find user_id for scoped RAG search
        chat = await self._chat_repo.get(chat_id)
        user_id = str(chat.user_id) if chat else None

        # Search for relevant RAG context
        rag_context = ""
        if user_text:
            try:
                rag_results = await rag_service.search_context(
                    query=user_text,
                    user_id=user_id,
                    limit=3,
                )
                rag_context = rag_service.format_context(rag_results)
            except Exception as e:
                logger.warning("RAG search failed (non-critical): %s", e)

        # Build messages with RAG context
        messages = await self._build_messages(chat_id, rag_context)

        # Get tool specs
        tool_specs = registry.get_specs()
        tools_param = tool_specs if tool_specs else None

        logger.debug(
            "Generating response for chat %s with %d messages, %d tools",
            chat_id, len(messages), len(tool_specs),
        )

        # Call the LLM with tool support
        response = await llm_client.chat_completion(messages, tools=tools_param)

        # Handle tool calls if present
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls", [])

        tool_iterations = 0
        while tool_calls and tool_iterations < MAX_TOOL_ITERATIONS:
            tool_iterations += 1
            messages.append({
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": tool_calls,
            })
            messages = await self._execute_tool_calls(messages, tool_calls, user_id=user_id or "")
            response = await llm_client.chat_completion(messages, tools=tools_param)
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])

        # Extract the final response text
        try:
            ai_content = message.get("content") or ""
            if not ai_content:
                ai_content = "I've completed the requested action."
            total_tokens = response.get("usage", {}).get("total_tokens", 0)
            logger.info(
                "LLM response: %d tokens, %d tool calls for chat %s",
                total_tokens, tool_iterations, chat_id,
            )
        except (KeyError, IndexError) as e:
            logger.error("Failed to parse LLM response: %s", response)
            ai_content = "I'm sorry, I encountered an error processing your request."

        # Save the AI response
        if chat:
            metadata = {
                "model": response.get("model", ""),
                "total_tokens": response.get("usage", {}).get("total_tokens", 0),
                "rag_used": bool(rag_context),
                "tool_calls": tool_iterations,
            }
            await self._msg_repo.create(
                chat_id=chat_id,
                user_id=chat.user_id,
                role="assistant",
                content=ai_content,
                metadata_json=json.dumps(metadata),
            )

        return ai_content