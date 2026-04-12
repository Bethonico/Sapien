import os
import threading
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from database import SapienDB
from audio_manager import SapienAudio  # Importando o novo gerenciador

class SapienEngine:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.import_path = os.path.join(self.base_path, "import_zone")
        self.covers_path = os.path.join(self.base_path, "assets", "covers")
        
        # Garante as pastas base
        os.makedirs(self.import_path, exist_ok=True)
        os.makedirs(self.covers_path, exist_ok=True)
        
        # Inicializa os módulos
        self.db = SapienDB()
        self.audio = SapienAudio() # Agora o audio_manager gerencia os blocos

    def check_new_imports(self, on_progress=None, on_complete=None):
        """Roda em segundo plano para achar novos EPUBs na import_zone"""
        def _process():
            epubs = [f for f in os.listdir(self.import_path) if f.endswith('.epub')]
            if not epubs:
                if on_complete: on_complete(False)
                return

            for filename in epubs:
                novel_name = filename.replace('.epub', '')
                if not self.db.novel_exists(novel_name):
                    if on_progress: on_progress(f"Processando {novel_name}...")
                    filepath = os.path.join(self.import_path, filename)
                    self._parse_and_save_epub(novel_name, filepath)
            
            if on_complete: on_complete(True)
            
        threading.Thread(target=_process, daemon=True).start()

    def _parse_and_save_epub(self, name, filepath):
        try:
            book = epub.read_epub(filepath)
            cover_path = "assets/covers/default_cover.png" # Imagem padrão
            
            # 1. Tenta a capa oficial
            covers = list(book.get_items_of_type(ebooklib.ITEM_COVER))
            if covers:
                cover_path = os.path.join(self.covers_path, f"{name}_cover.jpg")
                with open(cover_path, "wb") as f:
                    f.write(covers[0].get_content())
            else:
                # 2. Fallback: Tenta pegar a primeira imagem que encontrar no livro
                images = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
                if images:
                    cover_path = os.path.join(self.covers_path, f"{name}_cover.jpg")
                    with open(cover_path, "wb") as f:
                        f.write(images[0].get_content())

            # Extrai os capítulos
            chapters_data = []
            items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            idx = 0
            
            for item in items:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text(separator='\n\n', strip=True)
                
                # Só salva se tiver texto real
                if len(text_content) > 300:
                    title_tag = soup.find(['h1', 'h2', 'h3'])
                    title = title_tag.get_text().strip() if title_tag else f"Capítulo {idx + 1}"
                    chapters_data.append({"idx": idx, "title": title, "content": text_content})
                    idx += 1
            
            print(f"✅ {name} importado com {len(chapters_data)} capítulos.")
            self.db.add_novel(name, cover_path, chapters_data)
            
        except Exception as e:
            print(f"❌ Erro em {name}: {e}")

    # --- Métodos de Biblioteca ---
    def get_library(self):
        return self.db.get_all_novels()

    def get_chapters_list(self, novel_name):
        return self.db.get_novel_chapters(novel_name)

    def get_chapter(self, novel_name, idx):
        return self.db.get_chapter_content(novel_name, idx)

    def update_reading_progress(self, novel_name, idx):
        self.db.update_progress(novel_name, idx)