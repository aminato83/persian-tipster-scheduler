import os, json, time, requests
from datetime import datetime, timezone

COMPOSIO_API_KEY = os.environ["COMPOSIO_API_KEY"]
WINDOW_SEC = 900

SCHEDULE = [
    {"id": "18100412321277949", "ts": 1780763400, "name": "visa_drama - 6 giu 18:30"},
    {"id": "18100412384277949", "ts": 1780936200, "name": "taremi_analysis - 8 giu 18:30"},
    {"id": "18100412375277949", "ts": 1781109000, "name": "group_g - 10 giu 18:30"},
    {"id": "18100412378277949", "ts": 1781281800, "name": "under_picks - 12 giu 18:30"},
    {"id": "18100412381277949", "ts": 1781368200, "name": "iran_nz_deep - 13 giu 18:30"},
    {"id": "18100412429277949", "ts": 1781506800, "name": "matchday_iran_nz - 15 giu 09:00"},
    {"id": "18100412432277949", "ts": 1781800200, "name": "belgium_intel - 18 giu 18:30"},
    {"id": "18100412438277949", "ts": 1781938800, "name": "matchday_bel_iran - 20 giu 09:00"},
    {"id": "18100412435277949", "ts": 1782318600, "name": "egypt_intel - 24 giu 18:30"},
    {"id": "18100412477277949", "ts": 1782370800, "name": "matchday_egy_iran - 25 giu 09:00"},
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

def publish_via_composio(container_id):
    url = "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute"
    headers = {"x-api-key": COMPOSIO_API_KEY, "Content-Type": "application/json"}
    body = {
        "input": {"creation_id": container_id, "ig_user_id": "me", "max_wait_seconds": 60},
        "connectedAccountId": "instagram_mease-bitter"
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    return r.json()

def main():
    now = int(time.time())
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Checking schedule...")
    published = load_published()
    for post in SCHEDULE:
        pid = post["id"]
        diff = now - post["ts"]
        if 0 <= diff <= WINDOW_SEC and pid not in published:
            print(f"  Publishing: {post['name']}")
            result = publish_via_composio(pid)
            success = result.get("successfull") or result.get("successful") or \
                      (isinstance(result.get("data"), dict) and result["data"].get("id"))
            if success:
                ig_id = result.get("data", {}).get("id", "ok")
                published[pid] = {"name": post["name"],
                                  "published_at": datetime.now(timezone.utc).isoformat(),
                                  "instagram_post_id": ig_id}
                save_published(published)
                print(f"  Published! Instagram ID: {ig_id}")
            else:
                print(f"  Error: {result}")
        elif diff < 0:
            h, m = abs(diff)//3600, (abs(diff)%3600)//60
            print(f"  Waiting: {post['name']} in {h}h {m}m")
        elif pid in published:
            print(f"  Done: {post['name']}")

if __name__ == "__main__":
    main()
