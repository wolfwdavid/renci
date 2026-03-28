"""Tests for SMS parsing and routing."""

from sms.twilio_handler import parse_incoming_sms


def test_parse_basic_sms():
    form = {
        "From": "+12125551234",
        "Body": "Hello",
        "NumMedia": "0",
    }
    msg = parse_incoming_sms(form)
    assert msg.from_number == "+12125551234"
    assert msg.body == "Hello"
    assert msg.media_urls == []
    assert msg.num_media == 0


def test_parse_sms_with_media():
    form = {
        "From": "+12125551234",
        "Body": "Check this out",
        "NumMedia": "2",
        "MediaUrl0": "https://api.twilio.com/media/1.jpg",
        "MediaUrl1": "https://api.twilio.com/media/2.jpg",
    }
    msg = parse_incoming_sms(form)
    assert msg.num_media == 2
    assert len(msg.media_urls) == 2


def test_parse_empty_body():
    form = {
        "From": "+12125551234",
        "Body": "  ",
        "NumMedia": "0",
    }
    msg = parse_incoming_sms(form)
    assert msg.body == ""


def test_parse_chinese_body():
    form = {
        "From": "+12125551234",
        "Body": "更新营业时间 周一到周五 9点到5点",
        "NumMedia": "0",
    }
    msg = parse_incoming_sms(form)
    assert "更新营业时间" in msg.body
