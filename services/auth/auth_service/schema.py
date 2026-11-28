"""auth-db sxemasi."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'courier')),
    active INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username),
    token_hash TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    replaced_by TEXT
);
CREATE INDEX IF NOT EXISTS refresh_tokens_user ON refresh_tokens (username, revoked_at);
"""
