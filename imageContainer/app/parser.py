from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


PARSER_VERSION = "easyocr_total_v1"


def is_float(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except (InvalidOperation, ValueError):
        return False


def parse_money_to_cents(value: str) -> int | None:
    cleaned = value.replace(" ", "").replace("$", "").replace(",", "")
    if not is_float(cleaned):
        return None
    amount = Decimal(cleaned)
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def find_total_cents(result: list[str]) -> int | None:
    for index, text in enumerate(result):
        lowered = text.lower()
        if "subtotal" in lowered:
            continue
        if "total" not in lowered:
            continue

        if index > 0:
            previous = parse_money_to_cents(result[index - 1])
            if previous is not None:
                return previous

        if index + 1 != len(result):
            following = parse_money_to_cents(result[index + 1])
            if following is not None:
                return following

    return None
