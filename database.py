import sqlite3
import os

class SapienDB:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.base_path, "assets")
        self.db_path = os.path.join(self.assets_path, "library.db")
        
        if not os.path.exists(self.assets_path):
            os.makedirs(self.assets_path)
            
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS novels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE,
                            cover_path TEXT,
                            last_chapter_idx INTEGER DEFAULT 0)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS chapters (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            novel_id INTEGER,
                            title TEXT,
                            content TEXT,
                            chapter_idx INTEGER,
                            FOREIGN KEY(novel_id) REFERENCES novels(id))''')
        conn.commit()
        conn.close()

    def novel_exists(self, name):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM novels WHERE name = ?", (name,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_novel(self, name, cover_path, chapters_data):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Insere o livro
            cursor.execute("INSERT OR IGNORE INTO novels (name, cover_path) VALUES (?, ?)", (name, cover_path))
            novel_id = cursor.execute("SELECT id FROM novels WHERE name = ?", (name,)).fetchone()[0]
            
            # Insere os capítulos
            for cap in chapters_data:
                cursor.execute("INSERT INTO chapters (novel_id, title, content, chapter_idx) VALUES (?, ?, ?, ?)",
                               (novel_id, cap['title'], cap['content'], cap['idx']))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao salvar no DB: {e}")
            return False
        finally:
            conn.close()

    def get_all_novels(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, cover_path, last_chapter_idx FROM novels")
        novels = [{"name": r[0], "cover": r[1], "last_chapter": r[2]} for r in cursor.fetchall()]
        conn.close()
        return novels

    def get_novel_chapters(self, novel_name):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT chapters.chapter_idx, chapters.title 
                          FROM chapters JOIN novels ON chapters.novel_id = novels.id 
                          WHERE novels.name = ? ORDER BY chapter_idx''', (novel_name,))
        chapters = [{"idx": r[0], "title": r[1]} for r in cursor.fetchall()]
        conn.close()
        return chapters

    def get_chapter_content(self, novel_name, chapter_idx):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT chapters.title, chapters.content 
                          FROM chapters JOIN novels ON chapters.novel_id = novels.id 
                          WHERE novels.name = ? AND chapters.chapter_idx = ?''', (novel_name, chapter_idx))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"title": result[0], "content": result[1]}
        return {"title": "Erro", "content": "Conteúdo não encontrado no banco de dados."}

    def update_progress(self, novel_name, chapter_idx):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE novels SET last_chapter_idx = ? WHERE name = ?", (chapter_idx, novel_name))
        conn.commit()
        conn.close()