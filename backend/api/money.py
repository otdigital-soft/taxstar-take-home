from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Take-home assumption: all currencies use 2 decimal places (minor units).
CURRENCY_EXPONENT = 2
MINOR_FACTOR = Decimal(10) ** CURRENCY_EXPONENT


def parse_amount_to_minor(value) -> int:
    """Validate a decimal amount and convert to integer minor units."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Amount must be a valid decimal number") from exc

    if amount <= 0:
        raise ValueError("Amount must be a positive number")

    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized != amount:
        # Reject values with more than 2 decimal places rather than silently rounding.
        raise ValueError("Amount must have at most 2 decimal places")

    minor = int(quantized * MINOR_FACTOR)
    if minor <= 0:
        raise ValueError("Amount must be a positive number")
    return minor


def minor_to_amount_str(amount_minor: int) -> str:
    amount = (Decimal(amount_minor) / MINOR_FACTOR).quantize(Decimal("0.01"))
    return format(amount, "f")


def amount_minor_from_doc(doc: dict) -> int:
    """
    Read amount_minor from a document.
    Supports legacy invoices that stored a float/string `amount` field
    before the minor-units migration.
    """
    if "amount_minor" in doc and doc["amount_minor"] is not None:
        return int(doc["amount_minor"])
    if "amount" in doc and doc["amount"] is not None:
        return parse_amount_to_minor(doc["amount"])
    raise KeyError("Invoice is missing amount_minor (and legacy amount)")
