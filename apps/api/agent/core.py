"""Agent core — dispatches SMS messages to Claude for tool-use intent detection."""

import anthropic
from config import settings
from agent.tools import AGENT_TOOLS
from agent.prompts.system import get_agent_system_prompt
from agent.prompts.templates import (
    hours_updated_response,
    contact_updated_response,
    status_response,
    help_response,
)
from agent.actions.profile import update_hours, update_contact, update_description
from db.firestore import get_business
from language.detector import detect_language


async def dispatch(message, owner: dict, business_id: str) -> str:
    """Process an incoming message through the agent pipeline."""
    business = await get_business(business_id)
    if not business:
        return "Error: business not found. Please contact support."

    language = detect_language(message.body)

    # Build Claude request
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = get_agent_system_prompt(business, language)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=system_prompt,
        tools=AGENT_TOOLS,
        messages=[{"role": "user", "content": message.body}],
    )

    # Process response
    for block in response.content:
        if block.type == "tool_use":
            return await execute_tool(
                block.name, block.input, business, language
            )
        if block.type == "text":
            return block.text

    return help_response(language)


async def execute_tool(
    tool_name: str, tool_input: dict, business: dict, language: str
) -> str:
    """Execute an agent tool and return the response text."""
    business_id = business["id"]

    if tool_name == "update_business_hours":
        hours = tool_input.get("hours", {})
        await update_hours(business_id, hours)
        return hours_updated_response(hours, language)

    if tool_name == "update_contact_info":
        await update_contact(business_id, tool_input)
        return contact_updated_response(tool_input, language)

    if tool_name == "update_business_description":
        await update_description(business_id, tool_input)
        if language == "zh":
            return "商店描述已更新！"
        return "Description updated!"

    if tool_name == "show_status":
        return status_response(business, language)

    if tool_name == "show_help":
        return help_response(language)

    return help_response(language)
