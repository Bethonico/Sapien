import os
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
from kivy.metrics import dp


# =============================================================================
# COMPONENTE: BARRA DE PLAYER DE ÁUDIO (Bottom Sheet)
# =============================================================================
class AudioPlayerBar(MDBoxLayout):
    """
    Barra de player persistente que aparece na parte inferior da tela
    quando o modo audiobook é ativado. Similar ao player de apps de bíblia/podcasts.
    """
    def __init__(self, reader_screen, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader_screen
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 0          # começa escondido
        self.opacity = 0
        self.md_bg_color = (0.08, 0.04, 0.14, 1)

        # Estado interno
        self.is_playing = False
        self.current_chunk = 0
        self.total_chunks = 0
        self._tick_event = None

        self._build()

    def _build(self):
        # ── Linha de arraste (decoração) ──────────────────────────
        handle_box = MDBoxLayout(size_hint_y=None, height="18dp",
                                 padding=("0dp", "6dp"))
        handle = MDCard(
            size_hint=(None, None), size=("40dp", "4dp"),
            radius=[4], md_bg_color=(1, 1, 1, 0.2),
        )
        handle_anchor = AnchorLayout(anchor_x='center')
        handle_anchor.add_widget(handle)
        handle_box.add_widget(handle_anchor)
        self.add_widget(handle_box)

        # ── Título do capítulo ────────────────────────────────────
        self.title_label = MDLabel(
            text="",
            font_style="Subtitle1",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 0.9),
            size_hint_y=None,
            height="30dp",
        )
        self.add_widget(self.title_label)

        # ── Sub-label: "Trecho X de Y" ────────────────────────────
        self.chunk_label = MDLabel(
            text="",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=(0.7, 0.5, 1, 0.8),
            size_hint_y=None,
            height="22dp",
        )
        self.add_widget(self.chunk_label)

        # ── Barra de progresso dos chunks ─────────────────────────
        self.progress_bar = MDProgressBar(
            value=0,
            color=(0.6, 0.4, 1, 1),
            size_hint_y=None,
            height="3dp",
        )
        self.add_widget(self.progress_bar)

        # ── Controles: rew | play/pause | fwd ─────────────────────
        controls = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="72dp",
            padding=("30dp", "4dp"),
            spacing="10dp",
        )

        # Voltar chunk
        self.btn_prev = MDIconButton(
            icon="skip-previous",
            icon_size="32sp",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 0.6),
            on_release=lambda x: self.skip(-1),
        )

        # Play / Pause — botão central maior
        self.btn_play = MDIconButton(
            icon="play-circle",
            icon_size="52sp",
            theme_icon_color="Custom",
            icon_color=(0.7, 0.5, 1, 1),
            on_release=lambda x: self.toggle_play(),
        )

        # Avançar chunk
        self.btn_next = MDIconButton(
            icon="skip-next",
            icon_size="32sp",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 0.6),
            on_release=lambda x: self.skip(1),
        )

        # Fechar player
        self.btn_close = MDIconButton(
            icon="close",
            icon_size="24sp",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 0.3),
            on_release=lambda x: self.reader.parar_audio(),
        )

        # Espaçadores para centralizar
        controls.add_widget(MDBoxLayout())   # flex esquerdo
        controls.add_widget(self.btn_prev)
        controls.add_widget(self.btn_play)
        controls.add_widget(self.btn_next)
        controls.add_widget(MDBoxLayout())   # flex direito
        controls.add_widget(self.btn_close)
        self.add_widget(controls)

        # Padding inferior (respeita barra de navegação do Android)
        self.add_widget(MDBoxLayout(size_hint_y=None, height="8dp"))

    # ── API pública ───────────────────────────────────────────────

    def show(self, chapter_title="", total_chunks=0):
        """Força exibição e anima só o opacity."""
        self.title_label.text = chapter_title
        self.total_chunks = total_chunks
        self.current_chunk = 0
        self._update_labels()
        self.set_playing(True)

        self.height = dp(165)
        self.opacity = 0
        Animation(opacity=1, d=0.3).start(self)

        # Força o layout pai a recalcular após mudar a altura
        if self.parent:
            self.parent.do_layout()

    def hide(self):
        """Anima saída e zera altura no callback para garantir sequência."""
        self.set_playing(False)

        def _after_hide(*args):
            self.height = 0
            if self.parent:
                self.parent.do_layout()

        anim = Animation(opacity=0, d=0.25, t='in_cubic')
        anim.bind(on_complete=_after_hide)
        anim.start(self)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        self.btn_play.icon = "pause-circle" if playing else "play-circle"
        self.btn_play.icon_color = (0.7, 0.5, 1, 1) if playing else (1, 1, 1, 0.6)

    def advance_chunk(self):
        """Chamado pelo ReaderScreen quando um novo chunk começa."""
        self.current_chunk += 1
        self._update_labels()

    def _update_labels(self):
        if self.total_chunks > 0:
            self.chunk_label.text = f"Trecho {self.current_chunk + 1} de {self.total_chunks}"
            self.progress_bar.value = ((self.current_chunk) / self.total_chunks) * 100
        else:
            self.chunk_label.text = f"Trecho {self.current_chunk + 1}"

    def toggle_play(self):
        audio = self.reader.view.engine.audio
        if self.is_playing:
            # Pausa: para o clock interno do audio_manager
            audio._stop_clock()
            if audio.current_sound:
                audio.current_sound.stop()
            self.set_playing(False)
        else:
            # Retoma: relança o loop de playback
            audio._start_playback_loop()
            if audio.current_sound:
                audio.current_sound.play()
            self.set_playing(True)

    def skip(self, direction):
        """Pula para o chunk anterior ou próximo."""
        audio = self.reader.view.engine.audio
        audio._stop_clock()
        audio._cancel_pause()
        
        if audio.current_sound:
            audio.current_sound.stop()
            audio.current_sound.unload()
            audio.current_sound = None

        target = self.current_chunk + direction
        target = max(0, min(target, self.total_chunks - 1))

        novel_folder = self.reader.current_novel.replace(" ", "_").lower()
        cap_idx = self.reader.current_idx
        file_path = os.path.join(
            "assets", "audios", novel_folder,
            f"cache_{novel_folder}_{cap_idx}_{target}.mp3"
        )

        if os.path.exists(file_path):
            # Limpa o prefetch antigo para não dar conflito
            if audio.next_sound:
                audio.next_sound.unload()
                audio.next_sound = None
                
            self.current_chunk = target
            self._update_labels()
            
            # Limpa a fila existente e toca o alvo diretamente
            audio._play_queue.clear()
            audio._play_file(target, file_path)
            audio._start_playback_loop()
            self.set_playing(True)


# =============================================================================
# VIEW PRINCIPAL
# =============================================================================
class SapienView(MDScreenManager):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.transition = FadeTransition(duration=0.2)
        self.engine = engine
        self.add_widget(NetflixHome(name="home", view=self))
        self.add_widget(ReaderScreen(name="reader", view=self))


# =============================================================================
# TELA HOME
# =============================================================================
class NetflixHome(MDScreen):
    def __init__(self, view, **kwargs):
        super().__init__(**kwargs)
        self.view = view
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        self.bg_container = MDBoxLayout(orientation='vertical',
                                        md_bg_color=(0.02, 0.01, 0.04, 1))

        header = MDBoxLayout(orientation='horizontal', size_hint_y=None,
                             height="80dp", padding=("20dp", "10dp"))
        header.add_widget(MDLabel(
            text="SAPIEN", font_style="H4", bold=True,
            theme_text_color="Custom", text_color=(0.6, 0.4, 1, 1)
        ))
        sync_btn = MDIconButton(
            icon="sync", theme_icon_color="Custom",
            icon_color=(0.6, 0.4, 1, 1),
            on_release=lambda x: self.import_new_books()
        )
        header.add_widget(sync_btn)
        self.bg_container.add_widget(header)

        self.main_scroll = MDScrollView(scroll_type=['bars', 'content'],
                                        smooth_scroll_end=10)
        self.content_layout = MDBoxLayout(
            orientation='vertical', padding="20dp", spacing="30dp",
            size_hint_y=None
        )
        self.content_layout.bind(
            minimum_height=self.content_layout.setter('height')
        )

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
                halign="center", theme_text_color="Hint",
                size_hint_y=None, height="200dp"
            ))
            return

        last = novels[0]
        hero_card = MDCard(
            orientation='horizontal', size_hint=(1, None), height="180dp",
            radius=[20], md_bg_color=(0.1, 0.05, 0.2, 1),
            padding="15dp", elevation=4
        )
        hero_cover = MDCard(size_hint=(None, 1), width="110dp",
                            radius=[10], elevation=0)
        hero_cover.add_widget(AsyncImage(
            source=last["cover"], allow_stretch=True, keep_ratio=False
        ))
        hero_card.add_widget(hero_cover)

        hero_info = MDBoxLayout(orientation='vertical', padding=("20dp", 0))
        hero_info.add_widget(MDLabel(
            text="CONTINUAR LENDO", font_style="Overline",
            theme_text_color="Hint"
        ))
        hero_info.add_widget(MDLabel(
            text=last["name"], font_style="H5", bold=True
        ))
        hero_info.add_widget(MDLabel(
            text=f"Capítulo {last['last_chapter'] + 1}",
            theme_text_color="Secondary"
        ))
        hero_info.add_widget(MDFillRoundFlatButton(
            text="RETOMAR AGORA", md_bg_color=(0.6, 0.4, 1, 1),
            on_release=lambda x, n=last["name"],
            c=last["last_chapter"]: self.open_novel(n, c)
        ))
        hero_card.add_widget(hero_info)
        self.content_layout.add_widget(hero_card)

        self.content_layout.add_widget(MDLabel(
            text="Minha Biblioteca", font_style="H6", bold=True
        ))

        shelf_scroll = MDScrollView(
            do_scroll_x=True, do_scroll_y=False,
            size_hint=(1, None), height="220dp"
        )
        shelf = MDBoxLayout(
            orientation='horizontal', spacing="15dp",
            size_hint_x=None, padding="5dp"
        )
        shelf.bind(minimum_width=shelf.setter('width'))

        for novel in novels:
            novel_card = MDCard(
                orientation='vertical', size_hint=(None, None),
                size=("130dp", "190dp"), radius=[12],
                md_bg_color=(0.1, 0.05, 0.15, 1), elevation=2,
                on_release=lambda x, n=novel["name"],
                c=novel["last_chapter"]: self.open_novel(n, c)
            )
            novel_card.add_widget(AsyncImage(
                source=novel["cover"], allow_stretch=True, keep_ratio=False
            ))
            shelf.add_widget(novel_card)

        shelf_scroll.add_widget(shelf)
        self.content_layout.add_widget(shelf_scroll)

    def import_new_books(self):
        self.view.engine.check_new_imports(on_complete=self.finish_import)

    @mainthread
    def finish_import(self, has_new):
        if has_new:
            self.load_sections()

    def open_novel(self, novel_name, last_chapter_idx):
        reader = self.view.get_screen("reader")
        reader.init_novel(novel_name, last_chapter_idx)
        self.view.current = "reader"


# =============================================================================
# TELA DO LEITOR
# =============================================================================
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

        # Estado de áudio
        self.audio_active = False

        # Paleta
        self.bg_deep = (0.05, 0.02, 0.08, 1)
        self.purple_ui = (0.1, 0.05, 0.15, 1)

        self.build_ui()

    def build_ui(self):
        # ── Layout raiz ───────────────────────────────────────────
        self.root_layout = MDBoxLayout(
            orientation='vertical', md_bg_color=self.bg_deep
        )

        # ── Toolbar ───────────────────────────────────────────────
        self.toolbar = MDTopAppBar(
            title="Leitor",
            md_bg_color=self.purple_ui,
            elevation=0,
            left_action_items=[
                ["menu", lambda x: self.nav_drawer.set_state("open")]
            ],
            right_action_items=[
                ["headphones", lambda x: self.toggle_audio()],
                ["cog",        lambda x: self.open_settings()],
                ["home",       lambda x: self.go_home()],
            ],
        )
        self.root_layout.add_widget(self.toolbar)

        # ── Barra de progresso do capítulo ────────────────────────
        self.chapter_progress = MDProgressBar(
            value=0, color=(0.6, 0.4, 1, 1),
            size_hint_y=None, height="4dp"
        )
        self.root_layout.add_widget(self.chapter_progress)

        # ── Área de leitura (scroll + texto) ─────────────────────
        reader_anchor = AnchorLayout(anchor_x='center', size_hint=(1, 1))

        self.reading_column = MDBoxLayout(
            orientation='vertical', size_hint_x=None, width="800dp"
        )
        self.bind(width=lambda inst, val: setattr(
            self.reading_column, 'width', min(val, dp(850))
        ))

        self.scroll = MDScrollView(
            scroll_type=['bars', 'content'], smooth_scroll_end=10
        )
        self.scroll.bind(scroll_y=self._on_scroll_change)

        self.text_label = MDLabel(
            text="",
            padding=(40, 60),
            size_hint_y=None,
            theme_text_color="Custom",
            text_color=(0.9, 0.9, 0.9, 1),
            font_style="Body1",
            font_size=f"{self.font_size_sp}sp",
            line_height=1.7,
        )
        self.text_label.bind(texture_size=self._update_text_height)

        self.scroll.add_widget(self.text_label)
        self.reading_column.add_widget(self.scroll)
        reader_anchor.add_widget(self.reading_column)

        # Camada de toque para esconder/mostrar UI
        self.touch_layer = MDFlatButton(
            size_hint=(1, 1),
            on_release=lambda x: self.toggle_ui()
        )

        container = AnchorLayout()
        container.add_widget(reader_anchor)
        container.add_widget(self.touch_layer)

        # Botões prev/next sobrepostos
        nav_overlay = MDBoxLayout(
            orientation='horizontal', padding="10dp",
            size_hint=(1, None), height="80dp"
        )
        self.prev_btn = MDIconButton(
            icon="chevron-left", icon_size="40sp",
            theme_icon_color="Custom", icon_color=(1, 1, 1, 0.2),
            on_release=lambda x: self.change_chapter(-1)
        )
        self.next_btn = MDIconButton(
            icon="chevron-right", icon_size="40sp",
            theme_icon_color="Custom", icon_color=(1, 1, 1, 0.2),
            on_release=lambda x: self.change_chapter(1)
        )
        nav_overlay.add_widget(self.prev_btn)
        nav_overlay.add_widget(MDBoxLayout())
        nav_overlay.add_widget(self.next_btn)
        container.add_widget(nav_overlay)

        self.root_layout.add_widget(container)

        # ── Player de áudio (bottom sheet) ───────────────────────
        self.audio_player = AudioPlayerBar(reader_screen=self)
        self.root_layout.add_widget(self.audio_player)

        self.add_widget(self.root_layout)

        # ── Navigation Drawer ─────────────────────────────────────
        self.nav_drawer = MDNavigationDrawer(
            radius=(0, 16, 16, 0), md_bg_color=self.purple_ui
        )
        drawer_box = MDBoxLayout(
            orientation='vertical', padding="10dp", spacing="10dp"
        )
        self.search_bar = MDTextField(
            hint_text="Buscar...", mode="round",
            fill_color_normal=(1, 1, 1, 0.05)
        )
        self.search_bar.bind(text=self.filter_list)
        drawer_box.add_widget(self.search_bar)
        self.drawer_list = MDList()
        ds = MDScrollView()
        ds.add_widget(self.drawer_list)
        drawer_box.add_widget(ds)
        self.nav_drawer.add_widget(drawer_box)
        self.add_widget(self.nav_drawer)

    # ── Helpers de layout ─────────────────────────────────────────
    def _update_text_height(self, instance, size):
        self.text_label.height = size[1]

    def toggle_ui(self):
        alpha = 0 if self.ui_visible else 1
        Animation(opacity=alpha, d=0.2).start(self.toolbar)
        Animation(opacity=alpha, d=0.2).start(self.chapter_progress)
        self.ui_visible = not self.ui_visible

    def _on_scroll_change(self, instance, value):
        Clock.unschedule(self._save_scroll_to_db)
        Clock.schedule_once(lambda dt: self._save_scroll_to_db(value), 1.0)

    def _save_scroll_to_db(self, value):
        if self.current_novel:
            self.view.engine.db.update_scroll_pos(self.current_novel, value)

    # ── Navegação ─────────────────────────────────────────────────
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
                    text=cap["title"],
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 0.7),
                    on_release=lambda x, i=cap["idx"]: self.load_chapter(i)
                ))
                count += 1
                if count >= 30:
                    break

    def filter_list(self, instance, value):
        Clock.unschedule(self._perform_search)
        Clock.schedule_once(lambda dt: self._perform_search(value), 0.4)

    def _perform_search(self, query):
        self.populate_drawer(query)

    def load_chapter(self, idx):
        if self.audio_active:
            self.parar_audio()

        self.current_idx = idx
        data = self.view.engine.get_chapter(self.current_novel, idx)
        self.text_label.text = data["content"]
        self.toolbar.title = data["title"]
        self.view.engine.update_reading_progress(self.current_novel, idx)
        self.chapter_progress.value = (
            (idx + 1) / len(self.chapter_list)
        ) * 100
        self.scroll.scroll_y = 1
        self.nav_drawer.set_state("close")

    def change_chapter(self, direction):
        new_index = self.current_idx + direction
        if 0 <= new_index < len(self.chapter_list):
            self.load_chapter(new_index)

    def go_home(self):
        if self.audio_active:
            self.parar_audio()
        self.view.get_screen("home").load_sections()
        self.view.current = "home"

    # =================================================================
    # SISTEMA DE ÁUDIO — integração com novo AudioManager
    # =================================================================

    def toggle_audio(self):
        """Botão de fones na toolbar: liga/desliga o audiobook."""
        if self.audio_active:
            self.parar_audio()
            return

        self.audio_active = True

        # Ícone de carregando enquanto gera o primeiro chunk
        self.toolbar.right_action_items = [
            ["clock-outline", lambda x: self.parar_audio()],
            ["cog",  lambda x: self.open_settings()],
            ["home", lambda x: self.go_home()],
        ]

        text = self.text_label.text

        # Total de blocos igual ao audio_manager (grupos de 180+ chars)
        raw = [p.strip() for p in text.split('\n') if len(p.strip()) > 10]
        buffer = ""
        total = 0
        for para in raw:
            buffer = (buffer + " " + para).strip() if buffer else para
            if len(buffer) >= 180:
                total += 1
                buffer = ""
        if buffer:
            total += 1

        # Dispara o processamento; o audio_manager gerencia a fila internamente
        self.view.engine.audio.process_chapter(
            text=text,
            novel_name=self.current_novel,
            cap_idx=self.current_idx,
            on_playback_start=lambda: Clock.schedule_once(
                lambda dt: self._on_audio_started(total), 0
            ),
        )

    def _on_audio_started(self, total_chunks: int):
        """Chamado pelo audio_manager quando o 1º chunk começa a tocar."""
        if not self.audio_active:
            return

        # Restaura toolbar com botão de stop
        self.toolbar.right_action_items = [
            ["stop-circle", lambda x: self.parar_audio()],
            ["cog",  lambda x: self.open_settings()],
            ["home", lambda x: self.go_home()],
        ]

        # Exibe o player bar com animação
        self.audio_player.show(
            chapter_title=self.toolbar.title,
            total_chunks=total_chunks,
        )

        # Liga o ticker que avança o contador de chunks na UI
        self._chunk_tick = Clock.schedule_interval(
            self._update_chunk_display, 0.5
        )

    def _update_chunk_display(self, dt):
        if not self.audio_active:
            Clock.unschedule(self._update_chunk_display)
            return

        audio = self.view.engine.audio

        # Se estiver tocando ou em pausa natural, o botão deve mostrar Pause (tocar)
        if audio.is_playing() or audio._in_pause:
            self.audio_player.set_playing(True)

        # Sincroniza a label de "Trecho X" com o motor real de áudio
        if self.audio_player.current_chunk != audio.current_chunk_idx:
            self.audio_player.current_chunk = audio.current_chunk_idx
            self.audio_player._update_labels()

        # Só para tudo quando realmente não houver mais nada
        if (not audio.is_playing()
                and not audio._in_pause
                and not audio._play_queue
                and not audio._download_active):
            self.parar_audio()

    def parar_audio(self):
        """Para tudo e esconde o player."""
        self.audio_active = False
        Clock.unschedule(self._update_chunk_display)
        self.view.engine.audio.stop_audio()

        self.audio_player.hide()

        # Restaura toolbar original
        self.toolbar.right_action_items = [
            ["headphones", lambda x: self.toggle_audio()],
            ["cog",        lambda x: self.open_settings()],
            ["home",       lambda x: self.go_home()],
        ]

    # =================================================================
    # CONFIGURAÇÕES
    # =================================================================
    def open_settings(self):
        if not self.settings_dialog:
            content = MDBoxLayout(
                orientation="vertical", spacing="15dp",
                size_hint_y=None, height="160dp"
            )

            font_box = MDBoxLayout(orientation="horizontal", spacing="10dp")
            font_box.add_widget(MDLabel(
                text="Fonte:", halign="left", theme_text_color="Hint"
            ))
            font_box.add_widget(MDIconButton(
                icon="minus-circle-outline",
                on_release=lambda x: self.adjust_font(-2)
            ))
            font_box.add_widget(MDIconButton(
                icon="plus-circle-outline",
                on_release=lambda x: self.adjust_font(2)
            ))
            content.add_widget(font_box)

            theme_box = MDBoxLayout(orientation="horizontal", spacing="10dp")
            theme_box.add_widget(MDRectangleFlatButton(
                text="DARK PURPLE", text_color=(0.6, 0.4, 1, 1),
                on_release=lambda x: self.set_theme("dark")
            ))
            theme_box.add_widget(MDRectangleFlatButton(
                text="SÉPIA", text_color=(0.4, 0.3, 0.1, 1),
                on_release=lambda x: self.set_theme("sepia")
            ))
            content.add_widget(theme_box)

            self.settings_dialog = MDDialog(
                title="Personalizar Leitura",
                type="custom",
                content_cls=content,
            )

        self.settings_dialog.open()

    def adjust_font(self, amount):
        self.font_size_sp = max(12, min(40, self.font_size_sp + amount))
        self.text_label.font_size = f"{self.font_size_sp}sp"

    def set_theme(self, mode):
        if mode == "dark":
            self.root_layout.md_bg_color = self.bg_deep
            self.text_label.text_color = (0.9, 0.9, 0.9, 1)
            self.toolbar.md_bg_color = self.purple_ui
        elif mode == "sepia":
            self.root_layout.md_bg_color = (0.96, 0.89, 0.76, 1)
            self.text_label.text_color = (0.2, 0.1, 0, 1)
            self.toolbar.md_bg_color = (0.8, 0.7, 0.55, 1)

        if self.settings_dialog:
            self.settings_dialog.dismiss()