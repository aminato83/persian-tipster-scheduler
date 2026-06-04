"""
Persian Tipster — Instagram Auto-Scheduler
Gira ogni 15 minuti via GitHub Actions.
Pubblica i post agli orari esatti senza intervento umano.
"""
import os, json, time, requests
from datetime import datetime, timezone

IG_TOKEN   = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]
WINDOW_SEC = 900   # pubblica se siamo entro 15 minuti dall'orario target

# ── TUTTI I POST PROGRAMMATI ─────────────────────────────────────────────────
SCHEDULE = [
    # World Cup 2026 — Iran
    {"id": "18100412321277949", "ts": 1780763400, "name": "visa_drama          ─ 6 giu 18:30"},
    {"id": "18100412384277949", "ts": 1780936200, "name": "taremi_analysis     ─ 8 giu 18:30"},
    {"id": "18100412375277949", "ts": 1781109000, "name": "group_g             ─ 10 giu 18:30"},
    {"id": "18100412378277949", "ts": 1781281800, "name": "under_picks         ─ 12 giu 18:30"},
    {"id": "18100412381277949", "ts": 1781368200, "name": "iran_nz_deep        ─ 13 giu 18:30"},
    {"id": "18100412429277949", "ts": 1781506800, "name": "matchday_iran_nz    ─ 15 giu 09:00"},
    {"id": "18100412432277949", "ts": 1781800200, "name": "belgium_intel       ─ 18 giu 18:30"},
    {"id": "18100412438277949", "ts": 1781938800, "name": "matchday_bel_iran   ─ 20 giu 09:00"},
    {"id": "18100412435277949", "ts": 1782318600, "name": "egypt_intel         ─ 24 giu 18:30"},
    {"id": "18100412477277949", "ts": 1782370800, "name": "matchday_egy_iran   ─ 25 giu 09:00"},
]

PUBLISHED_FILE = "published.json"

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f:
            return json.load(f)
    return {}

def save_published(data):
    with open(PUBLISHED_FILE, "w") as f:
        json.dump(data, f, indent=2)

def publish_container(container_id):
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"
    r = requests.post(url, json={
        "creation_id": container_id,
        "access_token": IG_TOKEN
    })
    return r.json()

def main():
    now = int(time.time())
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Checking schedule...")

    published = load_published()
    did_publish = False

    for post in SCHEDULE:
        pid = post["id"]
        diff = now - post["ts"]

        # In window: da 0 a +WINDOW_SEC secondi dopo l'orario target
        if 0 <= diff <= WINDOW_SEC and pid not in published:
            print(f"  → Publishing: {post['name']}")
            result = publish_container(pid)

            if result.get("id"):
                published[pid] = {
                    "name": post["name"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "instagram_post_id": result["id"]
                }
                save_published(published)
                print(f"  ✅ Published! Instagram ID: {result['id']}")
                did_publish = True
            else:
                print(f"  ❌ Error: {result}")
        elif diff < 0:
            eta_h = abs(diff) // 3600
            eta_m = (abs(diff) % 3600) // 60
            print(f"  ⏳ {post['name']}: in {eta_h}h {eta_m}m")
        elif pid in published:
            print(f"  ✅ {post['name']}: already published")

    if not did_publish:
        print("  Nothing to publish right now.")

if __name__ == "__main__":
    main()
