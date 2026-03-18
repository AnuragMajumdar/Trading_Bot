import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger("trading_bot")

VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT")
KNOWN_QUOTE_ASSETS = ("USDT", "BUSD", "BTC", "ETH", "BNB")
MIN_SYMBOL_LENGTH = 5


class ValidationError(Exception):
    """Raised when order parameters fail validation."""
    pass


def _normalize_decimal(value: Decimal) -> str:
    """
    Convert a Decimal to a float-compatible string that Binance accepts.
    Strips trailing zeros and avoids scientific notation.
    e.g. Decimal('0.00100000') -> '0.001', Decimal('3500.00') -> '3500'
    """
    # Remove trailing zeros: 3500.00 -> 3.5E+3, 0.00100 -> 0.001
    normalized = value.normalize()
    text = str(normalized)
    # If normalize() produced scientific notation, convert back to plain decimal
    if "E" in text or "e" in text:
        # Use the normalized value but format without exponent
        text = f"{normalized:f}"
    return text


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
) -> dict:
    """
    Validate and normalize order parameters.
    Returns a dict with cleaned values ready for the API call.
    Raises ValidationError on any invalid input.
    """
    # Symbol: must be alphanumeric, reasonable length, end with a known quote asset
    if not symbol or not symbol.isalnum():
        raise ValidationError(f"Invalid symbol: '{symbol}'. Must be alphanumeric (e.g. BTCUSDT).")
    symbol = symbol.upper()
    if len(symbol) < MIN_SYMBOL_LENGTH:
        raise ValidationError(
            f"Invalid symbol: '{symbol}'. Too short — expected a pair like BTCUSDT."
        )
    if not any(symbol.endswith(quote) for quote in KNOWN_QUOTE_ASSETS):
        raise ValidationError(
            f"Invalid symbol: '{symbol}'. Must end with a known quote asset: "
            f"{', '.join(KNOWN_QUOTE_ASSETS)}."
        )

    # Side
    side = side.upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side: '{side}'. Must be one of {VALID_SIDES}.")

    # Order type
    order_type = order_type.upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(f"Invalid order type: '{order_type}'. Must be one of {VALID_ORDER_TYPES}.")

    # Quantity: parse with Decimal for precision, then normalize for Binance
    try:
        qty = Decimal(quantity)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"Invalid quantity: '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be positive, got {qty}.")

    # Price: required for LIMIT orders
    cleaned_price = None
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            cleaned_price = Decimal(price)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError(f"Invalid price: '{price}'. Must be a positive number.")
        if cleaned_price <= 0:
            raise ValidationError(f"Price must be positive, got {cleaned_price}.")

    params = {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": _normalize_decimal(qty),
    }
    if cleaned_price is not None:
        params["price"] = _normalize_decimal(cleaned_price)

    logger.debug("Validated order params: %s", params)
    return params
