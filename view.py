from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFillRoundFlatIconButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock

class SapienView(MDScreenManager):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.dark_purple = (0.19, 0.1, 0.57, 1)
        self.add_widget(HomeScreen(name="home", view=self))
        self.add_widget(LibraryScreen(name="library", view=self))
        self.add_widget(ReaderScreen(name="reader", view=self))

class HomeScreen(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.build_ui()

    def build_ui(self):
        self.layout = BoxLayout(orientation='vertical', padding="20dp", spacing="15dp")
        self.refresh_ui()
        self.add_widget(self.layout)

    def refresh_ui(self):
        self.layout.clear_widgets()
        config = self.view.engine.load_full_config()
        self.layout.add_widget(MDLabel(text="SAPIEN", font_style="H4", halign="center", theme_text_color="Custom", text_color=self.view.dark_purple))
        
        card = MDCard(orientation='vertical', size_hint=(1, None), height="350dp", padding="10dp", radius=[15,], md_bg_color=(0.15, 0.15, 0.15, 1))
        card.add_widget(AsyncImage(source=self.view.engine.library_data["Lord of the Mysteries"]["cover"], size_hint=(1, 0.7)))
        card.add_widget(MDLabel(text="Lord of the Mysteries", halign="center", bold=True))
        card.add_widget(MDLabel(text=f"Capítulo: {config.get('last_chapter_title', 'Início')}", halign="center", theme_text_color="Hint"))
        
        btn_cont = MDFillRoundFlatIconButton(
            icon="play", text="CONTINUAR", md_bg_color=self.view.dark_purple,
            pos_hint={"center_x": .5}, on_release=lambda x: self.view.get_screen("reader").load_chapter(config["last_chapter"])
        )
        card.add_widget(btn_cont)
        self.layout.add_widget(card)
        self.layout.add_widget(MDRaisedButton(text="BIBLIOTECA", pos_hint={"center_x": .5}, on_release=lambda x: setattr(self.view, 'current', 'library')))

class LibraryScreen(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(MDTopAppBar(title="Minha Biblioteca", md_bg_color=self.view.dark_purple, left_action_items=[["arrow-left", lambda x: setattr(self.view, 'current', 'home')]]))
        scroll = MDScrollView()
        list_view = MDList()
        for name, data in self.view.engine.library_data.items():
            item = MDCard(orientation='horizontal', size_hint=(1, None), height="120dp", padding="10dp", on_release=lambda x: self.view.get_screen("reader").load_chapter(self.view.engine.load_full_config()["last_chapter"]))
            item.add_widget(AsyncImage(source=data["cover"], size_hint=(0.3, 1)))
            list_view.add_widget(item)
        scroll.add_widget(list_view)
        layout.add_widget(scroll)
        self.add_widget(layout)

class ReaderScreen(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.fullscreen = False
        self.current_index = 0
        self.build_ui()

    def build_ui(self):
        self.main_layout = BoxLayout(orientation='vertical')
        
        # Barra Superior
        self.toolbar = MDTopAppBar(
            title="Leitor", md_bg_color=self.view.dark_purple,
            left_action_items=[["menu", lambda x: self.nav_drawer.set_state("open")]],
            right_action_items=[["fullscreen", lambda x: self.toggle_fullscreen()], ["home", lambda x: self.go_home()]]
        )
        self.main_layout.add_widget(self.toolbar)

        # Área de Texto e Botões de Navegação
        reader_area = AnchorLayout()
        
        # Scroll do Texto
        self.scroll = MDScrollView()
        self.text_label = MDLabel(text="", padding=(30, 80), size_hint_y=None, theme_text_color="Custom", text_color=(1, 1, 1, 1), font_style="Body1", line_height=1.5)
        self.text_label.bind(texture_size=self.text_label.setter('size'))
        self.scroll.add_widget(self.text_label)
        reader_area.add_widget(self.scroll)

        # Botões Flutuantes Laterais (Avançar/Voltar)
        nav_buttons = BoxLayout(orientation='horizontal', padding="10dp", size_hint=(1, None), height="80dp", pos_hint={'center_y': .5})
        nav_buttons.add_widget(MDIconButton(icon="chevron-left", theme_text_color="Custom", text_color=(1,1,1,0.3), on_release=lambda x: self.change_chapter(-1)))
        nav_buttons.add_widget(BoxLayout()) # Espaçador
        nav_buttons.add_widget(MDIconButton(icon="chevron-right", theme_text_color="Custom", text_color=(1,1,1,0.3), on_release=lambda x: self.change_chapter(1)))
        reader_area.add_widget(nav_buttons)

        # Botão de Sair do Fullscreen
        self.exit_fs_btn = MDIconButton(icon="fullscreen-exit", pos_hint={'right': 1, 'top': 1}, theme_text_color="Custom", text_color=(1,1,1,0.5), on_release=lambda x: self.toggle_fullscreen())

        self.main_layout.add_widget(reader_area)
        self.add_widget(self.main_layout)

        # Menu Lateral (Drawer) com Busca
        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0))
        drawer_content = BoxLayout(orientation='vertical', padding="12dp", spacing="10dp")
        
        self.search_bar = MDTextField(hint_text="Buscar capítulo...", mode="round", line_color_focus=self.view.dark_purple)
        self.search_bar.bind(text=self.schedule_search)
        drawer_content.add_widget(self.search_bar)

        self.chapter_list_widget = MDList()
        drawer_scroll = MDScrollView()
        drawer_scroll.add_widget(self.chapter_list_widget)
        drawer_content.add_widget(drawer_scroll)
        
        self.nav_drawer.add_widget(drawer_content)
        self.add_widget(self.nav_drawer)
        self.update_list()

    def schedule_search(self, instance, value):
        Clock.unschedule(self.update_list)
        Clock.schedule_once(lambda dt: self.update_list(value), 0.5)

    def update_list(self, query=""):
        self.chapter_list_widget.clear_widgets()
        filtered = self.view.engine.get_filtered_chapters(query)
        for idx, title in filtered[:50]:
            self.chapter_list_widget.add_widget(OneLineListItem(text=title, on_release=lambda x, i=idx: self.load_chapter(i)))

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
        self.current_index = index
        self.text_label.text = self.view.engine.get_content(index)
        self.toolbar.title = self.view.engine.chapters[index]["title"]
        self.view.engine.save_progress(index)
        self.view.current = "reader"
        self.nav_drawer.set_state("close")
        self.scroll.scroll_y = 1

    def go_home(self):
        self.view.get_screen("home").refresh_ui()
        self.view.current = "home"