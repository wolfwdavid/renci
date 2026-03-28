"""Tests for PPP loan data tools."""

from agent.actions.ppp_data import (
    lookup_ppp_data,
    compare_ppp_by_industry,
    check_ppp_forgiveness,
)


def test_lookup_ppp_valid_zip():
    result = lookup_ppp_data("10013")
    assert result["status"] == "success"
    assert result["total_loans"] > 0
    assert "$" in result["total_amount"]


def test_lookup_ppp_invalid_zip():
    result = lookup_ppp_data("99999")
    assert result["status"] == "success"
    assert "No PPP loan data" in result["message"]


def test_lookup_ppp_with_business_type():
    result = lookup_ppp_data("10013", "restaurant")
    assert result["status"] == "success"
    assert result["total_loans"] > 0


def test_lookup_ppp_with_unknown_type():
    result = lookup_ppp_data("10013", "spaceship")
    # Unknown type returns all data for the zip
    assert result["status"] == "success"


def test_compare_ppp_by_industry():
    result = compare_ppp_by_industry("10013")
    assert result["status"] == "success"
    assert "industries" in result
    assert len(result["industries"]) > 0


def test_compare_ppp_all_chinatown():
    result = compare_ppp_by_industry()
    assert result["status"] == "success"
    assert len(result["industries"]) > 0


def test_forgiveness_valid_zip():
    result = check_ppp_forgiveness("10013")
    assert result["status"] == "success"
    assert "%" in result["forgiveness_rate"]
    assert result["loans_forgiven"] > 0


def test_forgiveness_invalid_zip():
    result = check_ppp_forgiveness("99999")
    assert "No PPP data" in result["message"]


def test_lookup_ppp_10002():
    """Verify we have data for the other Chinatown zip."""
    result = lookup_ppp_data("10002")
    assert result["status"] == "success"
    assert result["total_loans"] > 0
