#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Usage examples:
    python cli.py market      --symbol BTCUSDT --side BUY  --quantity 0.002
    python cli.py limit       --symbol ETHUSDT --side SELL --quantity 0.05  --price 3500.00
    python cli.py stop-limit  --symbol BTCUSDT --side SELL --quantity 0.002 --price 80000 --stop-price 81000
"""

import argparse
import json
import sys

from bot.logging_config import setup_logging
from bot.client import get_futures_client, ClientError
from bot.validators import validate_order_params, ValidationError
from bot.orders import place_market_order, place_limit_order, place_stop_limit_order, OrderError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="order_type", help="Order type")
    subparsers.required = True

    # -- Shared arguments factory --
    def _add_common_args(sub):
        sub.add_argument("--symbol", required=True, help="Trading pair (e.g. BTCUSDT)")
        sub.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
        sub.add_argument("--quantity", required=True, help="Order quantity")

    # -- MARKET subcommand --
    market_parser = subparsers.add_parser("market", help="Place a MARKET order")
    _add_common_args(market_parser)

    # -- LIMIT subcommand --
    limit_parser = subparsers.add_parser("limit", help="Place a LIMIT order")
    _add_common_args(limit_parser)
    limit_parser.add_argument("--price", required=True, help="Limit price")

    # -- STOP-LIMIT subcommand --
    stop_limit_parser = subparsers.add_parser(
        "stop-limit",
        help="Place a STOP-LIMIT order (triggers at stop-price, executes at price)",
    )
    _add_common_args(stop_limit_parser)
    stop_limit_parser.add_argument("--price", required=True, help="Limit price after trigger")
    stop_limit_parser.add_argument("--stop-price", required=True, help="Trigger (stop) price")

    return parser


def _format_success(order_type: str, response: dict) -> str:
    """Build a human-readable success message from the API response.

    Binance returns different field names for standard vs conditional (algo) orders:
        Standard:    orderId, status, origQty, stopPrice
        Conditional: algoId, algoStatus, quantity, triggerPrice
    This function handles both transparently.
    """
    # Resolve fields with fallback from conditional → standard naming
    oid = response.get("orderId") or response.get("algoId", "N/A")
    symbol = response.get("symbol", "N/A")
    side = response.get("side", "N/A")
    status = response.get("status") or response.get("algoStatus", "N/A")
    qty = response.get("origQty") or response.get("quantity", "N/A")

    lines = [
        "",
        f"  [SUCCESS] {order_type} order placed",
        f"  Order ID : {oid}",
        f"  Symbol   : {symbol}",
        f"  Side     : {side}",
        f"  Quantity : {qty}",
        f"  Status   : {status}",
    ]

    if order_type in ("LIMIT", "STOP_LIMIT"):
        lines.append(f"  Price    : {response.get('price', 'N/A')}")

    if order_type == "STOP_LIMIT":
        stop = response.get("stopPrice") or response.get("triggerPrice", "N/A")
        lines.append(f"  Stop Price: {stop}")

    avg_price = response.get("avgPrice")
    if avg_price and avg_price != "0":
        lines.append(f"  Avg Price: {avg_price}")

    lines.append("")
    return "\n".join(lines)


def _format_failure(stage: str, error: str) -> str:
    """Build a human-readable failure message."""
    return f"\n  [FAILED] {stage}\n  Error: {error}\n"


# Map CLI subcommand names to internal order type constants
ORDER_TYPE_MAP = {
    "market": "MARKET",
    "limit": "LIMIT",
    "stop-limit": "STOP_LIMIT",
}


def main() -> None:
    logger = setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    order_type = ORDER_TYPE_MAP[args.order_type]
    price = getattr(args, "price", None)
    stop_price = getattr(args, "stop_price", None)

    # Validate inputs
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=order_type,
            quantity=args.quantity,
            price=price,
            stop_price=stop_price,
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
        elif order_type == "LIMIT":
            response = place_limit_order(
                client,
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
            )
        elif order_type == "STOP_LIMIT":
            response = place_stop_limit_order(
                client,
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
                stop_price=params["stop_price"],
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
