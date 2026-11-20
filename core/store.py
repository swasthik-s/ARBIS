"""SQLite persistence for observations, candidates and paper trades."""
import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str = "data/arbis.sqlite3"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at TEXT NOT NULL,
                    exchange_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_observations_time
                    ON observations(observed_at);
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    buy_exchange TEXT NOT NULL,
                    sell_exchange TEXT NOT NULL,
                    net_pnl REAL NOT NULL,
                    net_edge_pct REAL NOT NULL,
                    route_key TEXT UNIQUE,
                    payload TEXT NOT NULL
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(paper_trades)")}
            if "route_key" not in columns:
                db.execute("ALTER TABLE paper_trades ADD COLUMN route_key TEXT")
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_route_key ON paper_trades(route_key)")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def record_observation(self, exchange_id: str, symbol: str, observed_at: str, payload: dict[str, Any]):
        with self._connect() as db:
            db.execute(
                "INSERT INTO observations(observed_at,exchange_id,symbol,payload) VALUES(?,?,?,?)",
                (observed_at, exchange_id, symbol, json.dumps(payload, allow_nan=False)),
            )

    def record_trade(self, trade: dict[str, Any]) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO paper_trades
                (id,created_at,symbol,buy_exchange,sell_exchange,net_pnl,net_edge_pct,route_key,payload)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (trade["id"], trade["created_at"], trade["symbol"],
                 trade["buy_exchange"], trade["sell_exchange"],
                 trade["net_pnl"], trade["net_edge_pct"], trade.get("route_key"),
                 json.dumps(trade, allow_nan=False)),
            )
            return cursor.rowcount == 1

    def summary(self) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                """SELECT COUNT(*), COALESCE(SUM(net_pnl),0),
                COALESCE(AVG(net_pnl),0),
                COALESCE(SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END),0)
                FROM paper_trades"""
            ).fetchone()
        count, pnl, avg, wins = row
        return {
            "trades": count, "net_pnl": pnl, "average_pnl": avg,
            "win_rate_pct": (wins / count * 100) if count else None,
        }
