from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.uix.screenmanager import FadeTransition 
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDRectangleFlatButton, MDFillRoundFlatButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock, mainthread
from kivy.animation import Animation

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
        self.bg_container = MDBoxLayout(orientation='vertical', md_bg_color=(0.02, 0.01, 0.04, 1))
        
        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height="80dp", padding=("20dp", "10dp"))
        header.add_widget(MDLabel(
            text="SAPIEN", font_style="H4", bold=True, 
            theme_text_color="Custom", text_color=(0.6, 0.4, 1, 1)
        ))
        sync_btn = MDIconButton(icon="sync", theme_icon_color="Custom", icon_color=(0.6, 0.4, 1, 1),
                                on_release=lambda x: self.import_new_books())
        header.add_widget(sync_btn)
        self.bg_container.add_widget(header)

        self.main_scroll = MDScrollView(scroll_type=['bars', 'content'], smooth_scroll_end=10)
        self.content_layout = MDBoxLayout(orientation='vertical', padding="20dp", spacing="30dp", size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))

        self.load_sections()
        
        self.main_scroll.add_widget(self.content_layout)
        self.bg_container.add_widget(self.main_scroll)
        self.add_widget(self.bg_container)

    def load_sections(self):
        self.content_layout.clear_widgets()
        novels = self.view.engine.get_library()
        
        if not novels:
            self.content_layout.add_widget(MDLabel(
                text="Sua estante está esperando por histórias...", 
                halign="center", theme_text_color="Hint", size_hint_y=None, height="200dp"
            ))
            return

        last = novels[0]
        hero_card = MDCard(
            orientation='horizontal', size_hint=(1, None), height="180dp",
            radius=[20,], md_bg_color=(0.1, 0.05, 0.2, 1), padding="15dp", elevation=4
        )
        
        hero_cover = MDCard(size_hint=(None, 1), width="110dp", radius=[10,], elevation=0)
        hero_cover.add_widget(AsyncImage(source=last["cover"], allow_stretch=True, keep_ratio=False))
        hero_card.add_widget(hero_cover)
        
        hero_info = MDBoxLayout(orientation='vertical', padding=("20dp", 0))
        hero_info.add_widget(MDLabel(text="CONTINUAR LENDO", font_style="Overline", theme_text_color="Hint"))
        hero_info.add_widget(MDLabel(text=last["name"], font_style="H5", bold=True))
        hero_info.add_widget(MDLabel(text=f"Capítulo {last['last_chapter'] + 1}", theme_text_color="Secondary"))
        hero_info.add_widget(MDFillRoundFlatButton(
            text="RETOMAR AGORA", md_bg_color=(0.6, 0.4, 1, 1),
            on_release=lambda x, n=last["name"], c=last["last_chapter"]: self.open_novel(n, c)
        ))
        hero_card.add_widget(hero_info)
        self.content_layout.add_widget(hero_card)

        self.content_layout.add_widget(MDLabel(text="Minha Biblioteca", font_style="H6", bold=True))
        
        shelf_scroll = MDScrollView(do_scroll_x=True, do_scroll_y=False, size_hint=(1, None), height="220dp")
        shelf = MDBoxLayout(orientation='horizontal', spacing="15dp", size_hint_x=None, padding="5dp")
        shelf.bind(minimum_width=shelf.setter('width'))

        for novel in novels:
            novel_card = MDCard(
                orientation='vertical', size_hint=(None, None), size=("130dp", "190dp"), 
                radius=[12,], md_bg_color=(0.1, 0.05, 0.15, 1), elevation=2,
                on_release=lambda x, n=novel["name"], c=novel["last_chapter"]: self.open_novel(n, c)
            )
            novel_card.add_widget(AsyncImage(source=novel["cover"], allow_stretch=True, keep_ratio=False))
            shelf.add_widget(novel_card)

        shelf_scroll.add_widget(shelf)
        self.content_layout.add_widget(shelf_scroll)

    def import_new_books(self):
        self.view.engine.check_new_imports(on_complete=self.finish_import)

    @mainthread
    def finish_import(self, has_new):
        if has_new: self.load_sections()

    def open_novel(self, novel_name, last_chapter_idx):
        reader = self.view.get_screen("reader")
        reader.init_novel(novel_name, last_chapter_idx)
        self.view.current = "reader"

class ReaderScreen(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.current_novel = None
        self.current_idx = 0
        self.chapter_list = []
        self.font_size_sp = 18 
        self.ui_visible = True
        self.settings_dialog = None
        
        # Cores padrão
        self.bg_deep = (0.05, 0.02, 0.08, 1) 
        self.purple_ui = (0.1, 0.05, 0.15, 1)
        self.build_ui()

    def build_ui(self):
        # Usamos MDBoxLayout para poder trocar a cor do fundo dinamicamente
        self.main_layout = MDBoxLayout(orientation='vertical', md_bg_color=self.bg_deep)
        
        self.toolbar = MDTopAppBar(
            title="Leitor", md_bg_color=self.purple_ui, elevation=0,
            left_action_items=[["menu", lambda x: self.nav_drawer.set_state("open")]],
            right_action_items=[
                ["cog", lambda x: self.open_settings()],
                ["home", lambda x: self.go_home()]
            ]
        )
        self.main_layout.add_widget(self.toolbar)

        self.progress_bar = MDProgressBar(value=0, color=(0.6, 0.4, 1, 1), size_hint_y=None, height="4dp")
        self.main_layout.add_widget(self.progress_bar)

        reader_container = AnchorLayout()
        
        # Ativando suporte a scroll por mouse/barra
        self.scroll = MDScrollView(scroll_type=['bars', 'content'], smooth_scroll_end=10)
        self.text_label = MDLabel(
            text="", padding=(40, 60), size_hint_y=None, 
            theme_text_color="Custom", text_color=(0.9, 0.9, 0.9, 1), 
            font_style="Body1", font_size=f"{self.font_size_sp}sp", line_height=1.7
        )
        self.text_label.bind(texture_size=self._update_text_height)
        
        self.scroll.add_widget(self.text_label)
        
        self.touch_layer = MDFlatButton(size_hint=(1, 1), on_release=lambda x: self.toggle_ui())
        
        reader_container.add_widget(self.scroll)
        reader_container.add_widget(self.touch_layer)
        
        # Botões laterais
        nav_overlay = MDBoxLayout(orientation='horizontal', padding="10dp", size_hint=(1, None), height="80dp")
        self.prev_btn = MDIconButton(icon="chevron-left", icon_size="40sp", theme_icon_color="Custom", 
                                     icon_color=(1, 1, 1, 0.2), on_release=lambda x: self.change_chapter(-1))
        self.next_btn = MDIconButton(icon="chevron-right", icon_size="40sp", theme_icon_color="Custom", 
                                     icon_color=(1, 1, 1, 0.2), on_release=lambda x: self.change_chapter(1))
        
        nav_overlay.add_widget(self.prev_btn)
        nav_overlay.add_widget(MDBoxLayout()) 
        nav_overlay.add_widget(self.next_btn)
        
        reader_container.add_widget(nav_overlay)
        self.main_layout.add_widget(reader_container)
        self.add_widget(self.main_layout)

        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0), md_bg_color=self.purple_ui)
        drawer_box = MDBoxLayout(orientation='vertical', padding="10dp", spacing="10dp")
        self.search_bar = MDTextField(hint_text="Buscar...", mode="round", fill_color_normal=(1,1,1,0.05))
        self.search_bar.bind(text=self.filter_list)
        drawer_box.add_widget(self.search_bar)
        self.drawer_list = MDList()
        ds = MDScrollView()
        ds.add_widget(self.drawer_list)
        drawer_box.add_widget(ds)
        self.nav_drawer.add_widget(drawer_box)
        self.add_widget(self.nav_drawer)

    def _update_text_height(self, instance, size):
        self.text_label.height = size[1]

    def toggle_ui(self):
        alpha = 0 if self.ui_visible else 1
        Animation(opacity=alpha, d=0.2).start(self.toolbar)
        Animation(opacity=alpha, d=0.2).start(self.progress_bar)
        self.ui_visible = not self.ui_visible

    def init_novel(self, novel_name, start_idx):
        self.current_novel = novel_name
        self.chapter_list = self.view.engine.get_chapters_list(novel_name)
        self.populate_drawer()
        self.load_chapter(start_idx)

    def populate_drawer(self, query=""):
        self.drawer_list.clear_widgets()
        query = query.lower().strip()
        count = 0
        for cap in self.chapter_list:
            if not query or query in cap["title"].lower():
                self.drawer_list.add_widget(OneLineListItem(
                    text=cap["title"], theme_text_color="Custom", text_color=(1, 1, 1, 0.7),
                    on_release=lambda x, i=cap["idx"]: self.load_chapter(i)
                ))
                count += 1
                if count >= 30: break

    def filter_list(self, instance, value):
        Clock.unschedule(self._perform_search)
        Clock.schedule_once(lambda dt: self._perform_search(value), 0.4)

    def _perform_search(self, query):
        self.populate_drawer(query)

    def load_chapter(self, idx):
        self.current_idx = idx
        data = self.view.engine.get_chapter(self.current_novel, idx)
        self.text_label.text = data["content"]
        self.toolbar.title = data["title"]
        self.view.engine.update_reading_progress(self.current_novel, idx)
        self.progress_bar.value = ((idx + 1) / len(self.chapter_list)) * 100
        self.scroll.scroll_y = 1
        self.nav_drawer.set_state("close")

    def change_chapter(self, direction):
        new_index = self.current_idx + direction
        if 0 <= new_index < len(self.chapter_list):
            self.load_chapter(new_index)

    def go_home(self):
        self.view.get_screen("home").load_sections()
        self.view.current = "home"

    # --- SISTEMA DE CONFIGURAÇÕES REINTEGRADO ---
    def open_settings(self):
        if not self.settings_dialog:
            content = MDBoxLayout(orientation="vertical", spacing="15dp", size_hint_y=None, height="160dp")
            
            # Ajuste de Fonte
            font_box = MDBoxLayout(orientation="horizontal", spacing="10dp")
            font_box.add_widget(MDLabel(text="Fonte:", halign="left", theme_text_color="Hint"))
            font_box.add_widget(MDIconButton(icon="minus-circle-outline", on_release=lambda x: self.adjust_font(-2)))
            font_box.add_widget(MDIconButton(icon="plus-circle-outline", on_release=lambda x: self.adjust_font(2)))
            content.add_widget(font_box)

            # Temas
            theme_box = MDBoxLayout(orientation="horizontal", spacing="10dp")
            theme_box.add_widget(MDRectangleFlatButton(text="DARK PURPLE", 
                                                       text_color=(0.6, 0.4, 1, 1),
                                                       on_release=lambda x: self.set_theme("dark")))
            theme_box.add_widget(MDRectangleFlatButton(text="SÉPIA", 
                                                       text_color=(0.4, 0.3, 0.1, 1),
                                                       on_release=lambda x: self.set_theme("sepia")))
            content.add_widget(theme_box)

            self.settings_dialog = MDDialog(title="Personalizar Leitura", type="custom", content_cls=content)
        
        self.settings_dialog.open()

    def adjust_font(self, amount):
        self.font_size_sp = max(12, min(40, self.font_size_sp + amount))
        self.text_label.font_size = f"{self.font_size_sp}sp"

    def set_theme(self, mode):
        if mode == "dark":
            self.main_layout.md_bg_color = self.bg_deep
            self.text_label.text_color = (0.9, 0.9, 0.9, 1)
            self.toolbar.md_bg_color = self.purple_ui
        elif mode == "sepia":
            self.main_layout.md_bg_color = (0.96, 0.89, 0.76, 1)
            self.text_label.text_color = (0.2, 0.1, 0, 1)
            self.toolbar.md_bg_color = (0.8, 0.7, 0.55, 1)
        
        if self.settings_dialog:
            self.settings_dialog.dismiss()