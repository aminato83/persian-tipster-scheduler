"""
Persian Tipster — Stories System v2
Upload immagini via GitHub Releases (come i video Reels).
"""
import os, json, requests, base64, time
from datetime import datetime, timezone, timedelta

COMPOSIO_KEY   = os.environ["COMPOSIO_API_KEY"]
OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
STORY_TYPE     = os.environ.get("STORY_TYPE","morning")
GH_TOKEN       = os.environ.get("GITHUB_TOKEN","")
GH_REPO        = os.environ.get("GITHUB_REPOSITORY","")

IG_ACCOUNT  = "instagram_mease-bitter"
NOTIFY_USER = 899950945
TG_BASE     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ── Generate image (LOW = $0.011) ─────────────────────────────
def gen_image(prompt):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model":"gpt-image-1","prompt":prompt,
              "size":"1024x1024","quality":"low","output_format":"jpeg"},
        timeout=60)
    d = r.json()
    if d.get("data"):
        return base64.b64decode(d["data"][0]["b64_json"])
    print(f"  Image error: {d.get('error','?')}")
    return None

# ── Upload to GitHub Releases → get public URL ────────────────
def upload_to_github(img_bytes, filename):
    if not GH_TOKEN or not GH_REPO:
        print("  No GitHub token/repo")
        return None

    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get or create release
    rel_url = f"https://api.github.com/repos/{GH_REPO}/releases/tags/media-assets"
    r = requests.get(rel_url, headers=headers, timeout=10)

    if r.status_code == 404:
        r2 = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/releases",
            headers=headers,
            json={"tag_name":"media-assets","name":"Media Assets",
                  "body":"Auto-uploaded media","draft":False,"prerelease":True},
            timeout=10)
        release = r2.json()
    else:
        release = r.json()

    release_id = release.get("id")
    if not release_id:
        print(f"  Release error: {release}")
        return None

    # Delete existing asset with same name
    assets = requests.get(
        f"https://api.github.com/repos/{GH_REPO}/releases/{release_id}/assets",
        headers=headers, timeout=10).json()
    for asset in (assets if isinstance(assets, list) else []):
        if asset.get("name") == filename:
            requests.delete(
                f"https://api.github.com/repos/{GH_REPO}/releases/assets/{asset['id']}",
                headers=headers, timeout=10)

    # Upload
    path = f"/tmp/{filename}"
    open(path,"wb").write(img_bytes)

    upload_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{release_id}/assets?name={filename}"
    with open(path,"rb") as f:
        up = requests.post(upload_url,
            headers={**headers, "Content-Type":"image/jpeg"},
            data=f, timeout=60)

    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        url = f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
        print(f"  ✅ Uploaded to GitHub: {url[-50:]}")
        return url

    print(f"  Upload error: {up.status_code} {up.text[:100]}")
    return None

# ── Create & publish Instagram Story via image_url ────────────
def publish_story(image_url):
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}

    # Create container using image_url (no file upload needed)
    r1 = requests.post(
        "https://backend.composio.dev/api/v3/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=headers,
        json={"input": {"ig_user_id":"me",
                        "media_type":"STORIES",
                        "image_url": image_url},
              "connectedAccountId": IG_ACCOUNT},
        timeout=30)
    d1 = r1.json()
    cid = d1.get("data",{}).get("id")
    if not cid:
        print(f"  Container error: {d1}")
        return None

    print(f"  Container: {cid} — waiting 20s...")
    time.sleep(20)

    # Publish
    r2 = requests.post(
        "https://backend.composio.dev/api/v3/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","creation_id":cid,"max_wait_seconds":60},
              "connectedAccountId": IG_ACCOUNT},
        timeout=90)
    d2 = r2.json()
    return d2.get("data",{}).get("id")

# ── Check matches today ───────────────────────────────────────
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

# ── Story configs ─────────────────────────────────────────────
def get_story_config():
    if STORY_TYPE == "morning":
        prompt = """Vertical 9:16 dark sports betting Instagram Story image.
Black background with deep red-orange glow from bottom corners.
Center: large gold emoji style phone icon.
Large bold gold text: PICKS ARE LIVE
White text below: Free daily Iranian sports analysis on Telegram
Small text: Football · Futsal · Volleyball · Basketball · Handball
Bottom: @persiantipster · link in bio
Swipe up arrow. Dark cinematic luxury sports style. No people."""
        return prompt, "morning"

    elif STORY_TYPE == "matchday":
        match = get_matches_today()
        match_text = f"{match['home']} vs {match['away']}" if match else "BIG MATCH TODAY"
        league = match["league"] if match else "Iranian Football"
        prompt = f"""Vertical 9:16 dark sports betting Instagram Story.
Black background with dramatic orange-red fire glow from bottom.
Bold large gold text: MATCH DAY ⚽
White center text: {match_text.upper()}
Gold subtitle: {league}
White text: Full analysis on Telegram · link in bio
Fire particles. Dramatic atmosphere. @persiantipster bottom. No people."""
        return prompt, "matchday"

    elif STORY_TYPE == "win":
        prompt = """Vertical 9:16 dark sports betting Instagram Story.
Black background with gold and green celebration.
Confetti particles. Gold stars exploding.
Huge bold gold text: WE WON ✅
White text: Another verified win documented on Blogabet
Small text: +31% yield · 756 picks · All verified
Bottom: @persiantipster · persiantipster.blogabet.com
Celebration energy. Dark luxury aesthetic. No people."""
        return prompt, "win"

    else:
        prompt = """Vertical 9:16 dark sports betting Instagram Story.
Black background with red glow. Persian Tipster badge in gold.
Bold text: FREE DAILY TIPS
White subtitle: Iranian sports picks — every single day
Three lines: ⚽ Football  🏐 Volleyball  🤾 Futsal
CTA: Join free on Telegram · @persiantipster · link in bio
Clean dark professional. No people."""
        return prompt, "cta"

# ── Notify Telegram ───────────────────────────────────────────
def notify(msg):
    if TELEGRAM_TOKEN:
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":NOTIFY_USER,"text":msg,"disable_notification":True},
            timeout=10)

# ── Main ──────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Stories v2 — type: {STORY_TYPE}")

    prompt, stype = get_story_config()

    print("  Generating image...")
    img = gen_image(prompt)
    if not img:
        print("  ❌ Image generation failed"); return

    filename = f"story_{stype}_{int(time.time())}.jpg"
    print(f"  Uploading to GitHub Releases ({filename})...")
    image_url = upload_to_github(img, filename)
    if not image_url:
        print("  ❌ Upload failed"); return

    print("  Publishing Story to Instagram...")
    post_id = publish_story(image_url)

    if post_id:
        print(f"  ✅ Story published! ID: {post_id}")
        notify(f"📸 STORY PUBBLICATA\nTipo: {STORY_TYPE}\nID: {post_id}")
    else:
        print("  ❌ Publishing failed")

if __name__ == "__main__":
    main()
