import os
import threading
import time
import logging
from collections import deque
from gtts import gTTS
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE LOGGING
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("sapien_audio.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SapienAudio")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE SEGURANÇA E PAUSAS
# ══════════════════════════════════════════════════════════════════════════════
PAUSE_BETWEEN_BLOCKS = 0.8
PAUSE_TICK_INTERVAL = 0.3
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2.0  # segundos entre tentativas
MIN_FILE_SIZE = 100  # bytes mínimos para considerar ficheiro válido


class SapienAudio:
    """
    Gerenciador de áudio para o Sapien com proteções contra colisões de I/O.
    
    Funcionalidades:
    - Escrita atómica com ficheiros temporários
    - Cache inteligente para evitar downloads duplicados
    - Retry automático em caso de falha de rede
    - Limpeza adequada de recursos (memória)
    """
    
    def __init__(self):
        self.base_audio_path = os.path.join("assets", "audios")
        os.makedirs(self.base_audio_path, exist_ok=True)

        # Estado de reprodução
        self.current_sound = None
        self.next_sound = None
        self.stop_requested = False
        self._download_active = False
        self._play_queue = deque()
        self._clock_event = None
        self._pause_event = None
        self._in_pause = False
        self.current_chunk_idx = 0
        self.current_task_id = 0
        
        logger.info("SapienAudio inicializado com sucesso")

    def _group_paragraphs(self, text, min_chars=180):
        """
        Agrupa parágrafos em blocos de texto para conversão TTS.
        
        Args:
            text: Texto completo do capítulo
            min_chars: Tamanho mínimo de cada bloco
            
        Returns:
            Lista de strings (blocos de texto)
        """
        # Limpa caracteres problemáticos
        text = text.replace('\xad', '').replace('\u00ad', '').replace('\r', '')
        
        # Separa em parágrafos válidos
        raw = [p.strip() for p in text.split('\n') if len(p.strip()) > 10]
        
        groups = []
        buffer = ""
        
        for para in raw:
            buffer = (buffer + " " + para).strip() if buffer else para
            if len(buffer) >= min_chars:
                groups.append(buffer)
                buffer = ""
        
        # Processa o buffer restante
        if buffer:
            if groups and len(buffer) < 60:
                groups[-1] += " " + buffer
            else:
                groups.append(buffer)
        
        logger.info(f"Texto dividido em {len(groups)} blocos")
        return groups

    def _download_audio_with_retry(self, block_text, file_path, max_attempts=MAX_RETRY_ATTEMPTS):
        """
        Faz download do áudio com retry automático e escrita atómica.
        
        Args:
            block_text: Texto a converter em áudio
            file_path: Caminho final do ficheiro .mp3
            max_attempts: Número máximo de tentativas
            
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        temp_path = file_path + ".tmp"
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Tentativa {attempt}/{max_attempts}: {os.path.basename(file_path)}")
                
                # Gera o áudio via gTTS
                tts = gTTS(text=block_text, lang='pt', slow=False)
                
                # FASE 1: Salva no ficheiro temporário
                tts.save(temp_path)
                
                # Aguarda o buffer do sistema operativo estabilizar
                time.sleep(0.1)
                
                # Verifica se o ficheiro temporário é válido
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) < MIN_FILE_SIZE:
                    logger.warning(f"Ficheiro temporário inválido: {temp_path}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise ValueError("Ficheiro temporário corrompido")
                
                # FASE 2: Renomeia para o nome final (operação atómica)
                os.replace(temp_path, file_path)
                
                # Verifica integridade do ficheiro final
                if os.path.exists(file_path) and os.path.getsize(file_path) > MIN_FILE_SIZE:
                    logger.info(f"✅ Download bem-sucedido: {os.path.basename(file_path)}")
                    return True
                else:
                    logger.error(f"Ficheiro final inválido após renomear: {file_path}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Erro na tentativa {attempt}/{max_attempts}: {e}")
                
                # Limpa ficheiro temporário em caso de erro
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                
                # Se não foi a última tentativa, aguarda antes de tentar novamente
                if attempt < max_attempts:
                    retry_wait = RETRY_DELAY * attempt  # Backoff exponencial
                    logger.info(f"Aguardando {retry_wait}s antes de tentar novamente...")
                    time.sleep(retry_wait)
                else:
                    logger.error(f"Todas as tentativas falharam para: {os.path.basename(file_path)}")
                    return False
        
        return False

    def process_chapter(self, text, novel_name, cap_idx, on_playback_start=None):
        """
        Processa um capítulo completo: divide em blocos, faz cache/download e inicia reprodução.
        
        Args:
            text: Texto completo do capítulo
            novel_name: Nome da novel
            cap_idx: Índice do capítulo
            on_playback_start: Callback para quando o primeiro bloco começar a tocar
        """
        self.current_task_id += 1
        this_task = self.current_task_id
        self.stop_audio()
        
        logger.info(f"Processando capítulo {cap_idx} de '{novel_name}'")
        
        # Divide o texto em blocos
        blocks = self._group_paragraphs(text, min_chars=180)
        novel_folder = novel_name.replace(" ", "_").lower()
        novel_path = os.path.join(self.base_audio_path, novel_folder)
        os.makedirs(novel_path, exist_ok=True)

        def _download_worker(task_id):
            """Thread worker para downloads em background."""
            self._download_active = True
            successful_downloads = 0
            failed_downloads = 0
            
            try:
                for i, block_text in enumerate(blocks):
                    # Verifica se a tarefa foi cancelada
                    if self.stop_requested or task_id != self.current_task_id:
                        logger.info("Download cancelado pelo utilizador")
                        break
                    
                    file_name = f"cache_{novel_folder}_{cap_idx}_part_{i}.mp3"
                    file_path = os.path.join(novel_path, file_name)

                    # ═══════════════════════════════════════════════════════
                    # CACHE INTELIGENTE: Verifica se já existe
                    # ═══════════════════════════════════════════════════════
                    if os.path.exists(file_path) and os.path.getsize(file_path) > MIN_FILE_SIZE:
                        logger.info(f"✓ Cache HIT: {file_name}")
                    else:
                        # ═══════════════════════════════════════════════════
                        # DOWNLOAD COM ESCRITA ATÓMICA E RETRY
                        # ═══════════════════════════════════════════════════
                        logger.info(f"↓ Cache MISS: a fazer download de {file_name}")
                        
                        if self._download_audio_with_retry(block_text, file_path):
                            successful_downloads += 1
                        else:
                            failed_downloads += 1
                            logger.warning(f"Bloco {i} falhou após todas as tentativas - a continuar...")
                            continue  # Continua mesmo se falhar (não bloqueia o resto)
                    
                    # Adiciona à fila de reprodução (apenas se a tarefa ainda estiver ativa)
                    if task_id == self.current_task_id:
                        self._play_queue.append((i, file_path))
                        
                        # Inicia o motor de reprodução quando o primeiro bloco estiver pronto
                        if i == 0:
                            Clock.schedule_once(
                                lambda dt: self._start_engine(on_playback_start), 
                                0.2
                            )
                
                logger.info(f"Download concluído: {successful_downloads} OK, {failed_downloads} falhas")
                
            except Exception as e:
                logger.error(f"Erro crítico no download worker: {e}")
            finally:
                if task_id == self.current_task_id:
                    self._download_active = False

        # Inicia a thread de download
        threading.Thread(target=_download_worker, args=(this_task,), daemon=True).start()

    @mainthread
    def _start_engine(self, callback):
        """Inicia o motor de reprodução quando o primeiro bloco estiver pronto."""
        if self._play_queue and not self.stop_requested:
            idx, path = self._play_queue.popleft()
            self._play_file(idx, path)
            if callback:
                callback()
            self._start_playback_loop()

    def _play_file(self, index, file_path):
        """
        Reproduz um ficheiro de áudio com limpeza adequada de recursos.
        
        Args:
            index: Índice do bloco
            file_path: Caminho do ficheiro .mp3
        """
        self.current_chunk_idx = index
        
        # ═════════════════════════════════════════════════════════════════
        # LIMPEZA DE BUFFER: Descarrega o som anterior da memória
        # ═════════════════════════════════════════════════════════════════
        if self.current_sound:
            try:
                self.current_sound.stop()
                self.current_sound.unload()
                logger.debug(f"Som anterior descarregado da memória")
            except Exception as e:
                logger.warning(f"Erro ao descarregar som: {e}")
            finally:
                self.current_sound = None

        # Pequena pausa para o Windows libertar o ficheiro
        time.sleep(0.05)

        try:
            # Verifica se o ficheiro existe e é válido
            if os.path.exists(file_path) and os.path.getsize(file_path) > MIN_FILE_SIZE:
                
                # Reutiliza o som pré-carregado se disponível
                if self.next_sound and getattr(self.next_sound, 'source', '') == file_path:
                    logger.debug(f"Reutilizando som pré-carregado: bloco {index}")
                    self.current_sound = self.next_sound
                    self.next_sound = None
                else:
                    # Descarrega o prefetch antigo se existir
                    if self.next_sound:
                        self.next_sound.unload()
                        self.next_sound = None
                    
                    # Carrega o novo som
                    logger.info(f"▶ A reproduzir bloco {index}: {os.path.basename(file_path)}")
                    self.current_sound = SoundLoader.load(file_path)

                if self.current_sound:
                    self.current_sound.play()
                    # Agenda pré-carregamento do próximo bloco
                    Clock.schedule_once(lambda dt: self._prefetch_next(), 1.0)
                else:
                    logger.error(f"Falha ao carregar áudio: {file_path}")
            else:
                logger.error(f"Ficheiro inválido ou não existe: {file_path}")
                
        except Exception as e:
            logger.error(f"Erro ao reproduzir ficheiro: {e}")

    @mainthread
    def _prefetch_next(self):
        """Pré-carrega o próximo bloco para transições suaves."""
        if not self._play_queue or self.next_sound or self.stop_requested:
            return
        
        _, next_path = self._play_queue[0]
        if os.path.exists(next_path) and os.path.getsize(next_path) > MIN_FILE_SIZE:
            try:
                self.next_sound = SoundLoader.load(next_path)
                logger.debug(f"Próximo som pré-carregado: {os.path.basename(next_path)}")
            except Exception as e:
                logger.warning(f"Falha no pré-carregamento: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE CONTROLO DE REPRODUÇÃO
    # ══════════════════════════════════════════════════════════════════════════

    def _start_playback_loop(self):
        """Inicia o loop que monitora o fim de cada bloco."""
        self._stop_clock()
        self._clock_event = Clock.schedule_interval(self._playback_tick, PAUSE_TICK_INTERVAL)
        logger.debug("Loop de reprodução iniciado")

    def _playback_tick(self, dt):
        """Tick do loop de reprodução - verifica se o bloco atual terminou."""
        if self.stop_requested:
            self._stop_clock()
            return
        
        if self.current_sound and self.current_sound.state == 'stop' and not self._in_pause:
            if self._play_queue:
                self._in_pause = True
                self._pause_event = Clock.schedule_once(self._end_pause, PAUSE_BETWEEN_BLOCKS)

    def _end_pause(self, dt):
        """Termina a pausa e reproduz o próximo bloco."""
        self._in_pause = False
        if self._play_queue and not self.stop_requested:
            idx, path = self._play_queue.popleft()
            self._play_file(idx, path)

    def _stop_clock(self):
        """Para o clock de monitorização."""
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def _cancel_pause(self):
        """Cancela a pausa agendada."""
        if self._pause_event:
            self._pause_event.cancel()
            self._pause_event = None
        self._in_pause = False

    def is_playing(self):
        """Verifica se está a reproduzir áudio atualmente."""
        return bool(self.current_sound and self.current_sound.state == 'play')

    def stop_audio(self):
        """
        Para toda a reprodução e limpa todos os recursos.
        
        Esta função é crítica para evitar fugas de memória (memory leaks).
        """
        logger.info("A parar reprodução de áudio...")
        
        self.stop_requested = True
        self._stop_clock()
        self._cancel_pause()
        self._play_queue.clear()
        self._download_active = False
        
        # Limpa o som pré-carregado
        if self.next_sound:
            try:
                self.next_sound.unload()
            except:
                pass
            self.next_sound = None
        
        # Limpa o som atual
        if self.current_sound:
            try:
                self.current_sound.stop()
                self.current_sound.unload()
            except:
                pass
            self.current_sound = None
        
        self.stop_requested = False
        logger.info("✓ Reprodução parada e recursos libertados")