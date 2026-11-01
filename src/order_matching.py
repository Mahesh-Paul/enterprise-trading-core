"""
src/order_matching.py

Asynchronous High-Frequency Trading (HFT) Order Matching Engine.
Features an asynchronous order book, multi-asset matching loop, and settlement ledger.

================================================================================
BUG #3: CRITICAL ASYNCHRONOUS RACE CONDITION (TOCTOU & NON-ATOMIC YIELD)
================================================================================
Location:
    AsyncMatchingEngine._execute_match_loop() and AsyncMatchingEngine.submit_order()

Root Cause:
    1. The developer assumed Python's single-threaded asyncio event loop prevents
       state corruption without needing synchronization primitives (asyncio.Lock).
    2. However, order processing requires asynchronous side effects (e.g., WAL
       persistence, margin verification, or audit logging).
    3. The engine yields control to the event loop (`await self._async_settle_match(...)`)
       AFTER reading the best available resting order, but BEFORE decrementing
       `remaining_quantity` and before popping the resting order from the order book.
    4. Concurrently scheduled coroutines (e.g., via asyncio.gather or high-throughput
       WebSocket connections) see the stale resting liquidity and match against it.
    5. Result:
       - Resting orders are overfilled, driving `remaining_quantity` into negative numbers.
       - Phantom shares/tokens are generated out of thin air.
       - Double-spend vulnerabilities allow cash overdrafts without margin collateral.
================================================================================
"""

import asyncio
from dataclasses import dataclass, field
import logging
from typing import Optional

from src.models import Account, Order, OrderStatus, OrderType, Side, Trade

logger = logging.getLogger("matching_engine")


class OrderBook:
    """
    In-memory Level-2 order book maintaining price-time priority.
    Bids are sorted descending by price, ascending by timestamp.
    Asks are sorted ascending by price, ascending by timestamp.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: list[Order] = []
        self.asks: list[Order] = []

    def add_limit_order(self, order: Order) -> None:
        if order.side == Side.BUY:
            self.bids.append(order)
            # Sort bids: highest price first, earliest timestamp first
            self.bids.sort(key=lambda o: (-o.price, o.timestamp))
        else:
            self.asks.append(order)
            # Sort asks: lowest price first, earliest timestamp first
            self.asks.sort(key=lambda o: (o.price, o.timestamp))

    def remove_order(self, order_id: str, side: Side) -> Optional[Order]:
        book = self.bids if side == Side.BUY else self.asks
        for idx, o in enumerate(book):
            if o.order_id == order_id:
                return book.pop(idx)
        return None

    def get_best_bid(self) -> Optional[Order]:
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[Order]:
        return self.asks[0] if self.asks else None


class AsyncMatchingEngine:
    """
    Asynchronous Matching Engine processing market and limit orders.
    Designed for high throughput with async auditing and event streaming.
    """

    def __init__(self):
        self.books: dict[str, OrderBook] = {}
        self.accounts: dict[str, Account] = {}
        self.trade_history: list[Trade] = []
        self.submitted_orders: dict[str, Order] = {}

    def get_or_create_book(self, symbol: str) -> OrderBook:
        if symbol not in self.books:
            self.books[symbol] = OrderBook(symbol)
        return self.books[symbol]

    def register_account(self, account: Account) -> None:
        self.accounts[account.account_id] = account

    async def _async_pretrade_risk_check(self, order: Order) -> None:
        """
        Simulates an asynchronous external risk & margin verification service.
        Yields execution to the event loop.
        """
        await asyncio.sleep(0.005)

    async def _async_settle_match(
        self, incoming: Order, resting: Order, match_qty: float, match_price: float
    ) -> None:
        """
        Simulates asynchronous clearing, transaction log persistence,
        and Kafka event publishing. Yields execution to the event loop.
        """
        await asyncio.sleep(0.01)

    async def submit_order(self, order: Order) -> list[Trade]:
        """
        Submits and matches an order asynchronously.
        
        CRITICAL VULNERABILITY (Check-Then-Act Race Condition):
        Cash balance check occurs before an async yield (_async_pretrade_risk_check).
        Funds are deducted only AFTER the yield, enabling concurrent double-spending.
        """
        self.submitted_orders[order.order_id] = order
        account = self.accounts.get(order.trader_id)

        # Pre-trade capital allocation check
        if account and order.side == Side.BUY:
            required_funds = order.price * order.quantity
            # TIME-OF-CHECK: Inspect available funds
            if account.available_cash < required_funds:
                order.status = OrderStatus.REJECTED
                raise ValueError(
                    f"Insufficient funds for trader {order.trader_id}: "
                    f"Required ${required_funds:.2f}, Available ${account.available_cash:.2f}"
                )

            # ASYNC YIELD POINT: Context switches back to event loop!
            # Concurrent orders from the same trader pass the balance check simultaneously!
            await self._async_pretrade_risk_check(order)

            # TIME-OF-USE: Non-atomic deduction after yield point
            account.available_cash -= required_funds
            account.locked_cash += required_funds

        # Proceed to order book execution loop
        return await self._execute_match_loop(order)

    async def _execute_match_loop(self, incoming_order: Order) -> list[Trade]:
        """
        Matches incoming order against resting liquidity in the book.

        CRITICAL BUG (Non-Atomic Matching & Asynchronous Interleaving):
        During matching, the engine detects the best resting order, determines
        the match quantity, and then awaits `_async_settle_match`.
        Because the resting order's `remaining_quantity` is NOT decremented
        before the await, and the order is NOT locked or removed from the book,
        any other concurrent coroutine reading the order book will match the
        SAME resting liquidity, causing severe overfills and phantom shares!
        """
        book = self.get_or_create_book(incoming_order.symbol)
        trades: list[Trade] = []

        opposite_book = book.asks if incoming_order.side == Side.BUY else book.bids

        while incoming_order.remaining_quantity > 0 and opposite_book:
            best_match = opposite_book[0]

            # Price cross validation
            if incoming_order.side == Side.BUY and incoming_order.price < best_match.price:
                break
            if incoming_order.side == Side.SELL and incoming_order.price > best_match.price:
                break

            # Calculate match quantity based on STALE state
            match_qty = min(incoming_order.remaining_quantity, best_match.remaining_quantity)
            if match_qty <= 0:
                break

            match_price = best_match.price

            # ==================================================================
            # SEVERE CONCURRENCY BUG OCCURS HERE:
            # Yielding to event loop while leaving best_match in the opposite_book
            # with its un-decremented remaining_quantity!
            # ==================================================================
            await self._async_settle_match(incoming_order, best_match, match_qty, match_price)

            # Execution resumes: Task mutates state non-atomically
            incoming_order.remaining_quantity -= match_qty
            incoming_order.filled_quantity += match_qty

            # Resting order quantity decremented post-yield (can drop below zero!)
            best_match.remaining_quantity -= match_qty
            best_match.filled_quantity += match_qty

            if best_match.remaining_quantity <= 0:
                best_match.status = OrderStatus.FILLED
                if opposite_book and opposite_book[0].order_id == best_match.order_id:
                    opposite_book.pop(0)
            else:
                best_match.status = OrderStatus.PARTIALLY_FILLED

            trade = Trade(
                symbol=incoming_order.symbol,
                price=match_price,
                quantity=match_qty,
                buyer_trader_id=incoming_order.trader_id if incoming_order.side == Side.BUY else best_match.trader_id,
                seller_trader_id=best_match.trader_id if incoming_order.side == Side.BUY else incoming_order.trader_id,
                bid_order_id=incoming_order.order_id if incoming_order.side == Side.BUY else best_match.order_id,
                ask_order_id=best_match.order_id if incoming_order.side == Side.BUY else incoming_order.order_id,
            )
            trades.append(trade)
            self.trade_history.append(trade)

        # Update incoming order status
        if incoming_order.remaining_quantity == 0:
            incoming_order.status = OrderStatus.FILLED
        elif incoming_order.filled_quantity > 0:
            incoming_order.status = OrderStatus.PARTIALLY_FILLED
            book.add_limit_order(incoming_order)
        else:
            incoming_order.status = OrderStatus.NEW
            book.add_limit_order(incoming_order)

        return trades

