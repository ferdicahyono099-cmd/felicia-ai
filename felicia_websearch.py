# ==========================================
# FELICIA WEB SEARCH v3 - Akurat
# + Query enhancement + Trusted domain + Freshness
# + Multi-query strategy + Snippet cleaning
# ==========================================
from ddgs import DDGS
from datetime import datetime
import re


# ==========================================
# DOMAIN TERPERCAYA
# ==========================================
TRUSTED_DOMAINS = {
    # Pemerintah Indonesia (paling tinggi)
    ".go.id": 20,
    ".ac.id": 15,
    # Media nasional besar
    "antaranews.com": 18,
    "kompas.com": 15,
    "tempo.co": 15,
    "detik.com": 12,
    "cnnindonesia.com": 15,
    "tribunnews.com": 10,
    "liputan6.com": 12,
    "kominfo.go.id": 20,
    "setneg.go.id": 20,
    "presidenri.go.id": 25,
    "kpu.go.id": 20,
    "bps.go.id": 18,
    # Media internasional
    "reuters.com": 18,
    "bbc.com": 18,
    "bbc.co.uk": 18,
    "apnews.com": 18,
    "aljazeera.com": 15,
    "nytimes.com": 15,
    "theguardian.com": 15,
    # Data & referensi
    "wikipedia.org": 10,
    "britannica.com": 12,
    # Teknologi & crypto
    "github.com": 12,
    "stackoverflow.com": 10,
    "coindesk.com": 15,
    "coinmarketcap.com": 15,
    "coingecko.com": 15,
    "tradingview.com": 12,
    "yahoo.com": 10,
    "bloomberg.com": 15,
}


# ==========================================
# ENHANCE QUERY (perbaiki pertanyaan user)
# ==========================================
def enhance_query(query: str) -> str:
    """
    Perbaiki query biar lebih akurat:
    - Tambah tahun untuk pertanyaan dinamis
    - Tambah 'site:go.id' untuk pertanyaan pemerintahan
    - Buang kata tanya yang gak perlu
    """
    q = query.strip()
    q_lower = q.lower()
    tahun = datetime.now().year

    # Pertanyaan tentang jabatan/pejabat → tambah tahun + prioritas go.id
    trigger_jabatan = ["presiden", "wakil presiden", "menteri", "gubernur",
                       "bupati", "wali kota", "ketua", "ceo", "direktur"]
    if any(t in q_lower for t in trigger_jabatan):
        if str(tahun) not in q and str(tahun - 1) not in q:
            q = f"{q} {tahun}"

    # Pertanyaan harga/kurs
    trigger_harga = ["harga", "kurs", "nilai tukar", "berapa"]
    if any(t in q_lower for t in trigger_harga):
        if "hari ini" not in q_lower and "terbaru" not in q_lower:
            q = f"{q} hari ini"

    # Pertanyaan berita → tambah "terbaru"
    if any(t in q_lower for t in ["berita", "kabar", "update"]):
        if "terbaru" not in q_lower:
            q = f"{q} terbaru"

    return q


# ==========================================
# SKOR DOMAIN
# ==========================================
def skor_domain(url: str) -> int:
    """Beri skor lebih tinggi untuk domain terpercaya."""
    if not url:
        return 0
    url_lower = url.lower()
    for dom, skor in TRUSTED_DOMAINS.items():
        if dom in url_lower:
            return skor
    return 0


# ==========================================
# FRESHNESS (deteksi tanggal di snippet)
# ==========================================
def cek_freshness(snippet: str) -> int:
    """Deteksi kesegaran dari snippet."""
    if not snippet:
        return 0
    s = snippet.lower()

    # Sangat baru
    if any(k in s for k in ["hari ini", "jam lalu", "menit lalu", "baru saja",
                             "hours ago", "minutes ago", "today", "just now",
                             "detik lalu", "sekarang"]):
        return 15

    # Baru
    if any(k in s for k in ["kemarin", "yesterday", "1 day ago", "tadi malam"]):
        return 10

    # Minggu ini
    if any(k in s for k in ["minggu ini", "this week", "days ago"]):
        return 6

    # Bulan ini
    bulan_id = ["januari", "februari", "maret", "april", "mei", "juni",
                "juli", "agustus", "september", "oktober", "november", "desember"]
    bulan_en = ["january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december"]
    tahun = str(datetime.now().year)
    if tahun in s and any(b in s for b in bulan_id + bulan_en):
        return 4

    return 0


# ==========================================
# SNIPPET CLEANING
# ==========================================
def clean_snippet(snippet: str) -> str:
    """Bersihin snippet dari karakter aneh."""
    if not snippet:
        return ""
    # Buang elipsis berlebih
    s = re.sub(r"\.{3,}", "...", snippet)
    # Buang whitespace berlebih
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# ==========================================
# WEB SEARCH UTAMA
# ==========================================
def web_search(query: str, max_results: int = 7) -> list[dict]:
    """Cari di web, return hasil terurut by skor."""
    if not query or not query.strip():
        return []

    # Enhance query
    enhanced = enhance_query(query)
    if enhanced != query:
        print(f"[SEARCH] Enhanced: '{query}' -> '{enhanced}'")

    # Ambil lebih banyak kandidat (2x lipat untuk difilter)
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(enhanced, max_results=max_results * 3))
    except Exception as e:
        print(f"[ERR] DuckDuckGo: {e}")
        return []

    # Skor + normalisasi
    hasil = []
    for r in raw:
        title = r.get("title", "")
        url = r.get("href", "") or r.get("url", "")
        snippet = clean_snippet(r.get("body", "") or r.get("snippet", ""))

        skor_dom = skor_domain(url)
        skor_fresh = cek_freshness(snippet)
        skor_total = skor_dom + skor_fresh

        hasil.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "score": skor_total,
            "score_domain": skor_dom,
            "score_fresh": skor_fresh,
        })

    # Sort by skor tertinggi
    hasil.sort(key=lambda x: x["score"], reverse=True)

    # Buang duplikat domain (maks 2 per domain)
    seen_domains = {}
    filtered = []
    for h in hasil:
        dom = h["url"].split("/")[2] if "/" in h["url"] else h["url"]
        seen_domains[dom] = seen_domains.get(dom, 0) + 1
        if seen_domains[dom] <= 2:
            filtered.append(h)
        if len(filtered) >= max_results:
            break

    return filtered


# ==========================================
# OUTPUT TEKS (untuk LLM)
# ==========================================
def web_search_teks(query: str, max_results: int = 7) -> str:
    """Versi teks siap kirim ke LLM."""
    results = web_search(query, max_results=max_results)
    if not results:
        return ""

    lines = [f"# Hasil Pencarian Web: {query}"]
    lines.append(f"_Tanggal: {datetime.now().strftime('%d %B %Y')}_")
    lines.append(f"_(Diurutkan: sumber terpercaya & terbaru di atas)_\n")

    for i, r in enumerate(results, 1):
        # Tag
        tags = []
        if r["score_domain"] >= 18:
            tags.append("SUMBER RESMI")
        elif r["score_domain"] >= 12:
            tags.append("SUMBER TERPERCAYA")
        if r["score_fresh"] >= 10:
            tags.append("BARU")
        tag_str = f" [{' | '.join(tags)}]" if tags else ""

        lines.append(f"## {i}. {r['title']}{tag_str}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"{r['snippet']}\n")

    # Instruksi buat LLM
    lines.append("---")
    lines.append("INSTRUKSI UNTUK AI:")
    lines.append("- Prioritaskan informasi dari [SUMBER RESMI] dan [SUMBER TERPERCAYA].")
    lines.append("- Jika ada info dengan tag [BARU], pakai itu daripada pengetahuan lama.")
    lines.append("- Jika ada konflik antar sumber, sebutkan perbedaannya.")
    lines.append("- SELALU sebutkan sumber (nama media/situs) di jawaban.")
    lines.append(f"- Tahun sekarang: {datetime.now().year}. Jangan pakai data lama.")
    lines.append("- Jika hasil pencarian tidak menjawab, bilang jujur 'saya tidak yakin'.")

    return "\n".join(lines)


# ==========================================
# DETEKSI KAPAN BUTUH WEB SEARCH
# ==========================================
def perlu_web_search(pertanyaan: str) -> bool:
    """Heuristik: kapan butuh web search?"""
    t = pertanyaan.lower()
    triggers = [
        # Waktu
        "sekarang", "hari ini", "terbaru", "kemarin", "besok",
        "minggu ini", "bulan ini", "tahun ini", "tadi",
        # Data real-time
        "harga", "kurs", "cuaca", "suhu", "berita", "skor", "hasil",
        "jadwal", "tanding", "vs", "melawan",
        # Tahun
        "2024", "2025", "2026", "2027",
        # Entitas yang sering berubah
        "presiden", "menteri", "gubernur", "bupati", "wali kota",
        "ceo", "juara", "peringkat", "siapa yang",
        # Pertanyaan faktual
        "siapa yang menang", "kapan", "di mana",
    ]
    return any(k in t for k in triggers)


# ==========================================
# TEST
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("TEST FELICIA WEB SEARCH v3")
    print("=" * 60)

    queries = [
        "siapa presiden Indonesia sekarang",
        "harga bitcoin hari ini",
        "berita teknologi terbaru",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"Perlu search? {perlu_web_search(q)}")
        print('=' * 60)

        hasil = web_search(q, max_results=5)
        for i, r in enumerate(hasil, 1):
            tags = []
            if r["score_domain"] >= 18:
                tags.append("RESMI")
            elif r["score_domain"] >= 12:
                tags.append("TERPERCAYA")
            if r["score_fresh"] >= 10:
                tags.append("BARU")
            tag_str = f" [{'|'.join(tags)}]" if tags else ""

            print(f"\n{i}. {r['title']}{tag_str}")
            print(f"   {r['url']}")
            print(f"   Score: {r['score']} (dom:{r['score_domain']} fresh:{r['score_fresh']})")
            print(f"   {r['snippet'][:200]}...")

    print("\n" + "=" * 60)
    print("Selesai")
    print("=" * 60)