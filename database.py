import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sapien.db")

class SapienDB:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS novels (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    name           TEXT    UNIQUE NOT NULL,
                    cover_path     TEXT,
                    total_chapters INTEGER DEFAULT 0,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chapters (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    novel_id INTEGER NOT NULL,
                    idx      INTEGER NOT NULL,
                    title    TEXT,
                    content  TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id),
                    UNIQUE (novel_id, idx)
                );
                CREATE TABLE IF NOT EXISTS progress (
                    novel_id    INTEGER PRIMARY KEY,
                    chapter_idx INTEGER DEFAULT 0,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                );
            """)

    # ── Novels ───────────────────────────────────────────────────────
    def novel_exists(self, name: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute("SELECT id FROM novels WHERE name = ?", (name,)).fetchone()
            return row is not None

    def add_novel(self, name: str, cover_path: str, chapters: list):
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO novels (name, cover_path, total_chapters) VALUES (?, ?, ?)",
                (name, cover_path, len(chapters))
            )
            novel_id = cur.lastrowid
            if novel_id:
                conn.executemany(
                    "INSERT OR IGNORE INTO chapters (novel_id, idx, title, content) VALUES (?,?,?,?)",
                    [(novel_id, c["idx"], c["title"], c["content"]) for c in chapters]
                )
                conn.execute(
                    "INSERT OR IGNORE INTO progress (novel_id, chapter_idx) VALUES (?, 0)",
                    (novel_id,)
                )

    def get_all_novels(self) -> list:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT n.id, n.name, n.cover_path, n.total_chapters,
                       COALESCE(p.chapter_idx, 0) AS last_chapter
                FROM novels n
                LEFT JOIN progress p ON p.novel_id = n.id
                ORDER BY p.updated_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    # ── Chapters ─────────────────────────────────────────────────────
    def get_novel_chapters(self, novel_name: str) -> list:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT c.idx, c.title FROM chapters c
                JOIN novels n ON n.id = c.novel_id
                WHERE n.name = ? ORDER BY c.idx
            """, (novel_name,)).fetchall()
            return [dict(r) for r in rows]

    def get_chapter_content(self, novel_name: str, idx: int) -> dict:
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT c.idx, c.title, c.content FROM chapters c
                JOIN novels n ON n.id = c.novel_id
                WHERE n.name = ? AND c.idx = ?
            """, (novel_name, idx)).fetchone()
            if not row:
                return {"idx": idx, "title": "Capítulo não encontrado", "content": ""}
            return dict(row)

    # ── Progress ──────────────────────────────────────────────────────
    def update_progress(self, novel_name: str, chapter_idx: int):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE progress SET chapter_idx = ?, updated_at = CURRENT_TIMESTAMP
                WHERE novel_id = (SELECT id FROM novels WHERE name = ?)
            """, (chapter_idx, novel_name))