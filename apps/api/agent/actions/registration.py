"""Multi-step SMS registration flow for new business owners."""

from sms.twilio_handler import IncomingSMS
from db.firestore import create_owner, update_owner, create_business, get_owner_by_phone, slugify
from models.business import BUSINESS_TYPES
from language.detector import detect_language

# Registration steps in order
STEPS = ["name", "type", "address", "address_confirm", "email", "complete"]


async def handle_registration(message: IncomingSMS) -> str:
    """Handle registration flow based on current step."""
    owner = await get_owner_by_phone(message.from_number)

    if owner is None:
        owner = await create_owner(message.from_number)
        return _welcome_message()

    step = owner.get("registration_step", "name")
    reg_data = owner.get("registration_data", {})
    language = detect_language(message.body) if message.body else "en"

    if step == "name":
        return await _handle_name(owner, message.body, reg_data)

    if step == "type":
        return await _handle_type(owner, message.body, reg_data)

    if step == "address":
        return await _handle_address(owner, message.body, reg_data)

    if step == "address_confirm":
        return await _handle_address_confirm(owner, message.body, reg_data)

    if step == "email":
        return await _handle_email(owner, message.body, reg_data)

    return _welcome_message()


def _welcome_message() -> str:
    return (
        "Welcome to Renci! I help small businesses "
        "build their online presence for free.\n\n"
        "What is the name of your business?\n"
        "你的店叫什么名字？"
    )


async def _handle_name(owner: dict, body: str, reg_data: dict) -> str:
    reg_data["name"] = body
    await update_owner(owner["id"], {
        "registration_step": "type",
        "registration_data": reg_data,
    })
    return (
        f"Got it: {body}\n\n"
        "What kind of business? Reply with a number:\n"
        "1=Restaurant 餐馆\n"
        "2=Bakery 面包店\n"
        "3=Grocery 杂货店\n"
        "4=Salon 美容院\n"
        "5=Laundry 洗衣店\n"
        "6=Retail 零售店\n"
        "7=Other 其他"
    )


async def _handle_type(owner: dict, body: str, reg_data: dict) -> str:
    choice = body.strip()
    if choice not in BUSINESS_TYPES:
        return (
            "Please reply with a number 1-7:\n"
            "1=Restaurant 2=Bakery 3=Grocery\n"
            "4=Salon 5=Laundry 6=Retail 7=Other"
        )

    reg_data["business_type"] = BUSINESS_TYPES[choice]
    await update_owner(owner["id"], {
        "registration_step": "address",
        "registration_data": reg_data,
    })
    return "What is your address?\n你的地址是什么？"


async def _handle_address(owner: dict, body: str, reg_data: dict) -> str:
    address = body.strip()
    # Append NYC defaults if not specified
    if "new york" not in address.lower() and "ny" not in address.lower():
        address = f"{address}, New York, NY"

    reg_data["address"] = address
    await update_owner(owner["id"], {
        "registration_step": "address_confirm",
        "registration_data": reg_data,
    })
    return f"{address}\n\nCorrect? (Y/N)\n对吗？(Y/N)"


async def _handle_address_confirm(owner: dict, body: str, reg_data: dict) -> str:
    answer = body.strip().upper()
    if answer in ("Y", "YES", "是", "对"):
        await update_owner(owner["id"], {
            "registration_step": "email",
            "registration_data": reg_data,
        })
        return "What email should we use for your account?\n你的电邮是什么？"

    # Go back to address step
    await update_owner(owner["id"], {
        "registration_step": "address",
        "registration_data": reg_data,
    })
    return "No problem. What is the correct address?\n请输入正确的地址："


async def _handle_email(owner: dict, body: str, reg_data: dict) -> str:
    email = body.strip()

    # Basic email validation
    if "@" not in email or "." not in email:
        return "Please enter a valid email address.\n请输入有效的电邮地址。"

    # Create the business
    name = reg_data.get("name", "")
    slug = slugify(name)

    business_id = await create_business({
        "slug": slug,
        "name": name,
        "name_zh": "",
        "business_type": reg_data.get("business_type", "other"),
        "address": reg_data.get("address", ""),
        "phone": owner.get("phone", ""),
        "email": email,
        "description_en": "",
        "description_zh": "",
        "hours": {},
    })

    # Finalize owner record
    await update_owner(owner["id"], {
        "registration_step": None,
        "registration_data": {},
        "email": email,
        "business_id": business_id,
    })

    return (
        f"You're all set! Your website is live:\n"
        f"renci.app/{slug}\n\n"
        f"Text me anytime to update it!\n"
        f"随时发短信给我来更新！\n\n"
        f'Try: "Update hours Mon-Sat 9am-6pm"\n'
        f'或者: "更新营业时间 周一到周六 9点到6点"'
    )
