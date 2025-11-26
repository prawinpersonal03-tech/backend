# whisper_server.py
import os
import tempfile
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException

app = Flask(__name__)
CORS(app)

model = whisper.load_model("small")

SUPPORTED_LANGUAGES = {
    "en", "hi", "ta", "te", "ml", "mr", "bn", "kn", "gu", "pa", "or", "ur",
    "fr", "de", "es", "ru", "ar", "ja", "ko", "zh"
}

def normalize_lang_code(code):
    if not code:
        return None
    code = code.strip().lower()
    if len(code) == 2:
        return code
    mapping = {
        "chinese": "zh",
        "mandarin": "zh",
        "hindi": "hi",
        "tamil": "ta",
        "telugu": "te",
        "malayalam": "ml",
        "english": "en"
    }
    return mapping.get(code, code[:2])

def detect_language_whisper(result, transcript):
    try:
        if isinstance(result, dict):
            w = result.get("language")
            if w:
                return normalize_lang_code(w)
    except Exception:
        pass
    try:
        detected = detect(transcript)
        return normalize_lang_code(detected)
    except Exception:
        return None

def looks_like_transliteration(original, translated):
    if not translated or not translated.strip():
        return True
    if original.strip() == translated.strip():
        return True
    return False

def translate_with_source(text, target_lang, source_lang=None):
    src = source_lang if (source_lang and source_lang in SUPPORTED_LANGUAGES) else "auto"
    try:
        translated = GoogleTranslator(source=src, target=target_lang).translate(text)
        if looks_like_transliteration(text, translated) and src != "auto":
            try:
                alt = GoogleTranslator(source="auto", target=target_lang).translate(text)
                if not looks_like_transliteration(text, alt):
                    return alt
            except Exception:
                pass
        return translated
    except Exception:
        try:
            return GoogleTranslator(source="auto", target=target_lang).translate(text)
        except Exception:
            return None

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    try:
        target_lang = (request.form.get("target_lang") or "en").strip().lower()
        source_hint = request.form.get("source_lang")
        if target_lang not in SUPPORTED_LANGUAGES:
            target_lang = "en"
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        uploaded = request.files["file"]
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(uploaded.filename or "tmp")[1] or ".wav")
        os.close(fd)
        with open(temp_path, "wb") as f:
            f.write(uploaded.read())
        size = os.path.getsize(temp_path)
        if size == 0:
            os.remove(temp_path)
            return jsonify({"error": "Uploaded file is empty"}), 400
        result = model.transcribe(temp_path, task="transcribe")
        transcript = (result.get("text") if isinstance(result, dict) else "") or ""
        detected = detect_language_whisper(result, transcript)
        if source_hint:
            detected = normalize_lang_code(source_hint)
        if not transcript.strip():
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return jsonify({
                "transcript": "",
                "detected_source": detected,
                "original_transcript": transcript,
                "error": "No speech recognized. Ensure audio has speech and ffmpeg is installed on server."
            }), 200
        if detected == target_lang:
            translated = translate_with_source(transcript, target_lang, source_lang=detected)
            translated = translated if translated is not None else transcript
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return jsonify({
                "transcript": translated,
                "detected_source": detected,
                "original_transcript": transcript
            }), 200
        translated = translate_with_source(transcript, target_lang, source_lang=detected)
        if translated is None:
            translated = ""
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return jsonify({
            "transcript": translated,
            "detected_source": detected,
            "original_transcript": transcript
        }), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500

@app.route("/translate", methods=["POST"])
def translate_text():
    try:
        text = (request.form.get("text") or "").strip()
        target_lang = (request.form.get("target_lang") or "en").strip().lower()
        source_hint = request.form.get("source_lang")
        if not text:
            return jsonify({"translated": "", "error": "No text provided."}), 200
        if target_lang not in SUPPORTED_LANGUAGES:
            target_lang = "en"
        detected = None
        if source_hint:
            detected = normalize_lang_code(source_hint)
        else:
            try:
                detected = normalize_lang_code(detect(text))
            except Exception:
                detected = None
        if detected == target_lang:
            translated = translate_with_source(text, target_lang, source_lang=detected)
            translated = translated if translated is not None else text
            return jsonify({"translated": translated, "detected_source": detected}), 200
        translated = translate_with_source(text, target_lang, source_lang=detected)
        if translated is None:
            return jsonify({"translated": "", "detected_source": detected, "error": "Translation failed."}), 200
        return jsonify({"translated": translated, "detected_source": detected}), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
