"""Tool definitions for the Renci agent. Claude uses these to determine intent."""

AGENT_TOOLS = [
    {
        "name": "update_business_hours",
        "description": (
            "Update the business operating hours. Use when the owner mentions "
            "hours, schedule, open times, close times, or days of operation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "object",
                    "description": (
                        "Map of day to hours string, e.g. "
                        '{"monday": "9:00-17:00", "tuesday": "9:00-17:00"}'
                    ),
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["hours"],
        },
    },
    {
        "name": "update_contact_info",
        "description": "Update business contact information (phone, email).",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "New phone number"},
                "email": {"type": "string", "description": "New email address"},
            },
        },
    },
    {
        "name": "update_business_description",
        "description": "Update the business description or about text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description_en": {"type": "string"},
                "description_zh": {"type": "string"},
            },
        },
    },
    {
        "name": "show_status",
        "description": (
            "Show the business profile status — website URL, hours, "
            "connected accounts. Use when the owner asks about their status, "
            "profile, or current settings."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "show_help",
        "description": (
            "Show available commands. Use when the owner is confused, "
            "asks for help, or sends an unclear message."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]
