#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Usage examples:
    python cli.py market --symbol BTCUSDT --side BUY --quantity 0.001
    python cli.py limit  --symbol ETHUSDT --side SELL --quantity 0.05 --price 3500.00
"""

import argparse
import json
import sys

from bot.logging_config import setup_logging
from bot.client import get_futures_client, ClientError
from bot.validators import validate_order_params, ValidationError
from bot.orders import place_market_order, place_limit_order, OrderError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="order_type", help="Order type")
    subparsers.required = True

    # -- MARKET subcommand --
    market_parser = subparsers.add_parser("market", help="Place a MARKET order")
    market_parser.add_argument("--symbol", required=True, help="Trading pair (e.g. BTCUSDT)")
    market_parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    market_parser.add_argument("--quantity", required=True, help="Order quantity")

    # -- LIMIT subcommand --
    limit_parser = subparsers.add_parser("limit", help="Place a LIMIT order")
    limit_parser.add_argument("--symbol", required=True, help="Trading pair (e.g. BTCUSDT)")
    limit_parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    limit_parser.add_argument("--quantity", required=True, help="Order quantity")
    limit_parser.add_argument("--price", required=True, help="Limit price")

    return parser


def _format_success(order_type: str, response: dict) -> str:
    """Build a human-readable success message from the API response."""
    oid = response.get("orderId", "N/A")
    symbol = response.get("symbol", "N/A")
    side = response.get("side", "N/A")
    status = response.get("status", "N/A")
    qty = response.get("origQty", response.get("executedQty", "N/A"))

    lines = [
        "",
        f"  [SUCCESS] {order_type} order placed",
        f"  Order ID : {oid}",
        f"  Symbol   : {symbol}",
        f"  Side     : {side}",
        f"  Quantity : {qty}",
        f"  Status   : {status}",
    ]

    if order_type == "LIMIT":
        lines.append(f"  Price    : {response.get('price', 'N/A')}")

    avg_price = response.get("avgPrice")
    if avg_price and avg_price != "0":
        lines.append(f"  Avg Price: {avg_price}")

    lines.append("")
    return "\n".join(lines)


def _format_failure(stage: str, error: str) -> str:
    """Build a human-readable failure message."""
    return f"\n  [FAILED] {stage}\n  Error: {error}\n"


def main() -> None:
    logger = setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    order_type = args.order_type.upper()
    price = getattr(args, "price", None)

    # Validate inputs
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=order_type,
            quantity=args.quantity,
            price=price,
        )
    except ValidationError as exc:
        msg = _format_failure("Input validation", str(exc))
        logger.error("Validation failed: %s", exc)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Initialize client
    try:
        client = get_futures_client()
    except ClientError as exc:
        msg = _format_failure("Client initialization", str(exc))
        logger.error("Client initialization failed: %s", exc)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Place order
    try:
        if order_type == "MARKET":
            response = place_market_order(
                client,
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
            )
        else:
            response = place_limit_order(
                client,
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
            )
    except OrderError as exc:
        msg = _format_failure("Order placement", str(exc))
        logger.error("Order failed: %s", exc)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Display results
    logger.info("Order response:\n%s", json.dumps(response, indent=2))
    print(_format_success(order_type, response))


if __name__ == "__main__":
    main()
