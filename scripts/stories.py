"""
Persian Tipster — Stories System v3
Chiama Instagram Graph API direttamente — zero dipendenza da Composio.
"""
import os, json, requests, base64, time
from datetime import datetime, timezone, timedelta

OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
STORY_TYPE     = os.environ.get("STORY_TYPE","morning")
GH_TOKEN       = os.environ.get("GITHUB_TOKEN","")
GH_REPO        = os.environ.get("GITHUB_REPOSITORY","")
IG_TOKEN       = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID     = os.environ.get("IG_USER_ID","36000867572895127")

NOTIFY_USER = 899950945
TG_BASE     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
IG_BASE     = "https://graph.facebook.com/v21.0"

# ── Generate image (LOW = $0.011) ─────────────────────────────
def gen_image(prompt):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model":"gpt-image-1","prompt":prompt,
              "size":"1024x1536","quality":"low","output_format":"jpeg"},
        timeout=60)
    d = r.json()
    if d.get("data"):
        return base64.b64decode(d["data"][0]["b64_json"])
    print(f"  Image error: {d.get('error','?')}")
    return None

# ── Upload to GitHub Releases ─────────────────────────────────
def upload_to_github(img_bytes, filename):
    if not GH_TOKEN or not GH_REPO:
        print("  ❌ No GitHub token/repo")
        return None
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    # Get or create release
    r = requests.get(
        f"https://api.github.com/repos/{GH_REPO}/releases/tags/media-assets",
        headers=headers, timeout=10)
    if r.status_code == 404:
        r2 = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/releases",
            headers=headers,
            json={"tag_name":"media-assets","name":"Media Assets",
                  "draft":False,"prerelease":True},
            timeout=10)
        release = r2.json()
    else:
        release = r.json()
    release_id = release.get("id")
    if not release_id:
        print(f"  ❌ Release error: {release}")
        return None
    # Delete existing asset
    assets = requests.get(
        f"https://api.github.com/repos/{GH_REPO}/releases/{release_id}/assets",
        headers=headers, timeout=10).json()
    for a in (assets if isinstance(assets,list) else []):
        if a.get("name") == filename:
            requests.delete(
                f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",
                headers=headers, timeout=10)
    # Upload
    path = f"/tmp/{filename}"
    open(path,"wb").write(img_bytes)
    up_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{release_id}/assets?name={filename}"
    with open(path,"rb") as f:
        up = requests.post(up_url,
            headers={**headers,"Content-Type":"image/jpeg"},
            data=f, timeout=60)
    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        url = f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
        print(f"  ✅ GitHub URL ready")
        return url
    print(f"  ❌ Upload error: {up.status_code}")
    return None

# ── Publish Story via Instagram Graph API directly ────────────
def publish_story(image_url):
    # Step 1: Create container
    r1 = requests.post(
        f"{IG_BASE}/{IG_USER_ID}/media",
        params={
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": IG_TOKEN
        },
        timeout=30)
    print(f"  Container status: {r1.status_code}")
    if r1.status_code != 200:
        print(f"  Container error: {r1.text[:200]}")
        return None
    cid = r1.json().get("id")
    if not cid:
        print(f"  No container ID: {r1.json()}")
        return None
    print(f"  Container: {cid} — waiting 20s...")
    time.sleep(20)
    # Step 2: Publish
    r2 = requests.post(
        f"{IG_BASE}/{IG_USER_ID}/media_publish",
        params={"creation_id": cid, "access_token": IG_TOKEN},
        timeout=30)
    print(f"  Publish status: {r2.status_code}")
    if r2.status_code != 200:
        print(f"  Publish error: {r2.text[:200]}")
        return None
    return r2.json().get("id")

# ── Story configs ─────────────────────────────────────────────
def get_story_config():
    if STORY_TYPE == "morning":
        return ("""Vertical 9:16 dark sports betting Instagram Story.
Black background, deep red-orange glow from bottom corners.
Large bold gold text center: PICKS ARE LIVE
White text: Free daily Iranian sports analysis on Telegram
Small text: Football · Futsal · Volleyball · Basketball · Handball
Bottom: @persiantipster · link in bio · swipe up arrow.
Dark cinematic luxury sports style. No people.""", "morning")

    elif STORY_TYPE == "matchday":
        match = get_matches_today()
        mt = f"{match['home']} vs {match['away']}" if match else "BIG MATCH TODAY"
        league = match["league"] if match else "Iranian Football"
        return (f"""Vertical 9:16 dark sports betting Instagram Story.
Black background, dramatic orange-red fire glow from bottom.
Bold large gold text: MATCH DAY ⚽
White text: {mt.upper()}
Gold subtitle: {league}
Text: Full analysis on Telegram · link in bio
Fire particles. @persiantipster bottom. No people.""", "matchday")

    elif STORY_TYPE == "win":
        return ("""Vertical 9:16 dark sports betting Instagram Story.
Black background, gold and green celebration.
Confetti, gold stars. Huge bold gold text: WE WON ✅
White: Another verified win on Blogabet
Small: +31% yield · 756 picks · All verified
Bottom: @persiantipster · persiantipster.blogabet.com
No people.""", "win")

    else:
        return ("""Vertical 9:16 dark sports betting Story.
Black background, red glow. Gold badge: PERSIAN TIPSTER.
Bold text: FREE DAILY TIPS
White: Iranian sports picks every day
Lines: ⚽ Football  🏐 Volleyball  🤾 Futsal & more
CTA: Join free on Telegram · link in bio. No people.""", "cta")

def get_matches_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for team_id in [4946, 134511]:
        try:
            r = requests.get(
                f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}",
                headers={"User-Agent":"PersianTipster/1.0"}, timeout=8)
            for e in (r.json().get("events",[]) or []):
                if e.get("dateEvent","") == today:
                    return {"home":e.get("strHomeTeam",""),
                            "away":e.get("strAwayTeam",""),
                            "league":e.get("strLeague","")}
        except: pass
    return None

def notify(msg):
    if TELEGRAM_TOKEN:
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":NOTIFY_USER,"text":msg,"disable_notification":True},
            timeout=10)

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Stories v3 — type: {STORY_TYPE}")
    prompt, stype = get_story_config()
    print("  Generating image...")
    img = gen_image(prompt)
    if not img:
        print("  ❌ Image generation failed"); return
    filename = f"story_{stype}_{int(time.time())}.jpg"
    print(f"  Uploading to GitHub ({filename})...")
    image_url = upload_to_github(img, filename)
    if not image_url:
        print("  ❌ Upload failed"); return
    print("  Publishing Story...")
    post_id = publish_story(image_url)
    if post_id:
        print(f"  ✅ Story published! ID: {post_id}")
        notify(f"📸 STORY PUBBLICATA\nTipo: {STORY_TYPE}\nID: {post_id}")
    else:
        print("  ❌ Publishing failed")

if __name__ == "__main__":
    main()
