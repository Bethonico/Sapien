import os
import re

class SapienAudio:
    """Gerencia a geração e cache de áudio por chunks de parágrafo."""

    MAX_CHARS = 500  # Limite de caracteres por bloco de TTS

    def _group_paragraphs(self, content: str) -> list[str]:
        """
        Divide o conteúdo em blocos menores, respeitando parágrafos
        e o limite de caracteres do gTTS.
        """
        raw_paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        blocks = []
        current = ""

        for para in raw_paragraphs:
            # Se o parágrafo sozinho ultrapassa o limite, divide por sentenças
            if len(para) > self.MAX_CHARS:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= self.MAX_CHARS:
                        current += (" " if current else "") + sentence
                    else:
                        if current:
                            blocks.append(current.strip())
                        current = sentence
            else:
                if len(current) + len(para) + 2 <= self.MAX_CHARS:
                    current += ("\n\n" if current else "") + para
                else:
                    if current:
                        blocks.append(current.strip())
                    current = para

        if current:
            blocks.append(current.strip())

        return blocks

    def get_audio_path(self, novel_folder: str, cap_idx: int, part: int) -> str:
        """Retorna o caminho esperado para um chunk de áudio."""
        file_name = f"cache_{novel_folder}_{cap_idx}_part_{part}.mp3"
        return os.path.join("assets", "audios", novel_folder, file_name)

    def generate_chunk(self, text: str, output_path: str, lang: str = "pt") -> bool:
        """
        Gera um arquivo de áudio MP3 via gTTS.
        Retorna True em sucesso, False em erro.
        """
        try:
            from gtts import gTTS
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            gTTS(text=text, lang=lang, slow=False).save(output_path)
            return True
        except Exception as e:
            print(f"[AudioManager] Erro ao gerar áudio: {e}")
            return False