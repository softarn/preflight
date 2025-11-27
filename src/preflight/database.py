import sqlite3
from pathlib import Path
from datetime import datetime
from preflight.ai_reviewer import ReviewIssue

class Database:
    def __init__(self, db_path: Path = Path.home() / ".preflight" / "reviews.db"):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Create table with new schema if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT,
                start_line INTEGER,
                end_line INTEGER,
                severity TEXT,
                description TEXT,
                suggestion TEXT,
                code_snippet TEXT,
                commit_hash TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Migration: Check if commit_hash column exists, add if missing
        cursor.execute("PRAGMA table_info(issues)")
        columns = [info[1] for info in cursor.fetchall()]
        if "commit_hash" not in columns:
            cursor.execute("ALTER TABLE issues ADD COLUMN commit_hash TEXT")
            
        self.conn.commit()

    def save_issue(self, issue: ReviewIssue, commit_hash: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO issues (
                file, start_line, end_line, severity, description, suggestion, code_snippet, commit_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue.file,
            issue.line.start,
            issue.line.end,
            issue.severity,
            issue.description,
            issue.suggestion,
            issue.codeSnippet,
            commit_hash,
            datetime.now()
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()
