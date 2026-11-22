import sqlite3
from contextlib import contextmanager
from app.core.config import get_settings
# SQLite keeps application state and citations. PDF passage text/vectors live
# separately in ChromaDB; this database stores their IDs and conversation links.
SCHEMA='''PRAGMA foreign_keys=ON;
-- Uploaded PDF registry and asynchronous ingestion status.
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,filename TEXT NOT NULL,sha256 TEXT NOT NULL UNIQUE,page_count INTEGER NOT NULL DEFAULT 0,title TEXT,status TEXT NOT NULL,error TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
-- Selected PDF scope, rolling conversation summary, and most recent topic.
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL DEFAULT 'New chat',summary TEXT NOT NULL DEFAULT '',selected_document_ids TEXT NOT NULL DEFAULT '[]',last_topic TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
-- User/assistant turns and the source citations shown below assistant answers.
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,role TEXT NOT NULL,content TEXT NOT NULL,sources_json TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
-- Passage IDs already used in a conversation, with their citation coordinates.
CREATE TABLE IF NOT EXISTS retrieved_chunks(conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,chunk_id TEXT NOT NULL,page_number INTEGER,section_title TEXT,PRIMARY KEY(conversation_id,chunk_id));'''
@contextmanager
def connection():
    """Open a foreign-key-aware SQLite connection and commit on success."""
    db=sqlite3.connect(get_settings().sqlite_path,timeout=30); db.row_factory=sqlite3.Row; db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db; db.commit()
    finally: db.close()
def init_db():
    """Create application tables on backend startup if they do not exist."""
    with connection() as db: db.executescript(SCHEMA)
