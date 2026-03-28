"""Tests for photo/multimodal tools."""

from agent.actions.photo import extract_menu_from_photo


def test_extract_menu_returns_success():
    result = extract_menu_from_photo("Pork bun $2.50, Egg tart $1.75, Sesame ball $1.00")
    assert result["status"] == "success"
    assert "menu items" in result["message"].lower()
    assert result["description"] == "Pork bun $2.50, Egg tart $1.75, Sesame ball $1.00"


def test_extract_menu_empty_description():
    result = extract_menu_from_photo("")
    assert result["status"] == "success"
