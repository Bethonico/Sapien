import os
import json
import threading # NOVA IMPORTAÇÃO
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

class SapienEngine:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(self.base_path, "assets")
        self.config_path = os.path.join(self.assets_path, "config.json")
        
        self.library = {} 
        self.current_novel_data = None
        self.chapters = []
        
        self.scan_library()

    def scan_library(self):
        if not os.path.exists(self.assets_path):
            os.makedirs(self.assets_path)
            return

        for folder in os.listdir(self.assets_path):
            folder_path = os.path.join(self.assets_path, folder)
            if os.path.isdir(folder_path):
                epubs = [f for f in os.listdir(folder_path) if f.endswith('.epub')]
                if epubs:
                    cover = os.path.join(folder_path, "cover.jpg")
                    if not os.path.exists(cover):
                        cover = "https://m.media-amazon.com/images/M/MV5BMWE1ZWYwZGUtZjRmOS00NzUzLTlkZmUtMTEwMjNhNTVmNDIwXkEyXkFqcGc@._V1_.jpg"
                    
                    self.library[folder] = {
                        "path": os.path.join(folder_path, epubs[0]),
                        "cover": cover,
                        "name": folder
                    }

    # CARREGAMENTO ASSÍNCRONO: Agora aceita um "callback" (uma função para chamar quando terminar)
    def load_novel_async(self, novel_name, on_complete):
        def _load_process():
            if novel_name in self.library:
                self.current_novel_data = self.library[novel_name]
                self.chapters = []
                try:
                    book = epub.read_epub(self.current_novel_data["path"])
                    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
                    
                    for item in items:
                        try:
                            content = item.get_content()
                            soup = BeautifulSoup(content, 'html.parser')
                            text_content = soup.get_text(strip=True)
                            if len(text_content) > 200: 
                                title_tag = soup.find(['h1', 'h2', 'h3'])
                                title = title_tag.get_text().strip() if title_tag else f"Capítulo {len(self.chapters) + 1}"
                                self.chapters.append({"title": title, "item": item})
                        except: continue
                    on_complete(True) # Avisa a View que terminou
                except Exception as e:
                    print(f"Erro ao ler EPUB: {e}")
                    on_complete(False)
            else:
                on_complete(False)
        
        # Inicia o processo em segundo plano para não travar a tela
        threading.Thread(target=_load_process, daemon=True).start()

    def get_content(self, index):
        if 0 <= index < len(self.chapters):
            content = self.chapters[index]["item"].get_content()
            return BeautifulSoup(content, 'html.parser').get_text(separator='\n').strip()
        return "Conteúdo indisponível."

    def save_progress(self, novel_name, index):
        config = self.load_full_config()
        if index < len(self.chapters):
            config[novel_name] = {
                "last_chapter": index,
                "title": self.chapters[index]["title"]
            }
            config["last_read"] = novel_name
            with open(self.config_path, "w") as f:
                json.dump(config, f)

    def load_full_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    def get_filtered_chapters(self, query=""):
        query = query.lower()
        return [(i, c["title"]) for i, c in enumerate(self.chapters) if query in c["title"].lower()]