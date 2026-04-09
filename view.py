from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.uix.screenmanager import FadeTransition 
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDRectangleFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.dialog import MDDialog
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock, mainthread # Necessário para atualizar a tela após o Threading

class SapienView(MDScreenManager):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.transition = FadeTransition(duration=0.2)
        self.engine = engine
        self.add_widget(NetflixHome(name="home", view=self))
        self.add_widget(ReaderScreen(name="reader", view=self))

class NetflixHome(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        main_layout = BoxLayout(orientation='vertical', padding="20dp", spacing="20dp")
        
        main_layout.add_widget(MDLabel(text="SAPIEN", font_style="H4", bold=True, 
                                      theme_text_color="Custom", text_color=(0.6, 0.4, 1, 1), 
                                      size_hint_y=None, height="60dp"))

        config = self.view.engine.load_full_config()
        last_novel = config.get("last_read")
        
        if last_novel and last_novel in self.view.engine.library:
            main_layout.add_widget(MDLabel(text="Continuar Lendo", font_style="H6", bold=True, size_hint_y=None, height="30dp"))
            data = self.view.engine.library[last_novel]
            progresso = config.get(last_novel, {"title": "Início", "last_chapter": 0})
            
            hero_card = MDCard(size_hint=(1, None), height="150dp", radius=[15,], md_bg_color=(0.18, 0.12, 0.3, 1), 
                               on_release=lambda x: self.start_loading_novel(last_novel))
            hero_box = BoxLayout(padding="10dp", spacing="15dp")
            hero_box.add_widget(AsyncImage(source=data["cover"], size_hint_x=0.3))
            
            info = BoxLayout(orientation='vertical', padding="5dp")
            info.add_widget(MDLabel(text=last_novel, bold=True, font_style="H6"))
            info.add_widget(MDLabel(text=f"Último: {progresso['title']}", theme_text_color="Hint"))
            hero_box.add_widget(info)
            hero_card.add_widget(hero_box)
            main_layout.add_widget(hero_card)
        
        main_layout.add_widget(MDLabel(text="Minha Estante", font_style="H6", bold=True, size_hint_y=None, height="30dp"))
        
        h_scroll = MDScrollView(do_scroll_x=True, do_scroll_y=False, size_hint=(1, None), height="220dp")
        shelf = BoxLayout(orientation='horizontal', spacing="15dp", size_hint_x=None, padding="5dp")
        shelf.bind(minimum_width=shelf.setter('width'))

        for name, data in self.view.engine.library.items():
            novel_card = MDCard(orientation='vertical', size_hint=(None, None), size=("130dp", "190dp"), 
                                radius=[10,], md_bg_color=(0,0,0,0), on_release=lambda x, n=name: self.start_loading_novel(n))
            novel_card.add_widget(AsyncImage(source=data["cover"], allow_stretch=True, keep_ratio=False))
            shelf.add_widget(novel_card)

        h_scroll.add_widget(shelf)
        main_layout.add_widget(h_scroll)
        main_layout.add_widget(BoxLayout()) 
        self.add_widget(main_layout)

    def start_loading_novel(self, name):
        # Vai para a tela de leitura imediatamente e mostra "Carregando..."
        reader = self.view.get_screen("reader")
        reader.show_loading()
        self.view.current = "reader"
        
        # Pede para a Engine carregar o livro no fundo
        self.view.engine.load_novel_async(name, lambda success: self.finish_loading_novel(name, success))

    @mainthread
    def finish_loading_novel(self, name, success):
        # Esta função roda quando a Engine termina o carregamento
        if success:
            config = self.view.engine.load_full_config()
            cap_idx = config.get(name, {}).get("last_chapter", 0)
            
            reader = self.view.get_screen("reader")
            reader.update_list()
            reader.load_chapter(cap_idx)

class ReaderScreen(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.fullscreen = False
        self.current_index = 0
        self.font_size_sp = 16 # Tamanho da fonte padrão
        self.settings_dialog = None
        self.build_ui()
        self.set_theme("dark") # Inicia no modo escuro

    def build_ui(self):
        self.main_layout = BoxLayout(orientation='vertical')
        
        # Adicionado botão de Engrenagem (cog)
        self.toolbar = MDTopAppBar(
            title="Leitor",
            left_action_items=[["menu", lambda x: self.nav_drawer.set_state("open")]],
            right_action_items=[
                ["cog", lambda x: self.open_settings()],
                ["fullscreen", lambda x: self.toggle_fullscreen()], 
                ["home", lambda x: self.go_home()]
            ]
        )
        self.main_layout.add_widget(self.toolbar)

        # BARRA DE PROGRESSO (NOVO)
        self.progress_bar = MDProgressBar(value=0, color=(0.6, 0.4, 1, 1), size_hint_y=None, height="4dp")
        self.main_layout.add_widget(self.progress_bar)

        reader_area = AnchorLayout()
        
        # Fundo do leitor (para podermos mudar de cor no Modo Sépia)
        self.bg_card = MDCard(radius=[0,], md_bg_color=(0.12, 0.07, 0.2, 1))
        
        self.scroll = MDScrollView()
        self.text_label = MDLabel(text="Carregando livro...\nPor favor aguarde.", padding=(30, 50), size_hint_y=None, 
                                  theme_text_color="Custom", text_color=(1, 1, 1, 1), 
                                  font_style="Body1", font_size=f"{self.font_size_sp}sp", line_height=1.5)
        self.text_label.bind(texture_size=self.text_label.setter('size'))
        self.scroll.add_widget(self.text_label)
        self.bg_card.add_widget(self.scroll)
        reader_area.add_widget(self.bg_card)

        nav_buttons = BoxLayout(orientation='horizontal', padding="20dp", size_hint=(1, None), height="100dp")
        nav_buttons.add_widget(MDIconButton(icon="chevron-left", icon_size="44sp", theme_text_color="Custom", 
                                           text_color=(0.5,0.5,0.5,0.8), on_release=lambda x: self.change_chapter(-1)))
        nav_buttons.add_widget(BoxLayout()) 
        nav_buttons.add_widget(MDIconButton(icon="chevron-right", icon_size="44sp", theme_text_color="Custom", 
                                           text_color=(0.5,0.5,0.5,0.8), on_release=lambda x: self.change_chapter(1)))
        
        reader_area.add_widget(nav_buttons)
        self.main_layout.add_widget(reader_area)
        self.add_widget(self.main_layout)

        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0), md_bg_color=(0.15, 0.1, 0.25, 1))
        drawer_content = BoxLayout(orientation='vertical', padding="12dp", spacing="10dp")
        
        self.search_bar = MDTextField(hint_text="Buscar capítulo...", mode="round", fill_color_normal=(1,1,1,0.1))
        self.search_bar.bind(text=self.schedule_search)
        drawer_content.add_widget(self.search_bar)

        self.chapter_list_widget = MDList()
        ds = MDScrollView()
        ds.add_widget(self.chapter_list_widget)
        drawer_content.add_widget(ds)
        self.nav_drawer.add_widget(drawer_content)
        self.add_widget(self.nav_drawer)

        self.exit_fs_btn = MDIconButton(icon="fullscreen-exit", pos_hint={'right': 1, 'top': 1}, theme_text_color="Custom", 
                                        text_color=(1,1,1,0.5), on_release=lambda x: self.toggle_fullscreen())

    def show_loading(self):
        self.text_label.text = "Processando arquivo EPUB...\nIsso pode levar alguns segundos dependendo do tamanho do livro."
        self.toolbar.title = "Carregando..."
        self.progress_bar.value = 0

    # -------- CONFIGURAÇÕES (HUD) --------
    def open_settings(self):
        if not self.settings_dialog:
            content = BoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None, height="120dp")
            
            # Controles de Fonte
            font_box = BoxLayout(orientation="horizontal", spacing="10dp")
            font_box.add_widget(MDLabel(text="Tamanho da Fonte:", halign="left"))
            font_box.add_widget(MDIconButton(icon="minus", on_release=lambda x: self.adjust_font(-2)))
            font_box.add_widget(MDIconButton(icon="plus", on_release=lambda x: self.adjust_font(2)))
            content.add_widget(font_box)

            # Controles de Tema
            theme_box = BoxLayout(orientation="horizontal", spacing="10dp")
            theme_box.add_widget(MDRectangleFlatButton(text="Modo Escuro", on_release=lambda x: self.set_theme("dark")))
            theme_box.add_widget(MDRectangleFlatButton(text="Modo Sépia", on_release=lambda x: self.set_theme("sepia")))
            content.add_widget(theme_box)

            self.settings_dialog = MDDialog(
                title="Configurações de Leitura",
                type="custom",
                content_cls=content,
            )
        self.settings_dialog.open()

    def adjust_font(self, amount):
        self.font_size_sp += amount
        # Limites de tamanho
        if self.font_size_sp < 12: self.font_size_sp = 12
        if self.font_size_sp > 32: self.font_size_sp = 32
        self.text_label.font_size = f"{self.font_size_sp}sp"

    def set_theme(self, mode):
        if mode == "dark":
            self.bg_card.md_bg_color = (0.12, 0.07, 0.2, 1) # Roxo escuro Sapien
            self.text_label.text_color = (1, 1, 1, 0.8)     # Branco 80%
            self.toolbar.md_bg_color = (0.12, 0.07, 0.2, 1)
        elif mode == "sepia":
            self.bg_card.md_bg_color = (0.96, 0.89, 0.76, 1) # Sépia (bege)
            self.text_label.text_color = (0.2, 0.1, 0, 1)    # Marrom escuro
            self.toolbar.md_bg_color = (0.8, 0.7, 0.55, 1)   # Topbar bege escuro

    # -------------------------------------

    def schedule_search(self, instance, value):
        Clock.unschedule(self.update_list)
        Clock.schedule_once(lambda dt: self.update_list(value), 0.3)

    def update_list(self, query=""):
        self.chapter_list_widget.clear_widgets()
        filtered = self.view.engine.get_filtered_chapters(query)
        for idx, title in filtered[:100]:
            item = OneLineListItem(text=title, theme_text_color="Custom", text_color=(1,1,1,0.8),
                                   on_release=lambda x, i=idx: self.load_chapter(i))
            self.chapter_list_widget.add_widget(item)

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.main_layout.remove_widget(self.toolbar)
            self.add_widget(self.exit_fs_btn)
            self.fullscreen = True
        else:
            self.main_layout.add_widget(self.toolbar, index=1)
            self.remove_widget(self.exit_fs_btn)
            self.fullscreen = False

    def change_chapter(self, direction):
        new_index = self.current_index + direction
        if 0 <= new_index < len(self.view.engine.chapters):
            self.load_chapter(new_index)

    def load_chapter(self, index):
        if not self.view.engine.chapters: return
        self.current_index = index
        self.text_label.text = self.view.engine.get_content(index)
        self.toolbar.title = self.view.engine.chapters[index]["title"]
        self.view.engine.save_progress(self.view.engine.current_novel_data["name"], index)
        
        # Atualiza a barra de progresso
        progresso = (index + 1) / len(self.view.engine.chapters) * 100
        self.progress_bar.value = progresso

        self.nav_drawer.set_state("close")
        self.scroll.scroll_y = 1

    def go_home(self):
        if self.settings_dialog:
            self.settings_dialog.dismiss()
        self.view.get_screen("home").build_ui()
        self.view.current = "home"