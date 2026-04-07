import os
import json
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

class SapienEngine:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.base_path, "assets")
        self.epub_path = os.path.join(self.assets_path, "lom.epub")
        self.config_path = os.path.join(self.assets_path, "config.json")
        
        self.library_data = {
            "Lord of the Mysteries": {
                "cover": "https://m.media-amazon.com/images/M/MV5BMWE1ZWYwZGUtZjRmOS00NzUzLTlkZmUtMTEwMjNhNTVmNDIwXkEyXkFqcGc@._V1_.jpg",
                "description": "Com o despertar do vapor e da maquinaria, quem poderá chegar a ser um 'Extraordinário'?",
                "file": "lom.epub"
            }
        }
        
        self.chapters = []
        if os.path.exists(self.epub_path):
            self.book = epub.read_epub(self.epub_path)
            self._load_chapters()

    def _load_chapters(self):
        items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        for item in items:
            try:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                title_tag = soup.find(['h1', 'h2', 'h3'])
                title = title_tag.get_text().strip() if title_tag else f"Capítulo {len(self.chapters) + 1}"
                self.chapters.append({"title": title, "item": item})
            except: continue

    def get_content(self, index):
        if 0 <= index < len(self.chapters):
            content = self.chapters[index]["item"].get_content()
            return BeautifulSoup(content, 'html.parser').get_text(separator='\n').strip()
        return ""

    def save_progress(self, index):
        config = self.load_full_config()
        config["last_chapter"] = index
        config["last_chapter_title"] = self.chapters[index]["title"]
        with open(self.config_path, "w") as f:
            json.dump(config, f)

    def load_full_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {"last_chapter": 0, "last_chapter_title": "Início", "history": []}

    def get_filtered_chapters(self, query=""):
        query = query.lower()
        return [(i, c["title"]) for i, c in enumerate(self.chapters) if query in c["title"].lower()]