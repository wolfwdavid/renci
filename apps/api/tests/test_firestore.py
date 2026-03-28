"""Tests for the Firestore helper functions (slugify)."""

from db.firestore import slugify


def test_slugify_basic():
    assert slugify("Wong's Bakery") == "wongs-bakery"


def test_slugify_chinese():
    assert slugify("黄记饼家") == "黄记饼家"


def test_slugify_mixed():
    assert slugify("Wong's Bakery 黄记饼家") == "wongs-bakery-黄记饼家"


def test_slugify_extra_spaces():
    assert slugify("  Hello   World  ") == "hello-world"


def test_slugify_special_chars():
    assert slugify("Joe's #1 Deli!") == "joes-1-deli"
