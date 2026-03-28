"""Response templates for common agent actions — bilingual."""


def hours_updated_response(hours: dict, language: str) -> str:
    hours_str = "\n".join(f"  {day}: {time}" for day, time in sorted(hours.items()))
    if language == "zh":
        return f"营业时间已更新！\n{hours_str}"
    return f"Hours updated!\n{hours_str}"


def contact_updated_response(updates: dict, language: str) -> str:
    parts = []
    if "phone" in updates:
        parts.append(f"Phone: {updates['phone']}")
    if "email" in updates:
        parts.append(f"Email: {updates['email']}")
    detail = ", ".join(parts)
    if language == "zh":
        return f"联系方式已更新！{detail}"
    return f"Contact info updated! {detail}"


def status_response(business: dict, language: str) -> str:
    slug = business.get("slug", "")
    name = business.get("name_zh") or business.get("name", "")
    hours = business.get("hours", {})
    hours_str = ", ".join(f"{d}: {t}" for d, t in sorted(hours.items())) or "Not set"

    if language == "zh":
        return (
            f"{name}\n"
            f"网站: renci.app/{slug}\n"
            f"营业时间: {hours_str}\n"
            f"电话: {business.get('phone', 'Not set')}\n"
            f"邮箱: {business.get('email', 'Not set')}"
        )
    return (
        f"{business.get('name', '')}\n"
        f"Website: renci.app/{slug}\n"
        f"Hours: {hours_str}\n"
        f"Phone: {business.get('phone', 'Not set')}\n"
        f"Email: {business.get('email', 'Not set')}"
    )


def help_response(language: str) -> str:
    if language == "zh":
        return (
            "你可以发短信给我：\n"
            '- "更新营业时间 周一到周五 9点到5点"\n'
            '- "更新电话 212-555-1234"\n'
            '- "更新描述 家庭式面包店"\n'
            '- "状态" 查看当前信息\n'
            '- "帮助" 显示此菜单'
        )
    return (
        "You can text me:\n"
        '- "Update hours Mon-Fri 9am-5pm"\n'
        '- "Update phone 212-555-1234"\n'
        '- "Update description Family bakery since 1985"\n'
        '- "Status" to see your profile\n'
        '- "Help" for this menu'
    )
