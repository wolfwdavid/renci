"""Agent core — dispatches SMS messages via Google ADK with Gemini."""

import os
from google import genai
from google.genai import types
from config import settings
from agent.tools import (
    update_business_hours,
    update_contact_info,
    update_business_description,
    show_status,
    show_help,
)
from agent.actions.ppp_data import (
    lookup_ppp_data,
    compare_ppp_by_industry,
    check_ppp_forgiveness,
)
from agent.actions.photo import extract_menu_from_photo, download_twilio_media
from agent.prompts.system import get_agent_system_prompt
from agent.prompts.templates import help_response
from db.firestore import get_business
from language.detector import detect_language

# All tools available to the agent
TOOLS = [
    update_business_hours,
    update_contact_info,
    update_business_description,
    show_status,
    show_help,
    lookup_ppp_data,
    compare_ppp_by_industry,
    check_ppp_forgiveness,
    extract_menu_from_photo,
]


def _get_client() -> genai.Client:
    """Get the Gemini client."""
    if settings.use_vertex_ai:
        return genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location="us-east1",
        )
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    return genai.Client()


async def dispatch(message, owner: dict, business_id: str) -> str:
    """Process an incoming SMS through the Gemini agent pipeline."""
    business = await get_business(business_id)
    if not business:
        return "Error: business not found. Please contact support."

    language = detect_language(message.body)
    system_prompt = get_agent_system_prompt(business, language)

    # Build message parts (text + optional MMS images)
    parts = []
    if message.body:
        parts.append(types.Part.from_text(text=message.body))

    # Handle MMS photos — multimodal input for Gemini
    for url in message.media_urls:
        try:
            image_bytes = await download_twilio_media(url)
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        except Exception:
            pass  # Skip failed downloads

    if not parts:
        return help_response(language)

    # Inject business context into tool calls via system instruction
    context_instruction = (
        f"{system_prompt}\n\n"
        f"IMPORTANT: When calling any tool that accepts business_id, "
        f'always pass business_id="{business_id}". '
        f'When calling any tool that accepts language, always pass language="{language}".'
    )

    client = _get_client()

    # Call Gemini with tool definitions
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=context_instruction,
            tools=TOOLS,
            temperature=0.3,
            max_output_tokens=500,
        ),
    )

    # Extract response text
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                return part.text

    return help_response(language)
