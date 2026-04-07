from kivymd.app import MDApp
from engine import SapienEngine
from view import SapienView

class SapienApp(MDApp):
    def build(self):
        # Define a estética global do App
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple" 
        self.theme_cls.accent_palette = "Amber" # Cor para detalhes e botões de destaque

        # 1. Inicia o Motor de busca e extração do EPUB (LOM)
        try:
            engine = SapienEngine()
            
            # 2. Retorna o Gerenciador de Telas (HomeScreen + ReaderScreen)
            # Passamos a engine para que as telas possam acessar os dados
            return SapienView(engine=engine)
            
        except Exception as e:
            print(f"❌ Erro crítico ao iniciar o Sapien: {e}")
            return None

if __name__ == "__main__":
    # Garante que o App rode apenas se este arquivo for executado diretamente
    SapienApp().run()