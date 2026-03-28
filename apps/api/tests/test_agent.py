"""Tests for the agent core and tool execution."""

import pytest
from language.detector import detect_language, is_traditional_chinese
from agent.prompts.templates import help_response, status_response


def test_detect_english():
    assert detect_language("Update hours Mon-Fri 9-5") == "en"


def test_detect_chinese():
    assert detect_language("更新营业时间") == "zh"


def test_detect_mixed_mostly_english():
    assert detect_language("Update hours 周一到周五") == "en"


def test_detect_mixed_mostly_chinese():
    assert detect_language("更新营业时间 Monday to Friday") == "zh"


def test_traditional_chinese_detection():
    assert is_traditional_chinese("這裡有很多東西") is True
    assert is_traditional_chinese("这里有很多东西") is False


def test_help_response_english():
    resp = help_response("en")
    assert "Update hours" in resp
    assert "Help" in resp


def test_help_response_chinese():
    resp = help_response("zh")
    assert "更新营业时间" in resp
    assert "帮助" in resp


def test_status_response():
    business = {
        "name": "Wong's Bakery",
        "name_zh": "黄记饼家",
        "slug": "wongs-bakery",
        "hours": {"monday": "7:00-18:00"},
        "phone": "212-555-1234",
        "email": "wong@gmail.com",
    }
    resp = status_response(business, "en")
    assert "wongs-bakery" in resp
    assert "Wong's Bakery" in resp
