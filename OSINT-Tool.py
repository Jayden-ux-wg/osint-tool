import streamlit as st
import asyncio
import aiohttp
import json
import io
import csv
import random
from datetime import datetime

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Stealth OSINT Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN-ANPASSUNG (Dark / Hacker Theme) ---
st.markdown("""
    <style>
    .stApp { background-color: #080808; color: #00ff66; font-family: 'Courier New', Courier, monospace; }
    h1, h2, h3 { color: #ff2a2a !important; font-family: 'Courier New', Courier, monospace; text-shadow: 0px 0px 8px rgba(255, 42, 42, 0.4); }
    .stTextInput input { background-color: #121212; color: #00ff66; border: 1px solid #ff2a2a; font-family: 'Courier New', Courier, monospace; }
    .stButton button { background: linear-gradient(45deg, #ff2a2a, #8b0000); color: white; font-weight: bold; border-radius: 4px; border: 1px solid #ff5555; width: 100%; padding: 0.6rem 1rem; }
    .stButton button:hover { background: linear-gradient(45deg, #ff5555, #ff2a2a); color: #fff; border: 1px solid #00ff66; box-shadow: 0 0 10px rgba(0, 255, 102, 0.5); }
    div[data-testid="stMetricValue"] { color: #00ff66 !important; font-family: 'Courier New', Courier, monospace; }
    </style>
""", unsafe_allow_html=True)

# --- USER-AGENT ROTATION (STEALTH) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

# --- OSINT TARGET DATABASE ---
PLATFORMS_DB = {
    "Social & Networks": {
        "GitHub": "https://github.com/{}",
        "X (Twitter)": "https://twitter.com/{}",
        "Reddit": "https://www.reddit.com/user/{}",
        "Instagram": "https://www.instagram.com/{}",
        "TikTok": "https://www.tiktok.com/@{}",
        "LinkedIn": "https://www.linkedin.com/in/{}",
        "Facebook": "https://www.facebook.com/{}",
        "Telegram": "https://t.me/{}",
        "Pinterest": "https://pinterest.com/{}",
        "Snapchat": "https://www.snapchat.com/add/{}"
    },
    "Gaming & Esports": {
        "Steam": "https://steamcommunity.com/id/{}",
        "Twitch": "https://www.twitch.tv/{}",
        "Kick": "https://kick.com/{}",
        "Chess.com": "https://www.chess.com/member/{}",
        "Xbox": "https://account.xbox.com/en-us/profile?gamertag={}",
        "PSN Profiles": "https://psnprofiles.com/{}",
        "Fortnite Tracker": "https://fortnitetracker.com/profile/all/{}"
    },
    "Developer & Tech": {
        "GitLab": "https://gitlab.com/{}",
        "Bitbucket": "https://bitbucket.org/{}",
        "Replit": "https://replit.com/@{}",
        "StackOverflow": "https://stackoverflow.com/users/{}"
    },
    "Media & Creative": {
        "Spotify": "https://open.spotify.com/user/{}",
        "SoundCloud": "https://soundcloud.com/{}",
        "YouTube": "https://www.youtube.com/@{}",
        "Vimeo": "https://vimeo.com/{}"
    }
}

# --- ASYNC PRÜFFUNKTION ---
async def fetch_platform(session, name, category, url_template, username, timeout_sec):
    target_url = url_template.format(username, username) if url_template.count('{}') > 1 else url_template.format(username)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
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
                    "seite nicht gefunden", "konto existiert nicht", "error 404", "ungültiger benutzer"
                ]
                for indicator in not_found_indicators:
                    if indicator in page_text:
                        return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
                return {"name": name, "category": category, "url": target_url, "status": "FOUND"}
                
            elif status in [403, 429]:
                return {"name": name, "category": category, "url": target_url, "status": "BLOCKED", "code": status}
            elif status == 404:
                return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
            else:
                return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": status}
                
    except asyncio.TimeoutError:
        return {"name": name, "category": category, "url": target_url, "status": "TIMEOUT"}
    except Exception as e:
        return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": "Exception"}

# --- ASYNC ENGINE MANAGER ---
async def run_osint_scan(targets, username, max_concurrent, timeout_sec, progress_bar, status_text):
    # TCPConnector limitiert die parallelen Verbindungen, um IP-Bans zu vermeiden
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_platform(session, name, cat, url, username, timeout_sec)
            for name, cat, url in targets
        ]
        
        results = []
        total = len(tasks)
        completed = 0
        
        # as_completed aktualisiert den Balken, sobald *irgendeine* Plattform fertig ist
        for f in asyncio.as_completed(tasks):
            res = await f
            results.append(res)
            completed += 1
            progress_bar.progress(completed / total)
            status_text.text(f"Geprüft: {completed}/{total} Target-Webseiten...")
            
        return results

# --- HELPER: CSV EXPORT ---
def generate_csv(results):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Plattform", "Kategorie", "Status", "URL"])
    for r in results:
        writer.writerow([r["name"], r["category"], r["status"], r["url"]])
    return output.getvalue()

# --- INITIALISIERUNG DES SESSION STATES ---
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = None
if "scanned_user" not in st.session_state:
    st.session_state["scanned_user"] = ""

# --- SIDEBAR EINSTELLUNGEN ---
st.sidebar.title("⚙️ Engine Konfiguration")
selected_categories = st.sidebar.multiselect("Kategorien auswählen:", options=list(PLATFORMS_DB.keys()), default=list(PLATFORMS_DB.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Performance Settings")
max_threads = st.sidebar.slider("Parallel Verbindungen (Speed/Stealth)", min_value=5, max_value=50, value=20)
request_timeout = st.sidebar.slider("Timeout pro Anfrage (Sekunden)", min_value=2, max_value=15, value=5)

active_targets = []
for cat in selected_categories:
    for name, url in PLATFORMS_DB[cat].items():
        active_targets.append((name, cat, url))

st.sidebar.info(f"Aktivierte Targets: **{len(active_targets)}** Plattformen")

# --- MAIN UI ---
st.title("🛡️ Stealth OSINT Engine v3.0 (Async)")
st.markdown("Hochleistungs-Aufklärung mit asynchronem I/O und Stealth-Rotation.")

col_input, col_button = st.columns([3, 1])
with col_input:
    username_input = st.text_input("Ziel-Benutzername eingeben:", value=st.session_state["scanned_user"], placeholder="z.B. Alex123")
with col_button:
    st.markdown("<br>", unsafe_allow_html=True)
    start_scan = st.button("🔍 Scan Starten")

# --- SCAN LOGIK (ASYNC AUFRUF) ---
if start_scan:
    if not username_input.strip():
        st.warning("Bitte gib einen gültigen Benutzernamen ein.")
    elif not active_targets:
        st.error("Bitte wähle mindestens eine Kategorie in der Sidebar aus!")
    else:
        st.session_state["scanned_user"] = username_input
        st.info(f"Starte asynchronen High-Speed Scan für **{username_input}**...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Asyncio Loop starten
        results = asyncio.run(run_osint_scan(active_targets, username_input, max_threads, request_timeout, progress_bar, status_text))

        progress_bar.empty()
        status_text.empty()
        st.session_state["scan_results"] = results
        st.success("Scan erfolgreich abgeschlossen!")

# --- ERGEBNIS-ANZEIGE ---
if st.session_state["scan_results"]:
    results = st.session_state["scan_results"]
    
    found_list = [r for r in results if r["status"] == "FOUND"]
    blocked_list = [r for r in results if r["status"] == "BLOCKED"]
    not_found_list = [r for r in results if r["status"] == "NOT_FOUND"]
    error_list = [r for r in results if r["status"] in ["ERROR", "TIMEOUT"]]

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Gefunden", len(found_list))
    m2.metric("⚠️ Geblockt / Captcha", len(blocked_list))
    m3.metric("🚫 Nicht vorhanden", len(not_found_list))
    m4.metric("❌ Fehler / Timeout", len(error_list))
    
    tab_found, tab_blocked, tab_export = st.tabs([
        f"🎯 Gefunden ({len(found_list)})", 
        f"⚠️ Geblockt/Schutzfilter ({len(blocked_list)})", 
        "💾 Export & Report"
    ])
    
    with tab_found:
        if found_list:
            for item in found_list:
                st.markdown(f"- **[{item['category']}] {item['name']}**: [{item['url']}]({item['url']})")
        else:
            st.write("Keine aktiven Profile gefunden.")
            
    with tab_blocked:
        if blocked_list:
            for item in blocked_list:
                code_info = f" (Status {item.get('code')})" if 'code' in item else ""
                st.markdown(f"- **{item['name']}**{code_info}: [{item['url']}]({item['url']})")
        else:
            st.write("Keine Blockaden festgestellt.")

    with tab_export:
        col_csv, col_json = st.columns(2)
        
        csv_data = generate_csv(results)
        col_csv.download_button(
            label="📄 Als CSV herunterladen",
            data=csv_data,
            file_name=f"osint_{st.session_state['scanned_user']}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        json_data = json.dumps({"target": st.session_state["scanned_user"], "results": results}, indent=2, ensure_ascii=False)
        col_json.download_button(
            label="🌐 Als JSON herunterladen",
            data=json_data,
            file_name=f"osint_{st.session_state['scanned_user']}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
