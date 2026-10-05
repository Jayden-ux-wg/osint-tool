import streamlit as st
import asyncio
import aiohttp
import json
import io
import csv
import random
import re
import time
import concurrent.futures
from urllib.parse import quote
from datetime import datetime

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Stealth OSINT Engine v6.0 Ultimate",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DARK ULTIMATE STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #06080a; color: #00ff88; font-family: 'JetBrains Mono', 'Courier New', monospace; }
    h1, h2, h3 { color: #00e5ff !important; font-family: 'JetBrains Mono', monospace; text-shadow: 0px 0px 12px rgba(0, 229, 255, 0.4); }
    .stTextInput input { background-color: #0d1117; color: #00ff88; border: 1px solid #00e5ff; font-family: monospace; }
    .stButton button { background: linear-gradient(45deg, #00e5ff, #0055ff); color: black; font-weight: bold; border-radius: 4px; border: none; width: 100%; padding: 0.6rem 1rem; }
    .stButton button:hover { background: linear-gradient(45deg, #00ff88, #00e5ff); color: #000; box-shadow: 0 0 15px rgba(0, 255, 136, 0.6); }
    div[data-testid="stMetricValue"] { color: #00ff88 !important; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

# --- PLATFORM DATABASE ---
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
        "Keybase": "https://keybase.io/{}",
        "Facebook": "https://www.facebook.com/{}",
        "Snapchat": "https://www.snapchat.com/add/{}",
        "VK": "https://vk.com/{}"
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
        "NameMC": "https://namemc.com/profile/{}",
        "Xbox GamerCard": "https://xboxgamertag.com/search/{}",
        "PlayStation": "https://psnprofiles.com/{}"
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
        "SourceForge": "https://sourceforge.net/u/{}",
        "Dev.to": "https://dev.to/{}",
        "StackOverflow": "https://stackoverflow.com/users/{}"
    },
    "Crypto & Web3": {
        "Etherscan": "https://etherscan.io/address/{}",
        "BscScan": "https://bscscan.com/address/{}",
        "OpenSea": "https://opensea.io/{}",
        "Bitcoin Explorer": "https://www.blockchain.com/explorer/addresses/btc/{}"
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

# --- METADATEN-EXTRAKTION ---
def extract_deep_entities(html_text):
    metadata = {"title": None, "description": None, "image": None, "btc_wallets": [], "eth_wallets": [], "emails": []}
    
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

    metadata["btc_wallets"] = list(set(re.findall(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b', html_text)))
    metadata["eth_wallets"] = list(set(re.findall(r'\b0x[a-fA-F0-9]{40}\b', html_text)))
    metadata["emails"] = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html_text)))

    return metadata

async def fetch_platform(session, name, category, url_template, query, timeout_sec, proxy_url=None):
    target_url = url_template.format(query)
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    try:
        async with session.get(target_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout_sec), allow_redirects=True, proxy=proxy_url) as response:
            status = response.status
            if status == 200:
                text = await response.text(errors='ignore')
                page_text = text.lower()
                
                not_found_indicators = ["not found", "does not exist", "user not found", "account not found", "error 404", "seite nicht gefunden"]
                for indicator in not_found_indicators:
                    if indicator in page_text:
                        return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
                
                meta = extract_deep_entities(text)
                return {"name": name, "category": category, "url": target_url, "status": "FOUND", "metadata": meta}
            elif status in [403, 429]:
                return {"name": name, "category": category, "url": target_url, "status": "BLOCKED", "code": status}
            else:
                return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return {"name": name, "category": category, "url": target_url, "status": "TIMEOUT"}
    except Exception:
        return {"name": name, "category": category, "url": target_url, "status": "ERROR"}

async def run_osint_scan(targets, query, max_concurrent, timeout_sec, proxy_url):
    connector = aiohttp.TCPConnector(limit=max_concurrent, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_platform(session, name, cat, url, query, timeout_sec, proxy_url) for name, cat, url in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        clean_results = []
        for res in results:
            if isinstance(res, dict):
                clean_results.append(res)
            else:
                clean_results.append({"name": "Unbekannt", "category": "Error", "url": "", "status": "ERROR"})
        return clean_results

def execute_async_in_thread(coro):
    """Führt eine Async Koroutine isoliert in einem neuen Thread mit eigenem Event-Loop aus."""
    def worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker)
        return future.result()

# --- INITIALISIERUNG ---
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = None

st.sidebar.title("⚡ Engine Config")
selected_categories = st.sidebar.multiselect("Kategorien:", options=list(PLATFORMS_DB.keys()), default=list(PLATFORMS_DB.keys()))
proxy_input = st.sidebar.text_input("Optional Proxy (z.B. http://proxy:8080):", value="")

max_threads = st.sidebar.slider("Parallel-Verbindungen", min_value=5, max_value=30, value=15)
request_timeout = st.sidebar.slider("Timeout (Sek.)", min_value=2, max_value=10, value=4)

active_targets = []
for cat in selected_categories:
    for name, url in PLATFORMS_DB[cat].items():
        active_targets.append((name, cat, url))

st.title("⚡ Stealth OSINT Engine v6.0 Ultimate")
st.markdown("Advanced Multi-Target Intelligence Dashboard & Deep Entity Extraction.")

raw_input = st.text_input("Ziel-Benutzername oder E-Mails (kommagetrennt für Massen-Scan):", placeholder="z.B. alex123, target@domain.com")
start_scan = st.button("🚀 Ultimate Scan Starten")

if start_scan:
    if not raw_input.strip():
        st.warning("Bitte ein Ziel eingeben.")
    else:
        targets_list = [t.strip() for t in raw_input.split(",") if t.strip()]
        all_results = []
        
        with st.spinner("Scanne Plattformen im Hintergrund... Bitte warten..."):
            start_time = time.time()

            for t in targets_list:
                search_handle = t.split('@')[0] if "@" in t else t
                
                # Absturzsichere Ausführung im separaten Thread
                res = execute_async_in_thread(
                    run_osint_scan(
                        active_targets, 
                        search_handle, 
                        max_threads, 
                        request_timeout, 
                        proxy_input if proxy_input else None
                    )
                )
                all_results.extend(res)
            
            st.session_state["scan_results"] = all_results
            st.session_state["scan_time"] = round(time.time() - start_time, 2)
        
        st.success(f"Scan in {st.session_state['scan_time']}s erfolgreich beendet!")

if st.session_state["scan_results"]:
    results = st.session_state["scan_results"]
    found_list = [r for r in results if r["status"] == "FOUND"]
    blocked_list = [r for r in results if r["status"] == "BLOCKED"]
    
    score = min(100, len(found_list) * 8)
    
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Treffer", len(found_list))
    m2.metric("⚠️ Geblockt", len(blocked_list))
    m3.metric("🎯 Digital Exposure Score", f"{score}/100")
    m4.metric("⏱️ Scan-Zeit", f"{st.session_state.get('scan_time', 0)}s")

    tab_found, tab_dorks, tab_export = st.tabs(["🎯 Profil-Karten & Meta-Daten", "🔎 Multi-Engine Dorks", "💾 Report Export"])

    with tab_found:
        filter_text = st.text_input("🔍 Ergebnisse live filtern:", "")
        for item in found_list:
            if filter_text.lower() in item["name"].lower() or filter_text.lower() in item["url"].lower():
                meta = item.get("metadata", {})
                st.markdown(f"### [{item['category']}] {item['name']}")
                col_img, col_info = st.columns([1, 4])
                with col_img:
                    if meta.get("image"):
                        st.image(meta["image"], width=100)
                    else:
                        st.write("📷 Kein Bild")
                with col_info:
                    st.markdown(f"🔗 **URL:** [{item['url']}]({item['url']})")
                    if meta.get("title"):
                        st.markdown(f"**Titel:** {meta['title']}")
                    if meta.get("description"):
                        st.markdown(f"**Bio:** _{meta['description']}_")
                    if meta.get("emails"):
                        st.markdown(f"📧 **Gefundene E-Mails:** {', '.join(meta['emails'])}")
                    if meta.get("btc_wallets"):
                        st.markdown(f"🪙 **Bitcoin Wallets:** {', '.join(meta['btc_wallets'])}")
                    if meta.get("eth_wallets"):
                        st.markdown(f"🌐 **Ethereum Wallets:** {', '.join(meta['eth_wallets'])}")
                st.markdown("---")

    with tab_dorks:
        st.markdown("### Multi-Engine Dork Generator")
        q_enc = quote(raw_input)
        st.markdown(f"- 🔎 **Google Deep Search:** [Google Suche](https://www.google.com/search?q=%22{q_enc}%22)")
        st.markdown(f"- 🦆 **DuckDuckGo Leaks:** [DuckDuckGo Suche](https://duckduckgo.com/?q=%22{q_enc}%22+filetype%3Apdf)")
        st.markdown(f"- 🌐 **Yandex Global Search:** [Yandex Suche](https://yandex.com/search/?text=%22{q_enc}%22)")

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
            file_name=f"osint_v6_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        # JSON Export
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        col_json.download_button(
            label="📦 JSON herunterladen",
            data=json_data,
            file_name=f"osint_v6_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
