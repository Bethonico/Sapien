import os
import threading
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from database import SapienDB

class SapienEngine:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.import_path = os.path.join(self.base_path, "import_zone")
        self.covers_path = os.path.join(self.base_path, "assets", "covers")
        
        # Garante que as pastas existam
        os.makedirs(self.import_path, exist_ok=True)
        os.makedirs(self.covers_path, exist_ok=True)
        
        self.db = SapienDB()

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
                    # Opcional: mover ou deletar o arquivo após importar
                    # os.remove(filepath) 
            
            if on_complete: on_complete(True)
            
        threading.Thread(target=_process, daemon=True).start()

    def _parse_and_save_epub(self, name, filepath):
        try:
            book = epub.read_epub(filepath)
            
            # Tenta pegar uma capa (fallback para imagem da web)
            cover_path = "https://m.media-amazon.com/images/M/MV5BMWE1ZWYwZGUtZjRmOS00NzUzLTlkZmUtMTEwMjNhNTVmNDIwXkEyXkFqcGc@._V1_.jpg"
            for item in book.get_items_of_type(ebooklib.ITEM_COVER):
                local_cover = os.path.join(self.covers_path, f"{name}_cover.jpg")
                with open(local_cover, "wb") as f:
                    f.write(item.get_content())
                cover_path = local_cover
                break

            # Extrai os capítulos
            chapters_data = []
            items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            idx = 0
            
            for item in items:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text(separator='\n\n', strip=True)
                
                # Só salva se tiver texto real (ignora páginas de créditos, etc)
                if len(text_content) > 300:
                    title_tag = soup.find(['h1', 'h2', 'h3'])
                    title = title_tag.get_text().strip() if title_tag else f"Capítulo {idx + 1}"
                    chapters_data.append({"idx": idx, "title": title, "content": text_content})
                    idx += 1
            
            self.db.add_novel(name, cover_path, chapters_data)
        except Exception as e:
            print(f"Erro ao fazer o parse de {name}: {e}")

    # --- Métodos de Consumo da View (Acesso Rápido) ---
    def get_library(self):
        return self.db.get_all_novels()

    def get_chapters_list(self, novel_name):
        return self.db.get_novel_chapters(novel_name)

    def get_chapter(self, novel_name, idx):
        return self.db.get_chapter_content(novel_name, idx)

    def update_reading_progress(self, novel_name, idx):
        self.db.update_progress(novel_name, idx)
def _parse_and_save_epub(self, name, filepath):
        try:
            book = epub.read_epub(filepath)
            cover_path = "assets/covers/default_cover.png" # Tenha uma imagem padrão
            
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

            # ... (seu código de extração de capítulos)
            
            # Adicione um print para debugar no VS Code
            print(f"✅ {name} importado com {len(chapters_data)} capítulos.")
            self.db.add_novel(name, cover_path, chapters_data)
            
        except Exception as e:
            print(f"❌ Erro em {name}: {e}")