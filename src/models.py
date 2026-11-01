"""
src/models.py

Domain models for trading orders, trades, books, and trading accounts.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    order_id: str = field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:8]}")
    trader_id: str = ""
    symbol: str = "BTC-USD"
    side: Side = Side.BUY
    order_type: OrderType = OrderType.LIMIT
    price: float = 0.0
    quantity: float = 0.0
    remaining_quantity: float = 0.0
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.NEW
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.remaining_quantity == 0.0 and self.quantity > 0.0:
            self.remaining_quantity = self.quantity


@dataclass
class Trade:
    trade_id: str = field(default_factory=lambda: f"trd_{uuid.uuid4().hex[:8]}")
    symbol: str = ""
    price: float = 0.0
    quantity: float = 0.0
    buyer_trader_id: str = ""
    seller_trader_id: str = ""
    bid_order_id: str = ""
    ask_order_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Account:
    account_id: str
    available_cash: float = 0.0
    locked_cash: float = 0.0
    holdings: dict[str, float] = field(default_factory=dict)

