"""AI Task integration for OpenRouter."""

from __future__ import annotations

from json import JSONDecodeError
import logging
from typing import Any

from homeassistant.components import ai_task, conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.json import json_loads

from . import OpenRouterConfigEntry
from .entity import OpenRouterEntity

_LOGGER = logging.getLogger(__name__)

# Define supported features with fallback for older HA versions
try:
    SUPPORTED_FEATURES = (
        ai_task.AITaskEntityFeature.GENERATE_DATA |
        ai_task.AITaskEntityFeature.ATTACHMENTS
    )
except AttributeError:
    # Fallback for HA versions without ATTACHMENTS feature
    SUPPORTED_FEATURES = ai_task.AITaskEntityFeature.GENERATE_DATA | 2


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OpenRouterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AI Task entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "ai_task_data":
            continue

        async_add_entities(
            [OpenRouterAITaskEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class OpenRouterAITaskEntity(
    ai_task.AITaskEntity,
    OpenRouterEntity,
):
    """OpenRouter AI Task entity."""

    _attr_name = None
    _attr_supported_features = SUPPORTED_FEATURES
        
    async def async_generate_data(
        self,
        prompt: str,
        *,
        attachments: list[Any] | None = None,
        **kwargs,
    ) -> str | dict[str, Any]:
        """Generate data from prompt and optional attachments."""
        
        # Create a simple task object for internal processing
        from types import SimpleNamespace
        task = SimpleNamespace(
            prompt=prompt,
            attachments=attachments or [],
            name="AI Task",
            structure=None
        )
        chat_log = conversation.ChatLog()
        
        # Add user message with prompt
        chat_log.add_user_message(prompt)
        
        # If we have attachments, add them to the chat log
        if attachments:
            # The entity.py will handle the attachments in the chat log
            pass
            
        result = await self._async_generate_data(task, chat_log)
        return result.data

    async def _async_generate_data(
        self,
        task: Any,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenDataTaskResult:
        """Handle a generate data task."""
        # Extract attachments from task if available
        attachments = getattr(task, 'attachments', None)
        
        # Process the chat log (entity.py will handle image conversion)
        await self._async_handle_chat_log(chat_log, task.name, task.structure)

        if not isinstance(chat_log.content[-1], conversation.AssistantContent):
            raise HomeAssistantError(
                "Last content in chat log is not an AssistantContent"
            )

        text = chat_log.content[-1].content or ""

        if not task.structure:
            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )
        
        # Try to parse JSON response for structured output
        try:
            data = json_loads(text)
        except JSONDecodeError:
            # Return raw text if JSON parsing fails
            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )

        return ai_task.GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=data,
        )
