import os
import threading
from gtts import gTTS
from kivy.core.audio import SoundLoader

class SapienAudio:
    def __init__(self):
        # Define onde os audios serão salvos
        self.base_audio_path = os.path.join("assets", "audios")
        if not os.path.exists(self.base_audio_path):
            os.makedirs(self.base_audio_path)
        self.current_sound = None

    def download_audio(self, text, novel_name, cap_idx, on_start, on_complete):
        """Baixa o áudio via gTTS em uma thread separada"""
        def _task():
            # Pasta específica da novel
            novel_path = os.path.join(self.base_audio_path, novel_name.replace(" ", "_"))
            if not os.path.exists(novel_path):
                os.makedirs(novel_path)
            
            file_path = os.path.join(novel_path, f"cap_{cap_idx}.mp3")
            
            # Só baixa se o arquivo não existir
            if not os.path.exists(file_path):
                if on_start:
                    on_start()
                try:
                    tts = gTTS(text=text, lang='pt', slow=False)
                    tts.save(file_path)
                except Exception as e:
                    print(f"Erro ao baixar áudio: {e}")
                    return
            
            if on_complete:
                on_complete(file_path)
            
        threading.Thread(target=_task, daemon=True).start()

    def play_audio(self, file_path):
        """Toca o arquivo MP3 usando o SoundLoader do Kivy"""
        self.stop_audio() # Para o áudio atual antes de começar outro
        
        self.current_sound = SoundLoader.load(file_path)
        if self.current_sound:
            self.current_sound.play()
        else:
            print("Erro: Não foi possível carregar o arquivo de áudio.")

    def stop_audio(self):
        """Para a reprodução"""
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound.unload() # Libera o arquivo da memória
            self.current_sound = None