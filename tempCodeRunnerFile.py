from kivymd.app import MDApp
from view import SapienView
from engine import SapienEngine

class SapienApp(MDApp):
    def build(self):
        # 1. Tema Nativo KivyMD (Modo Escuro)
        self.theme_cls.theme_style = "Dark"
        
        # 2. Paleta de Cores Sapien (Roxo Profundo)
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.primary_hue = "700" 
        self.theme_cls.accent_palette = "Purple"
        self.theme_cls.accent_hue = "A400"

        # Inicia a Engine e passa para a View
        engine = SapienEngine()
        return SapienView(engine=engine)

if __name__ == "__main__":
    SapienApp().run()