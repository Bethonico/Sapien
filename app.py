from flask import Flask, render_template, jsonify, request, send_file, abort
from engine import SapienEngine
import os

app = Flask(__name__)
engine = SapienEngine()


# ── Páginas ───────────────────────────────────────────────────────────
@app.route("/")
def home():
    novels = engine.get_library()
    return render_template("home.html", novels=novels)


@app.route("/reader/<novel_name>/<int:chapter_idx>")
def reader(novel_name, chapter_idx):
    chapters = engine.get_chapters_list(novel_name)
    data = engine.get_chapter(novel_name, chapter_idx)
    engine.update_reading_progress(novel_name, chapter_idx)
    return render_template(
        "reader.html",
        novel_name=novel_name,
        chapter_idx=chapter_idx,
        chapters=chapters,
        title=data["title"],
        content=data["content"],
        total=len(chapters),
    )


# ── API JSON ──────────────────────────────────────────────────────────
@app.route("/api/chapter/<novel_name>/<int:idx>")
def api_chapter(novel_name, idx):
    data = engine.get_chapter(novel_name, idx)
    engine.update_reading_progress(novel_name, idx)
    return jsonify(data)


@app.route("/api/import", methods=["POST"])
def api_import():
    messages = []

    def on_progress(msg):
        messages.append(msg)

    # Roda síncrono para retornar feedback imediato ao cliente
    import threading, time
    done = threading.Event()
    result_box = [False]

    def on_complete(found):
        result_box[0] = found
        done.set()

    engine.check_new_imports(on_progress=on_progress, on_complete=on_complete)
    done.wait(timeout=60)  # aguarda até 60s

    return jsonify({
        "status": "ok",
        "imported": result_box[0],
        "messages": messages,
    })


@app.route("/api/library")
def api_library():
    return jsonify(engine.get_library())


# ── Áudio ─────────────────────────────────────────────────────────────
@app.route("/api/audio/info/<novel_name>/<int:cap_idx>")
def audio_info(novel_name, cap_idx):
    data = engine.get_chapter(novel_name, cap_idx)
    blocks = engine.audio._group_paragraphs(data["content"])
    return jsonify({"total_parts": len(blocks)})


@app.route("/api/audio/<novel_name>/<int:cap_idx>/<int:part>")
def serve_audio(novel_name, cap_idx, part):
    """Gera (se necessário) e serve o chunk de áudio correspondente."""
    novel_folder = novel_name.replace(" ", "_").lower()
    file_path = engine.audio.get_audio_path(novel_folder, cap_idx, part)

    if not os.path.exists(file_path):
        data = engine.get_chapter(novel_name, cap_idx)
        blocks = engine.audio._group_paragraphs(data["content"])

        if part >= len(blocks):
            return jsonify({"error": "part not found"}), 404

        success = engine.audio.generate_chunk(blocks[part], file_path)
        if not success:
            return jsonify({"error": "audio generation failed"}), 500

    return send_file(file_path, mimetype="audio/mpeg")


# ── Capas ─────────────────────────────────────────────────────────────
@app.route("/cover/<path:filename>")
def serve_cover(filename):
    if not os.path.exists(filename):
        abort(404)
    return send_file(filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)