"""Base entity for Open Router."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncGenerator, Callable
import json
from typing import TYPE_CHECKING, Any, Dict, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionAssistantMessageParam,
        ChatCompletionMessage,
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionToolMessageParam,
        ChatCompletionUserMessageParam,
    )

    # Handle ChatCompletionMessageFunctionToolCallParam separately
    try:
        from openai.types.chat import ChatCompletionMessageFunctionToolCallParam
    except ImportError:
        # Fallback for older versions
        ChatCompletionMessageFunctionToolCallParam = Dict[str, Any]

    # Handle different OpenAI library versions for imports
    try:
        from openai.types.chat import ChatCompletionFunctionToolParam
    except ImportError:
        # Fallback for older versions - create a type alias
        ChatCompletionFunctionToolParam = Dict[str, Any]

    try:
        from openai.types.chat.chat_completion_message_function_tool_call_param import Function
    except ImportError:
        # Fallback for older versions
        class Function(TypedDict):
            name: str
            arguments: str

    try:
        from openai.types.shared_params import FunctionDefinition
    except ImportError:
        # Fallback for older versions
        class FunctionDefinition(TypedDict):
            name: str
            description: NotRequired[str]
            parameters: NotRequired[Dict[str, Any]]

    # Handle different OpenAI library versions
    try:
        from openai.types.shared_params import ResponseFormatJSONSchema
        from openai.types.shared_params.response_format_json_schema import JSONSchema
    except ImportError:
        # Fallback for older OpenAI library versions

        class JSONSchema(TypedDict, total=False):
            """Fallback JSONSchema type."""
            name: str
            description: str | None
            schema: dict[str, Any]
            strict: bool | None

        class ResponseFormatJSONSchema(TypedDict):
            """Fallback ResponseFormatJSONSchema type."""
            type: Literal["json_schema"]
            json_schema: JSONSchema
import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_MODEL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, llm
from homeassistant.helpers.entity import Entity

from . import OpenRouterConfigEntry
from .const import DOMAIN, LOGGER

# Max number of back and forth with the LLM to generate a response
MAX_TOOL_ITERATIONS = 10


def _adjust_schema(schema: dict[str, Any]) -> None:
    """Adjust the schema to be compatible with OpenRouter API."""
    if schema["type"] == "object":
        if "properties" not in schema:
            return

        if "required" not in schema:
            schema["required"] = []

        # Ensure all properties are required
        for prop, prop_info in schema["properties"].items():
            _adjust_schema(prop_info)
            if prop not in schema["required"]:
                prop_info["type"] = [prop_info["type"], "null"]
                schema["required"].append(prop)

    elif schema["type"] == "array":
        if "items" not in schema:
            return

        _adjust_schema(schema["items"])


def _format_structured_output(
    name: str, schema: vol.Schema, llm_api: llm.APIInstance | None
) -> JSONSchema:
    """Format the schema to be compatible with OpenRouter API."""
    result: JSONSchema = {
        "name": name,
        "strict": True,
    }
    result_schema = convert(
        schema,
        custom_serializer=(
            llm_api.custom_serializer if llm_api else llm.selector_serializer
        ),
    )

    _adjust_schema(result_schema)

    result["schema"] = result_schema
    return result


def _format_tool(
    tool: llm.Tool,
    custom_serializer: Callable[[Any], Any] | None,
) -> ChatCompletionFunctionToolParam:
    """Format tool specification."""
    try:
        from openai.types.shared_params import FunctionDefinition
    except ImportError:
        FunctionDefinition = dict  # type: ignore[assignment,misc]

    try:
        from openai.types.chat import ChatCompletionFunctionToolParam as ToolParam
    except ImportError:
        ToolParam = dict  # type: ignore[assignment,misc]

    tool_spec = FunctionDefinition(
        name=tool.name,
        parameters=convert(tool.parameters, custom_serializer=custom_serializer),
    )
    if tool.description:
        tool_spec["description"] = tool.description

    # Create tool param compatible with both old and new OpenAI versions
    try:
        return ToolParam(type="function", function=tool_spec)
    except (TypeError, AttributeError):
        # Fallback to dict format for older versions
        return {"type": "function", "function": tool_spec}


def _convert_content_to_chat_message(
    content: conversation.Content,
) -> ChatCompletionMessageParam | None:
    """Convert any native chat message for this agent to the native format."""
    from openai.types.chat import (
        ChatCompletionAssistantMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionToolMessageParam,
        ChatCompletionUserMessageParam,
    )

    try:
        from openai.types.chat import ChatCompletionMessageFunctionToolCallParam
    except ImportError:
        ChatCompletionMessageFunctionToolCallParam = dict  # type: ignore[assignment,misc]

    try:
        from openai.types.chat.chat_completion_message_function_tool_call_param import Function
    except ImportError:
        Function = dict  # type: ignore[assignment,misc]

    LOGGER.debug("_convert_content_to_chat_message=%s", content)
    if isinstance(content, conversation.ToolResultContent):
        return ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=content.tool_call_id,
            content=json.dumps(content.tool_result),
        )

    role: Literal["user", "assistant", "system"] = content.role
    if role == "system" and content.content:
        return ChatCompletionSystemMessageParam(role="system", content=content.content)

    if role == "user":
        # Handle user messages with potential attachments
        if isinstance(content, conversation.UserContent) and content.attachments:
            # Create multi-part content with text and images
            message_parts = []
            
            # Add text content if present
            if content.content:
                message_parts.append({
                    "type": "text",
                    "text": content.content
                })
            
            # Add attachments (images, etc.)
            for attachment in content.attachments:
                LOGGER.debug("Processing attachment: %s", type(attachment))
                
                # Try different ways to get content type
                content_type = None
                if hasattr(attachment, 'content_type'):
                    content_type = attachment.content_type
                elif hasattr(attachment, 'mime_type'):
                    content_type = attachment.mime_type
                elif hasattr(attachment, 'type'):
                    content_type = attachment.type
                else:
                    # Try to guess from filename if available
                    if hasattr(attachment, 'filename'):
                        filename = attachment.filename.lower()
                        if filename.endswith(('.jpg', '.jpeg')):
                            content_type = 'image/jpeg'
                        elif filename.endswith('.png'):
                            content_type = 'image/png'
                        elif filename.endswith('.webp'):
                            content_type = 'image/webp'
                        elif filename.endswith('.gif'):
                            content_type = 'image/gif'
                    # Default to image/jpeg if we can't determine
                    if not content_type:
                        content_type = 'image/jpeg'
                        LOGGER.warning("Could not determine content type, defaulting to: %s", content_type)
                
                LOGGER.debug("Processing attachment with content type: %s", content_type)
                
                if content_type and content_type.startswith("image/"):
                    try:
                        # Get the content data - try many different attributes
                        image_content = None
                        content_source = None
                        
                        # List of possible content attributes
                        content_attrs = ['content', 'data', 'binary_data', 'bytes', 'file_content', 'image_data', 'payload']
                        
                        for attr in content_attrs:
                            if hasattr(attachment, attr):
                                image_content = getattr(attachment, attr)
                                if image_content:  # Check if not None/empty
                                    content_source = attr
                                    LOGGER.debug("Found image content via %s", attr)
                                    break
                        
                        # If still no content, try to read from file path/url
                        if not image_content:
                            if hasattr(attachment, 'file_path') and attachment.file_path:
                                try:
                                    with open(attachment.file_path, 'rb') as f:
                                        image_content = f.read()
                                        content_source = 'file_path'
                                        LOGGER.debug("Loaded image content from file")
                                except Exception as e:
                                    LOGGER.error("Failed to read file %s: %s", attachment.file_path, e)
                            elif hasattr(attachment, 'path') and attachment.path:
                                try:
                                    with open(attachment.path, 'rb') as f:
                                        image_content = f.read()
                                        content_source = 'path'
                                        LOGGER.debug("Loaded image content from path")
                                except Exception as e:
                                    LOGGER.error("Failed to read path %s: %s", attachment.path, e)
                            elif hasattr(attachment, 'url'):
                                LOGGER.debug("Attachment has URL but no direct content")
                        
                        if not image_content:
                            LOGGER.warning("Could not extract image content from attachment")
                            continue
                        
                        LOGGER.debug("Using image content from: %s", content_source)
                            
                        # Convert image attachment to base64 URL format
                        if isinstance(image_content, bytes):
                            image_data = base64.b64encode(image_content).decode('utf-8')
                        else:
                            # Assume it's already base64 if string
                            image_data = image_content.replace('data:', '').split(',')[-1] if 'data:' in str(image_content) else str(image_content)
                        
                        message_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{image_data}",
                                "detail": "high"  # Use high detail for better analysis
                            }
                        })
                        LOGGER.debug("Added image attachment: %s", content_type)
                    except Exception as e:
                        LOGGER.error("Failed to process image attachment: %s", e)
                        # Add error message to chat instead
                        message_parts.append({
                            "type": "text",
                            "text": f"[Error: Could not process image attachment - {e}]"
                        })
            
            if message_parts:
                return ChatCompletionUserMessageParam(role="user", content=message_parts)
        
        # Fallback to simple text message
        if content.content:
            return ChatCompletionUserMessageParam(role="user", content=content.content)

    if role == "assistant":
        param = ChatCompletionAssistantMessageParam(
            role="assistant",
            content=content.content,
        )
        if isinstance(content, conversation.AssistantContent) and content.tool_calls:
            tool_calls = []
            for tool_call in content.tool_calls:
                try:
                    # Try new OpenAI format first
                    tool_calls.append(ChatCompletionMessageFunctionToolCallParam(
                        type="function",
                        id=tool_call.id,
                        function=Function(
                            arguments=json.dumps(tool_call.tool_args),
                            name=tool_call.tool_name,
                        ),
                    ))
                except (TypeError, AttributeError):
                    # Fallback to dict format for older versions
                    tool_calls.append({
                        "type": "function",
                        "id": tool_call.id,
                        "function": {
                            "arguments": json.dumps(tool_call.tool_args),
                            "name": tool_call.tool_name,
                        },
                    })
            param["tool_calls"] = tool_calls
        return param
    LOGGER.warning("Could not convert message to Completions API: %s", content)
    return None


def _decode_tool_arguments(arguments: str) -> Any:
    """Decode tool call arguments."""
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as err:
        raise HomeAssistantError(f"Unexpected tool argument response: {err}") from err


async def _transform_response(
    message: ChatCompletionMessage,
) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Transform the OpenRouter message to a ChatLog format."""
    data: conversation.AssistantContentDeltaDict = {
        "role": message.role,
        "content": message.content,
    }
    if message.tool_calls:
        data["tool_calls"] = [
            llm.ToolInput(
                id=tool_call.id,
                tool_name=tool_call.function.name,
                tool_args=_decode_tool_arguments(tool_call.function.arguments),
            )
            for tool_call in message.tool_calls
            if tool_call.type == "function"
        ]
    yield data


class OpenRouterEntity(Entity):
    """Base entity for Open Router."""

    _attr_has_entity_name = True

    def __init__(self, entry: OpenRouterConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the entity."""
        self.entry = entry
        self.subentry = subentry
        self.model = subentry.data[CONF_MODEL]
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def _async_handle_chat_log(
        self,
        chat_log: conversation.ChatLog,
        structure_name: str | None = None,
        structure: vol.Schema | None = None,
    ) -> None:
        """Generate an answer for the chat log."""
        import openai

        try:
            from openai.types.shared_params import ResponseFormatJSONSchema
        except ImportError:
            ResponseFormatJSONSchema = dict  # type: ignore[assignment,misc]

        model_args = {
            "model": self.model,
            "user": chat_log.conversation_id,
            "extra_headers": {
                "X-Title": "Home Assistant",
                "HTTP-Referer": "https://www.home-assistant.io/integrations/open_router",
            },
            "extra_body": {"require_parameters": True},
        }

        tools: list[ChatCompletionFunctionToolParam] | None = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        if tools:
            model_args["tools"] = tools

        model_args["messages"] = [
            m
            for content in chat_log.content
            if (m := _convert_content_to_chat_message(content))
        ]

        if structure:
            if TYPE_CHECKING:
                assert structure_name is not None
            # Create response format compatible with both old and new OpenAI versions
            json_schema = _format_structured_output(
                structure_name, structure, chat_log.llm_api
            )
            try:
                # Try new OpenAI format first
                model_args["response_format"] = ResponseFormatJSONSchema(
                    type="json_schema",
                    json_schema=json_schema,
                )
            except (TypeError, AttributeError):
                # Fallback to dict format for compatibility
                model_args["response_format"] = {
                    "type": "json_schema",
                    "json_schema": json_schema,
                }

        client = self.entry.runtime_data

        # Check if we're sending images to a non-vision model
        has_images = any(
            isinstance(msg.get("content"), list) and 
            any(part.get("type") == "image_url" for part in msg.get("content", []))
            for msg in model_args.get("messages", [])
        )
        
        if has_images:
            LOGGER.info("Sending image content to model: %s", self.model)
            
        for _iteration in range(MAX_TOOL_ITERATIONS):
            # Retry logic for transient errors
            max_retries = 2
            last_error = None

            for retry_attempt in range(max_retries + 1):
                try:
                    result = await client.chat.completions.create(**model_args)
                    break  # Success, exit retry loop
                except openai.BadRequestError as err:
                    # Handle 400 errors - usually permanent
                    err_msg = str(err).lower()

                    # Check for vision/image errors (404 in error message)
                    if "vision" in err_msg or "image" in err_msg or "no endpoints found" in err_msg:
                        if "image input" in err_msg:
                            LOGGER.error("Model %s does not support image inputs", self.model)
                            raise HomeAssistantError(
                                f"Model {self.model} does not support images. Please configure a vision-capable model "
                                "(e.g., gpt-4-vision-preview, claude-3-haiku, gemini-pro-vision)."
                            ) from err
                        LOGGER.error("Model %s vision error: %s", self.model, err)
                        raise HomeAssistantError(f"Model {self.model} does not support images. Please configure a vision-capable model.") from err

                    LOGGER.error("Bad request to API: %s", err)
                    raise HomeAssistantError(f"Bad request to API: {err}") from err

                except openai.APIStatusError as err:
                    # Handle HTTP status errors (503, 429, 404, etc.)
                    status_code = err.status_code

                    # Try to extract provider and error details
                    provider_name = "Unknown"
                    error_detail = str(err)
                    try:
                        if hasattr(err, 'response') and err.response:
                            error_data = err.response.json() if hasattr(err.response, 'json') else {}
                            if isinstance(error_data, dict):
                                error_info = error_data.get('error', {})
                                provider_name = error_info.get('metadata', {}).get('provider_name', 'Unknown')
                                error_detail = error_info.get('message', str(err))
                                raw_detail = error_info.get('metadata', {}).get('raw', '')
                                if raw_detail:
                                    error_detail = f"{error_detail} ({raw_detail})"
                    except Exception:
                        pass  # Use default error_detail

                    # Handle specific status codes
                    if status_code == 503:
                        # Service unavailable - temporary capacity issue
                        if retry_attempt < max_retries:
                            retry_delay = 5 * (retry_attempt + 1)  # 5s, 10s
                            LOGGER.warning(
                                "Provider '%s' temporarily unavailable (attempt %d/%d). Retrying in %ds...",
                                provider_name, retry_attempt + 1, max_retries + 1, retry_delay
                            )
                            last_error = err
                            await asyncio.sleep(retry_delay)
                            continue  # Retry
                        else:
                            LOGGER.error("Provider '%s' unavailable after %d retries: %s", provider_name, max_retries, error_detail)
                            raise HomeAssistantError(
                                f"Provider '{provider_name}' is temporarily at capacity. Please try again in a few minutes or select a different model."
                            ) from err

                    elif status_code == 429:
                        # Rate limit - could be temporary
                        if retry_attempt < max_retries:
                            retry_delay = 10 * (retry_attempt + 1)  # 10s, 20s
                            LOGGER.warning(
                                "Rate limited by provider '%s' (attempt %d/%d). Retrying in %ds...",
                                provider_name, retry_attempt + 1, max_retries + 1, retry_delay
                            )
                            last_error = err
                            await asyncio.sleep(retry_delay)
                            continue  # Retry
                        else:
                            LOGGER.error("Rate limit persists after %d retries: %s", max_retries, error_detail)
                            raise HomeAssistantError(
                                f"Rate limit exceeded: {error_detail}. Please wait before retrying or upgrade to a paid plan."
                            ) from err

                    elif status_code == 404:
                        # Not found - usually a configuration issue
                        LOGGER.error("API endpoint not found (404): %s", error_detail)
                        raise HomeAssistantError(f"API error (404): {error_detail}") from err

                    else:
                        # Other HTTP errors
                        LOGGER.error("API returned status %d: %s", status_code, error_detail)
                        raise HomeAssistantError(f"API error ({status_code}): {error_detail}") from err

                except openai.OpenAIError as err:
                    # Generic OpenAI errors (network, auth, etc.)
                    LOGGER.error("Error talking to API: %s", err)
                    raise HomeAssistantError(f"Error talking to API: {err}") from err

            # If we exited retry loop due to max retries, the break above wasn't hit
            # So we need to check if result was set
            if 'result' not in locals():
                if last_error:
                    raise HomeAssistantError("Failed after retries") from last_error
                else:
                    raise HomeAssistantError("Failed to get API response")

            result_message = result.choices[0].message

            model_args["messages"].extend(
                [
                    msg
                    async for content in chat_log.async_add_delta_content_stream(
                        self.entity_id, _transform_response(result_message)
                    )
                    if (msg := _convert_content_to_chat_message(content))
                ]
            )
            if not chat_log.unresponded_tool_results:
                break
