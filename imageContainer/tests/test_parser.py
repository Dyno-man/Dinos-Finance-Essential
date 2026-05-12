from app.parser import PARSER_VERSION, find_total_cents


def test_parser_version_is_stable() -> None:
    assert PARSER_VERSION == "easyocr_total_v1"


def test_finds_total_after_keyword() -> None:
    assert find_total_cents(["WALMART", "TOTAL", "12.34"]) == 1234


def test_finds_total_before_keyword() -> None:
    assert find_total_cents(["12.34", "TOTAL"]) == 1234


def test_does_not_treat_subtotal_as_total() -> None:
    assert find_total_cents(["SUBTOTAL", "10.00"]) is None


def test_returns_none_when_total_missing() -> None:
    assert find_total_cents(["WALMART", "THANK YOU"]) is None
