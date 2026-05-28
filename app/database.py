from collections.abc import Iterator
from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "agentic_economy.db"


def connect(db_path: Path | str = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def init_db(connection: sqlite3.Connection | None = None) -> None:
    owns_connection = connection is None
    db = connection or connect()
    try:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                agent_type TEXT NOT NULL,
                owner_wallet TEXT NOT NULL,
                chain_id INTEGER NOT NULL DEFAULT 5000,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failed', 'error')),
                value_usd REAL NOT NULL DEFAULT 0,
                tx_hash TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
                status TEXT NOT NULL CHECK (status IN ('open', 'confirmed', 'dismissed')) DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marketplace_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL UNIQUE,
                pricing_model TEXT NOT NULL CHECK (pricing_model IN ('buy', 'rent_hourly', 'rent_daily', 'per_task')),
                price_usd REAL NOT NULL CHECK (price_usd >= 0),
                price_token TEXT NOT NULL DEFAULT 'USD',
                availability TEXT NOT NULL CHECK (availability IN ('available', 'rented', 'paused')) DEFAULT 'available',
                capabilities_json TEXT NOT NULL DEFAULT '[]',
                terms TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                renter_wallet TEXT NOT NULL,
                task_title TEXT NOT NULL,
                task_description TEXT NOT NULL DEFAULT '',
                duration_hours INTEGER NOT NULL DEFAULT 1 CHECK (duration_hours > 0),
                agreed_price_usd REAL NOT NULL CHECK (agreed_price_usd >= 0),
                status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'completed', 'disputed', 'cancelled')) DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (listing_id) REFERENCES marketplace_listings(id) ON DELETE CASCADE,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS wallet_auth_nonces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                chain_id INTEGER NOT NULL DEFAULT 5000,
                nonce TEXT NOT NULL,
                message TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_automation_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL UNIQUE,
                automation_enabled INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL DEFAULT 'manual' CHECK(mode IN ('manual', 'semi_auto', 'full_auto')),
                max_tx_value_usd REAL NOT NULL DEFAULT 0,
                daily_limit_usd REAL NOT NULL DEFAULT 0,
                max_transactions_per_hour INTEGER NOT NULL DEFAULT 0,
                min_native_balance_wei TEXT NOT NULL DEFAULT '0',
                require_confirmation_above_usd REAL NOT NULL DEFAULT 0,
                allowed_chain_ids_json TEXT NOT NULL DEFAULT '[]',
                allowed_tokens_json TEXT NOT NULL DEFAULT '[]',
                allowed_recipients_json TEXT NOT NULL DEFAULT '[]',
                allowed_actions_json TEXT NOT NULL DEFAULT '[]',
                emergency_stop INTEGER NOT NULL DEFAULT 0,
                smart_account_address TEXT,
                delegation_id TEXT,
                delegation_status TEXT NOT NULL DEFAULT 'none' CHECK(delegation_status IN ('none', 'requested', 'active', 'revoked', 'expired')),
                delegation_scope_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_automation_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                to_address TEXT NOT NULL,
                token_address TEXT,
                value_wei TEXT NOT NULL,
                value_usd REAL NOT NULL DEFAULT 0,
                chain_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared', 'requires_confirmation', 'delegation_required', 'executed', 'rejected', 'failed')),
                tx_hash TEXT,
                reason TEXT,
                rejection_reason TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                action TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );
            """
        )
        db.commit()
    finally:
        if owns_connection:
            db.close()
