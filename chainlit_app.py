# chainlit_app.py
# Felicia AI — UI utama (Chainlit)
# Otak: Groq openai/gpt-oss-20b (FAST) & openai/gpt-oss-120b (DEEP)
# Web Search: DuckDuckGo (gratis, gak butuh API key)
# RAG: di-comment sementara (RAM 4GB)

import sys
import os

# ==== PASTIKAN FOLDER PROYEK DI SYS.PATH ====
PROYEK_DIR = os.path.dirname(os.path.abspath(__file__))
if PROYEK_DIR not in sys.path:
    sys.path.insert(0, PROYEK_DIR)

# ==== BARU IMPORT YANG LAIN ====
import traceback
import chainlit as cl
from groq import Groq
from dotenv import load_dotenv

# ==== LOAD ENV ====
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY gak ada di .env")

client = Groq(api_key=GROQ_API_KEY)

# ==== KONFIG OTAK ====
OTAK = {
    "FAST": "openai/gpt-oss-20b",
    "DEEP": "openai/gpt-oss-120b",
}
OTAK_DEFAULT = "DEEP"

# ==== LAZY LOAD WEB SEARCH ====
_web_funcs = None

def get_web_search():
    """Lazy load fungsi web search — biar startup cepet."""
    global _web_funcs
    if _web_funcs is None:
        try:
            from felicia_websearch import perlu_web_search, web_search_teks
            _web_funcs = (perlu_web_search, web_search_teks)
            print("[WEB] Web search loaded ✅")
        except Exception as e:
            print(f"[WEB] Gagal load web search: {e}")
            _web_funcs = (None, None)
    return _web_funcs

# ==== AUTH ====
@cl.password_auth_callback
def auth(username, password):
    if username == "ferdi" and password == "felicia2026":
        return cl.User(
            identifier="ferdi",
            metadata={"role": "guru", "level": "ultra"}
        )
    return None

# ==== START CHAT ====
@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    nama = user.identifier if user else "tamu"

    cl.user_session.set("otak", OTAK_DEFAULT)
    cl.user_session.set("riwayat", [])

    await cl.Message(
        content=f"""Halo **{nama}**! 👋

Saya **Felicia AI** — asisten Indonesia yang jujur, transparan, bisa diaudit.

**Status:**
- Otak aktif: `{OTAK[OTAK_DEFAULT]}` ({OTAK_DEFAULT})
- Web search: **aktif** (DuckDuckGo, gratis)
- RAG: offline sementara (RAM 4GB)

**Command:**
- `/fast` — otak cepat (20b)
- `/deep` — otak dalam (120b)
- `/status` — liat status

Mau tanya apa, Kapten?"""
    ).send()

# ==== COMMAND HANDLER ====
async def handle_command(teks):
    cmd = teks.lower().split()[0]

    if cmd == "/fast":
        cl.user_session.set("otak", "FAST")
        await cl.Message(content=f"✅ Otak diganti ke **FAST** (`{OTAK['FAST']}`)").send()

    elif cmd == "/deep":
        cl.user_session.set("otak", "DEEP")
        await cl.Message(content=f"✅ Otak diganti ke **DEEP** (`{OTAK['DEEP']}`)").send()

    elif cmd == "/status":
        otak = cl.user_session.get("otak", OTAK_DEFAULT)
        riwayat = cl.user_session.get("riwayat", [])
        await cl.Message(
            content=f"""**Status Felicia AI**

- Otak aktif: `{OTAK[otak]}` ({otak})
- Riwayat sesi: {len(riwayat)} pesan
- Web search: aktif (DuckDuckGo)
- RAG: offline sementara
"""
        ).send()

    else:
        await cl.Message(content=f"⚠️ Command `{cmd}` gak dikenal.").send()

# ==== HANDLE PESAN ====
@cl.on_message
async def on_message(msg: cl.Message):
    teks = msg.content.strip()
    if not teks:
        return

    # ==== COMMAND ====
    if teks.startswith("/"):
        await handle_command(teks)
        return

    # ==== WEB SEARCH (kalau perlu) ====
    konteks_web = ""
    perlu_web, web_search_teks = get_web_search()

    if perlu_web and web_search_teks:
        try:
            if perlu_web(teks):
                async with cl.Step(name="Web Search", type="tool") as step:
                    step.output = f"Cari di web: {teks}"
                    hasil_web = web_search_teks(teks, max_results=5)
                    if hasil_web:
                        konteks_web = hasil_web
                        step.output = f"✅ Dapet {len(hasil_web)} karakter konteks"
                    else:
                        step.output = "⚠️ Gak ada hasil"
        except Exception as e:
            print(f"[WEB ERROR] {traceback.format_exc()}")

    # ==== BIKIN PROMPT ====
    if konteks_web:
        prompt = f"""Kamu adalah Felicia AI, asisten Indonesia yang jujur dan transparan.

Jawab pertanyaan user berdasarkan KONTEKS WEB di bawah ini.
Konteks ini diambil dari internet terkini — bisa lebih baru dari pengetahuanmu.
Jangan ngarang. Kalau konteks gak cukup, bilang terus terang.

=== KONTEKS WEB ===
{konteks_web}

=== PERTANYAAN ===
{teks}

=== JAWABAN ==="""
    else:
        prompt = f"""Kamu adalah Felicia AI, asisten Indonesia yang jujur dan transparan.

Jawab pertanyaan user dengan pengetahuanmu sendiri.
Kalau gak yakin, bilang "saya kurang yakin".

=== PERTANYAAN ===
{teks}

=== JAWABAN ="""

    # ==== KIRIM KE GROQ ====
    otak_aktif = cl.user_session.get("otak", OTAK_DEFAULT)
    model = OTAK[otak_aktif]

    pesan = cl.Message(content="")
    await pesan.send()

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Kamu adalah Felicia AI, asisten Indonesia yang jujur dan transparan. Jawab dengan bahasa Indonesia yang baik, santai, dan jelas."},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=2000,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                await pesan.stream_token(delta)

        await pesan.update()

        # simpan riwayat
        riwayat = cl.user_session.get("riwayat", [])
        riwayat.append({"q": teks, "web": bool(konteks_web)})
        cl.user_session.set("riwayat", riwayat[-10:])

    except Exception as e:
        print(f"[GROQ ERROR] {traceback.format_exc()}")
        await cl.Message(
            content=f"⚠️ **Groq error:** `{str(e)}`"
        ).send()