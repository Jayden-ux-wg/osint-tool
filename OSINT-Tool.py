import streamlit as st
import requests
import concurrent.futures
import json
import io
import csv
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
    .stApp {
        background-color: #080808;
        color: #00ff66;
        font-family: 'Courier New', Courier, monospace;
    }
    h1, h2, h3 {
        color: #ff2a2a !important;
        font-family: 'Courier New', Courier, monospace;
        text-shadow: 0px 0px 8px rgba(255, 42, 42, 0.4);
    }
    .stTextInput input {
        background-color: #121212;
        color: #00ff66;
        border: 1px solid #ff2a2a;
        font-family: 'Courier New', Courier, monospace;
    }
    .stButton button {
        background: linear-gradient(45deg, #ff2a2a, #8b0000);
        color: white;
        font-weight: bold;
        border-radius: 4px;
        border: 1px solid #ff5555;
        font-family: 'Courier New', Courier, monospace;
        width: 100%;
        padding: 0.6rem 1rem;
    }
    .stButton button:hover {
        background: linear-gradient(45deg, #ff5555, #ff2a2a);
        color: #fff;
        border: 1px solid #00ff66;
        box-shadow: 0 0 10px rgba(0, 255, 102, 0.5);
    }
    div[data-testid="stMetricValue"] {
        color: #00ff66 !important;
        font-family: 'Courier New', Courier, monospace;
    }
    </style>
""", unsafe_allow_html=True)

# --- OSINT TARGET DATABASE (NACH KATEGORIEN STRUKTURIERT) ---
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
        "Snapchat": "https://www.snapchat.com/add/{}",
        "Mastodon": "https://mastodon.social/@{}",
        "Medium": "https://medium.com/@{}",
        "Quora": "https://www.quora.com/profile/{}",
        "Substack": "https://substack.com/@{}",
        "Tumblr": "https://{}.tumblr.com",
        "VKontakte": "https://vk.com/{}",
        "Keybase": "https://keybase.io/{}",
        "About.me": "https://about.me/{}",
        "Disqus": "https://disqus.com/by/{}",
        "Linktree": "https://linktr.ee/{}"
    },
    "Gaming & Esports": {
        "Steam": "https://steamcommunity.com/id/{}",
        "Twitch": "https://www.twitch.tv/{}",
        "Kick": "https://kick.com/{}",
        "Chess.com": "https://www.chess.com/member/{}",
        "Lichess": "https://lichess.org/@/{}",
        "Xbox": "https://account.xbox.com/en-us/profile?gamertag={}",
        "PSN Profiles": "https://psnprofiles.com/{}",
        "Fortnite Tracker": "https://fortnitetracker.com/profile/all/{}",
        "Apex Tracker": "https://apex.tracker.gg/apex/profile/origin/{}",
        "Speedrun.com": "https://www.speedrun.com/user/{}",
        "Osu!": "https://osu.ppy.sh/users/{}",
        "Nexus Mods": "https://www.nexusmods.com/users/{}",
        "CurseForge": "https://www.curseforge.com/members/{}",
        "Planet Minecraft": "https://www.planetminecraft.com/member/{}",
        "Roblox DevForum": "https://devforum.roblox.com/u/{}",
        "Itch.io": "https://{}.itch.io",
        "VRChat": "https://vrchat.com/home/user/{}",
        "TruckersMP": "https://truckersmp.com/user/{}",
        "Faceit": "https://www.faceit.com/en/players/{}"
    },
    "Developer & Tech": {
        "GitLab": "https://gitlab.com/{}",
        "Bitbucket": "https://bitbucket.org/{}",
        "Replit": "https://replit.com/@{}",
        "CodePen": "https://codepen.io/{}",
        "StackOverflow": "https://stackoverflow.com/users/{}",
        "Kaggle": "https://www.kaggle.com/{}",
        "Docker Hub": "https://hub.docker.com/u/{}",
        "Npmjs": "https://www.npmjs.com/~{}",
        "PyPI": "https://pypi.org/user/{}",
        "HackerNews": "https://news.ycombinator.com/user?id={}",
        "LeetCode": "https://leetcode.com/{}",
        "HackerRank": "https://www.hackerrank.com/{}",
        "Codecademy": "https://www.codecademy.com/profiles/{}",
        "Glitch": "https://glitch.com/@{}",
        "Vercel": "https://vercel.com/{}"
    },
    "Media & Creative": {
        "Spotify": "https://open.spotify.com/user/{}",
        "SoundCloud": "https://soundcloud.com/{}",
        "YouTube": "https://www.youtube.com/@{}",
        "Vimeo": "https://vimeo.com/{}",
        "Behance": "https://www.behance.net/{}",
        "Dribbble": "https://dribbble.com/{}",
        "DeviantArt": "https://www.deviantart.com/{}",
        "Flickr": "https://www.flickr.com/photos/{}",
        "500px": "https://500px.com/{}",
        "Bandcamp": "https://bandcamp.com/{}",
        "ArtStation": "https://www.artstation.com/{}",
        "Sketchfab": "https://sketchfab.com/{}",
        "Mixcloud": "https://www.mixcloud.com/{}",
        "Last.fm": "https://www.last.fm/user/{}"
    },
    "E-Commerce & Services": {
        "Etsy": "https://www.etsy.com/people/{}",
        "Vinted": "https://www.vinted.fr/member/{}",
        "eBay": "https://www.ebay.com/usr/{}",
        "Patreon": "https://www.patreon.com/{}",
        "Ko-fi": "https://ko-fi.com/{}",
        "BuyMeACoffee": "https://buymeacoffee.com/{}",
        "Fiverr": "https://www.fiverr.com/{}",
        "CashApp": "https://cash.app/${}"
    }
}

# --- ROBUSTE PRÜFFUNKTION MIT CODES & SOFT-404 DETEKTION ---
def check_platform(name, category, url_template, username, timeout=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Platzhalter auflösen
    target_url = url_template.format(username, username) if url_template.count('{}') > 1 else url_template.format(username)
    
    try:
        response = requests.get(target_url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code == 200:
            page_text = response.text.lower()
            not_found_indicators = [
                "not found", "does not exist", "user not found", "account not found",
                "seite nicht gefunden", "konto existiert nicht", "profil wurde nicht gefunden",
                "dieses profil ist leider nicht verfügbar", "error 404", "ungültiger benutzer",
                "page not found", "couldn't find this account"
            ]
            
            for indicator in not_found_indicators:
                if indicator in page_text:
                    return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
                    
            return {"name": name, "category": category, "url": target_url, "status": "FOUND"}
            
        elif response.status_code in [403, 429] or "cloudflare" in response.text.lower():
            return {"name": name, "category": category, "url": target_url, "status": "BLOCKED", "code": response.status_code}
        elif response.status_code == 404:
            return {"name": name, "category": category, "url": target_url, "status": "NOT_FOUND"}
        else:
            return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": response.status_code}
            
    except requests.exceptions.Timeout:
        return {"name": name, "category": category, "url": target_url, "status": "TIMEOUT"}
    except requests.exceptions.RequestException:
        return {"name": name, "category": category, "url": target_url, "status": "ERROR", "code": "Exception"}

# --- HELPER: CSV EXPORT ERZEUGEN ---
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

selected_categories = st.sidebar.multiselect(
    "Kategorien auswählen:",
    options=list(PLATFORMS_DB.keys()),
    default=list(PLATFORMS_DB.keys())
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Performance Settings")
max_threads = st.sidebar.slider("Parallel Threads (Geschwindigkeit)", min_value=4, max_value=32, value=16)
request_timeout = st.sidebar.slider("Timeout pro Anfrage (Sekunden)", min_value=2, max_value=10, value=5)

# Plattform-Anzahl berechnen
active_targets = []
for cat in selected_categories:
    for name, url in PLATFORMS_DB[cat].items():
        active_targets.append((name, cat, url))

st.sidebar.info(f"Aktivierte Targets: **{len(active_targets)}** Plattformen")

# --- MAIN UI ---
st.title("🛡️ Stealth OSINT Engine v2.0")
st.markdown("Hochleistungs-Aufklärung von Benutzerprofilen über mehrere Netzwerke hinweg.")

col_input, col_button = st.columns([3, 1])

with col_input:
    username_input = st.text_input("Ziel-Benutzername eingeben:", value=st.session_state["scanned_user"], placeholder="z.B. Alex123")

with col_button:
    st.markdown("<br>", unsafe_allow_html=True)
    start_scan = st.button("🔍 Scan Starten")

# --- SCAN LOGIK ---
if start_scan:
    if not username_input.strip():
        st.warning("Bitte gib einen gültigen Benutzernamen ein.")
    elif not active_targets:
        st.error("Bitte wähle mindestens eine Kategorie in der Sidebar aus!")
    else:
        st.session_state["scanned_user"] = username_input
        st.info(f"Starte Echtzeit-Scan für **{username_input}** auf {len(active_targets)} Plattformen...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        completed = 0
        total = len(active_targets)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [
                executor.submit(check_platform, name, cat, url, username_input, request_timeout)
                for name, cat, url in active_targets
            ]
            
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results.append(res)
                completed += 1
                progress_bar.progress(completed / total)
                status_text.text(f"Geprüft: {completed}/{total} Target-Webseiten...")

        progress_bar.empty()
        status_text.empty()
        
        st.session_state["scan_results"] = results
        st.success("Scan erfolgreich abgeschlossen!")

# --- ERGEBNIS-ANZEIGE (FALLS VORHANDEN) ---
if st.session_state["scan_results"]:
    results = st.session_state["scan_results"]
    
    found_list = [r for r in results if r["status"] == "FOUND"]
    blocked_list = [r for r in results if r["status"] == "BLOCKED"]
    not_found_list = [r for r in results if r["status"] == "NOT_FOUND"]
    error_list = [r for r in results if r["status"] in ["ERROR", "TIMEOUT"]]

    st.markdown("---")
    
    # METRIKEN DASHBOARD
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Gefunden", len(found_list))
    m2.metric("⚠️ Geblockt / Captcha", len(blocked_list))
    m3.metric("🚫 Nicht vorhanden", len(not_found_list))
    m4.metric("❌ Fehler / Timeout", len(error_list))
    
    # TABS FÜR ERGEBNISSE
    tab_found, tab_blocked, tab_export = st.tabs([
        f"🎯 Gefunden ({len(found_list)})", 
        f"⚠️ Geblockt/Schutzfilter ({len(blocked_list)})", 
        "💾 Export & Report"
    ])
    
    with tab_found:
        if found_list:
            st.markdown("### Active Profile Links")
            for item in found_list:
                st.markdown(f"- **[{item['category']}] {item['name']}**: [{item['url']}]({item['url']})")
        else:
            st.write("Keine aktiven Profile für diesen Namen gefunden.")
            
    with tab_blocked:
        if blocked_list:
            st.warning("Diese Seiten haben die Anfrage blockiert (z. B. durch Cloudflare, CAPTCHAs oder Log-In Pflicht). Ein Profil könnte hier existieren.")
            for item in blocked_list:
                code_info = f" (Status {item.get('code')})" if 'code' in item else ""
                st.markdown(f"- **{item['name']}**{code_info}: [{item['url']}]({item['url']})")
        else:
            st.write("Keine Blockaden festgestellt.")

    with tab_export:
        st.markdown("### Report Exportieren")
        col_csv, col_json = st.columns(2)
        
        # CSV Export
        csv_data = generate_csv(results)
        col_csv.download_button(
            label="📄 Als CSV herunterladen",
            data=csv_data,
            file_name=f"osint_report_{st.session_state['scanned_user']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # JSON Export
        json_data = json.dumps({
            "target": st.session_state["scanned_user"],
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "found": len(found_list),
                "blocked": len(blocked_list),
                "not_found": len(not_found_list),
                "errors": len(error_list)
            },
            "results": results
        }, indent=2, ensure_ascii=False)
        
        col_json.download_button(
            label="🌐 Als JSON herunterladen",
            data=json_data,
            file_name=f"osint_report_{st.session_state['scanned_user']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
