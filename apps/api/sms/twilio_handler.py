from dataclasses import dataclass


@dataclass
class IncomingSMS:
    from_number: str
    body: str
    media_urls: list[str]
    num_media: int


def parse_incoming_sms(form_data: dict) -> IncomingSMS:
    """Parse Twilio webhook form data into a structured message."""
    num_media = int(form_data.get("NumMedia", 0))
    media_urls = []
    for i in range(num_media):
        url = form_data.get(f"MediaUrl{i}")
        if url:
            media_urls.append(url)

    return IncomingSMS(
        from_number=form_data.get("From", ""),
        body=form_data.get("Body", "").strip(),
        media_urls=media_urls,
        num_media=num_media,
    )
