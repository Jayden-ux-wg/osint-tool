import streamlit as st
import asyncio
import aiohttp
import json
import io
import csv
import random
import re
import time
from urllib.parse import quote
from datetime import datetime

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Stealth OSINT Engine v5.0 Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DARK ENTERPRISE STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0a0c10; color: #00ff88; font-family: 'JetBrains Mono', 'Courier New', monospace; }
    h1, h2, h3 { color: #ff3366 !important; font-family: 'JetBrains Mono', monospace; text-shadow: 0px 0px 10px rgba(255, 51, 102, 0.4); }
    .stTextInput input { background-color: #12161f; color: #00ff88; border: 1px solid #ff3366; font-family: monospace; }
    .stButton button { background: linear-gradient(45deg, #ff3366, #990033); color: white; font-weight: bold; border-radius: 4px; border: 1px solid #ff6688; width: 100%; padding: 0.6rem 1rem; }
    .stButton button:hover { background: linear-gradient(45deg, #ff6688, #ff3366); color: #fff; box-shadow: 0 0 12px rgba(0, 255, 136, 0.4); }
    div[data-testid="stMetricValue"] { color: #00ff88 !important; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

PLATFORMS_DB = {
    "Social & Networks": {
        "GitHub": "https://github.com/{}",
        "X (Twitter)": "https://twitter.com/{}",
        "Reddit": "https://www.reddit.com/user/{}",
        "Instagram": "https://www.instagram.com/{}",
        "TikTok": "https://www.tiktok.com/@{}",
        "LinkedIn": "https://www.linkedin.com/in/{}",
        "Telegram": "https://t.me/{}",
        "Pinterest": "https://pinterest.com/{}",
        "Mastodon": "https://mastodon.social/@{}",
        "Medium": "https://medium.com/@{}",
        "Linktree": "https://linktr.ee/{}",
        "Tumblr": "https://{}.tumblr.com",
        "Patreon": "https://www.patreon.com/{}",
        "Keybase": "https://keybase.io/{}"
    },
    "Gaming & Esports": {
        "Steam": "https://steamcommunity.com/id/{}",
        "Twitch": "https://www.twitch.tv/{}",
        "Kick": "https://kick.com/{}",
        "Chess.com": "https://www.chess.com/member/{}",
        "Lichess": "https://lichess.org/@/{}",
        "Speedrun.com": "https://www.speedrun.com/user/{}",
        "Roblox": "https://www.roblox.com/user.aspx?username={}",
        "Duolingo": "https://www.duolingo.com/profile/{}",
        "NameMC (Minecraft)": "https://namemc.com/profile/{}"
    },
    "Developer & Tech": {
        "GitLab": "https://gitlab.com/{}",
        "Bitbucket": "https://bitbucket.org/{}",
        "Replit": "https://replit.com/@{}",
        "Docker Hub": "https://hub.docker.com/u/{}",
        "Npmjs": "https://www.npmjs.com/~{}",
        "PyPI": "https://pypi.org/user/{}",
        "CodePen": "https://codepen.io/{}",
        "HackerNews": "https://news.ycombinator.com/user?id={}",
        "SourceForge": "https://sourceforge.net/u/{}"
    },
    "Media & Creative": {
        "Spotify": "https://open.spotify.com/user/{}",
        "SoundCloud": "https://soundcloud.com/{}",
        "YouTube": "https://www.youtube.com/@{}",
        "DeviantArt": "https://www.deviantart.com/{}",
        "Bandcamp": "https://bandcamp.com/{}",
        "Vimeo": "https://vimeo.com/{}",
        "Flickr": "https://www.flickr.com/people/{}"
    }
}

def extract_metadata(html_text):
    metadata = {"title": None, "description": None, "image": None}
    
    title_match = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()
        
    desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html_text, re.IGNORECASE) or \
                 re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html_text, re.IGNORECASE)
    if desc_match:
        metadata["description"] = desc_match.group(1).strip()
        
    img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', html_text, re.IGNORECASE)
    if img_match:
        metadata["image"] = img_match.group(1).strip()
        
    return metadata

async def fetch_platform(session, name, category, url_template, query, timeout_sec):
    target_url = url_template.format(query)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        async with session.get(target_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout_sec), allow_redirects=True) as response:
            status = response.status
            
            if status == 200:
                text = await response.text()
                page_text = text.lower()
                
                not_found_indicators = [
                    "not found", "does not exist", "user not found", "account not found",
                    "seite nicht gefunden", "konto existiert nicht", "error 404", "page not found"
                ]
                for indicator in not_found_indicators:
                    if indicator in page_text:
                        return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
                
                meta = extract_metadata(text)
                return {
                    "name": name, 
                    "category": category, 
                    "url": target_url, 
                    "status": "FOUND",
                    "metadata": meta
                }
                
            elif status in [403, 429]:
                return {"name": name, "category": category, "url": target_url, "status": "BLOCKED", "code": status}
            elif status == 404:
                return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
            else:
                return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": status}
                
    except asyncio.TimeoutError:
        return {"name": name, "category": category, "url": target_url, "status": "TIMEOUT"}
    except Exception:
        return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": "Exception"}

async def run_osint_scan(targets, query, max_concurrent, timeout_sec, progress_bar, status_text):
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_platform(session, name, cat, url, query, timeout_sec)
            for name, cat, url in targets
        ]
        
        results = []
        total = len(tasks)
        completed = 0
        
        for f in asyncio.as_completed(tasks):
            res = await f
            results.append(res)
            completed += 1
            progress_bar.progress(completed / total)
            status_text.text(f"Scanne Plattformen: {completed}/{total}...")
            
        return results

# --- INITIALISIERUNG ---
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = None
if "scan_time" not in st.session_state:
    st.session_state["scan_time"] = 0.0

st.sidebar.title("⚡ Engine Config")
selected_categories = st.sidebar.multiselect("Kategorien:", options=list(PLATFORMS_DB.keys()), default=list(PLATFORMS_DB.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Performance")
max_threads = st.sidebar.slider("Parallel-Verbindungen", min_value=5, max_value=50, value=25)
request_timeout = st.sidebar.slider("Timeout (Sek.)", min_value=2, max_value=15, value=5)

active_targets = []
for cat in selected_categories:
    for name, url in PLATFORMS_DB[cat].items():
        active_targets.append((name, cat, url))

# --- MAIN UI ---
st.title("⚡ Stealth OSINT Engine v5.0 Enterprise")
st.markdown("Hochleistungs-Recherche mit Deep-Metadata Extraction & Multi-Format Export.")

input_query = st.text_input("Ziel-Benutzername oder E-Mail eingeben:", placeholder="z.B. alex123 oder target@domain.com")
start_scan = st.button("🚀 Enterprise Scan Starten")

is_email = "@" in input_query and "." in input_query
clean_query = input_query.strip()

if is_email:
    search_handle = clean_query.split('@')[0]
    st.info(f"💡 **E-Mail-Modus**: Suchen werden mit dem Namenskürzel `{search_handle}` ausgeführt.")
else:
    search_handle = clean_query

if start_scan:
    if not clean_query:
        st.warning("Bitte gib ein gültiges Ziel ein.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        start_time = time.time()
        results = asyncio.run(run_osint_scan(active_targets, search_handle, max_threads, request_timeout, progress_bar, status_text))
        end_time = time.time()

        progress_bar.empty()
        status_text.empty()
        st.session_state["scan_results"] = results
        st.session_state["scan_time"] = round(end_time - start_time, 2)
        st.success(f"Scan in {st.session_state['scan_time']} Sekunden abgeschlossen!")

if st.session_state["scan_results"]:
    results = st.session_state["scan_results"]
    found_list = [r for r in results if r["status"] == "FOUND"]
    blocked_list = [r for r in results if r["status"] == "BLOCKED"]
    not_found_list = [r for r in results if r["status"] == "NOT_FOUND"]
    error_list = [r for r in results if r["status"] in ["ERROR", "TIMEOUT"]]

    st.markdown("---")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("✅ Gefunden", len(found_list))
    m2.metric("⚠️ Geblockt", len(blocked_list))
    m3.metric("🚫 Nicht vorhanden", len(not_found_list))
    m4.metric("❌ Fehler/Timeout", len(error_list))
    m5.metric("⏱️ Laufzeit", f"{st.session_state['scan_time']}s")

    tab_found, tab_dorks, tab_blocked, tab_export = st.tabs([
        f"🎯 Profil-Karten ({len(found_list)})", 
        "🔎 Google OSINT Dorks",
        f"⚠️ Geblockt ({len(blocked_list)})", 
        "💾 Export (CSV & JSON)"
    ])

    with tab_found:
        if found_list:
            for item in found_list:
                meta = item.get("metadata", {})
                with st.container():
                    st.markdown(f"### [{item['category']}] {item['name']}")
                    col_img, col_info = st.columns([1, 4])
                    with col_img:
                        if meta.get("image"):
                            st.image(meta["image"], width=110)
                        else:
                            st.write("📷 Kein Profilbild")
                    with col_info:
                        if meta.get("title"):
                            st.markdown(f"**Titel:** {meta['title']}")
                        if meta.get("description"):
                            st.markdown(f"**Bio:** _{meta['description']}_")
                        st.markdown(f"🔗 **URL:** [{item['url']}]({item['url']})")
                    st.markdown("---")
        else:
            st.write("Keine Treffer gefunden.")

    with tab_dorks:
        st.markdown("### Automatische Google Search Dorks")
        q_enc = quote(clean_query)
        st.markdown(f"- 📄 **Dokumente (PDF/DOCX):** [Google Suche](https://www.google.com/search?q=site:*+%22{q_enc}%22+filetype:pdf+OR+filetype:docx)")
        st.markdown(f"- 💬 **Pastebin & Code-Leaks:** [Google Suche](https://www.google.com/search?q=site:pastebin.com+OR+site:github.com+%22{q_enc}%22)")
        st.markdown(f"- 📱 **Social-Media-Erwähnungen:** [Google Suche](https://www.google.com/search?q=%22{q_enc}%22+site:twitter.com+OR+site:instagram.com)")

    with tab_blocked:
        for item in blocked_list:
            st.markdown(f"- **{item['name']}** (HTTP-Code {item.get('code')})")

    with tab_export:
        col_csv, col_json = st.columns(2)
        
        # CSV Export
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Name", "Kategorie", "Status", "URL", "Titel", "Description"])
        for r in results:
            meta = r.get("metadata", {})
            writer.writerow([r["name"], r["category"], r["status"], r["url"], meta.get("title"), meta.get("description")])
            
        col_csv.download_button(
            label="📄 CSV herunterladen",
            data=csv_buffer.getvalue(),
            file_name=f"osint_v5_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # JSON Export
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        col_json.download_button(
            label="📦 JSON herunterladen",
            data=json_data,
            file_name=f"osint_v5_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
