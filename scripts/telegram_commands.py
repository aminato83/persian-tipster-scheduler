"""
Persian Tipster — Telegram Command Handler v2
Comandi:
  /story morning   → story mattutina
  /story win       → story vittoria
  /story matchday  → story giorno partita
"""
import os, json, requests, time, base64
from datetime import datetime, timezone

TG_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_KEY    = os.environ["OPENAI_API_KEY"]
COMPOSIO_KEY  = os.environ["COMPOSIO_API_KEY"]
GH_TOKEN      = os.environ.get("GITHUB_TOKEN","")
GH_REPO       = os.environ.get("GITHUB_REPOSITORY","")

AUTHORIZED_USER = 899950945
TG_BASE   = f"https://api.telegram.org/bot{TG_TOKEN}"
IG_ACCOUNT = "instagram_mease-bitter"
OFFSET_FILE = "telegram_offset.json"

PROMPTS = {
    "morning":  "Vertical portrait dark sports betting Instagram Story. Black background deep red-orange glow. Bold gold text: PICKS ARE LIVE. White: Free daily Iranian sports analysis on Telegram. Small: Football Futsal Volleyball Basketball Handball. Bottom: @persiantipster link in bio. Dark cinematic luxury sports style. No people.",
    "win":      "Vertical portrait dark sports betting Instagram Story. Black gold green celebration. Confetti. Huge bold gold text: WE WON. White: Another verified win on Blogabet. Small: +31% yield 756 picks All verified. Bottom: @persiantipster. No people.",
    "matchday": "Vertical portrait dark sports betting Instagram Story. Black background orange-red fire. Bold gold: MATCH DAY. White: BIG MATCH TODAY. Gold: Iranian Football. Text: Full analysis on Telegram. Fire. @persiantipster. No people.",
}

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try: return json.load(open(OFFSET_FILE)).get("offset", 0)
        except: return 0
    return 0

def save_offset(offset):
    json.dump({"offset": offset}, open(OFFSET_FILE,"w"))

def tg_send(chat_id, text):
    try:
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":chat_id,"text":text,"disable_notification":True}, timeout=10)
    except: pass

def gen_image(story_type):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization":f"Bearer {OPENAI_KEY}"},
        json={"model":"gpt-image-1","prompt":PROMPTS.get(story_type,PROMPTS["morning"]),
              "size":"1024x1536","quality":"low","output_format":"jpeg"},
        timeout=60)
    d = r.json()
    if d.get("data"):
        img = base64.b64decode(d["data"][0]["b64_json"])
        path = f"/tmp/story_{story_type}_{int(time.time())}.jpg"
        open(path,"wb").write(img)
        return path
    print(f"  Image error: {d.get('error','?')}")
    return None

def upload_to_github(path, filename):
    if not GH_TOKEN or not GH_REPO: return None
    headers = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    r = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/tags/media-assets",headers=headers,timeout=10)
    if r.status_code == 404:
        r2 = requests.post(f"https://api.github.com/repos/{GH_REPO}/releases",headers=headers,
            json={"tag_name":"media-assets","name":"Media Assets","draft":False,"prerelease":True},timeout=10)
        release = r2.json()
    else:
        release = r.json()
    rid = release.get("id")
    if not rid: return None
    assets = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/{rid}/assets",headers=headers,timeout=10).json()
    for a in (assets if isinstance(assets,list) else []):
        if a.get("name") == filename:
            requests.delete(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",headers=headers,timeout=10)
    up_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{rid}/assets?name={filename}"
    with open(path,"rb") as f:
        up = requests.post(up_url,headers={**headers,"Content-Type":"image/jpeg"},data=f,timeout=60)
    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        return f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
    return None

def publish_story_composio(image_url):
    """Publish story via Composio API v2 using image_url"""
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}

    # Create container
    r1 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","image_url":image_url,"media_type":"STORIES"},
              "connectedAccountId":IG_ACCOUNT},
        timeout=30)

    d1 = r1.json()
    # Check for v2 retired error
    if d1.get("error",{}).get("status") == 410:
        print(f"  v2 retired, story queued for manual publish")
        return None

    cid = d1.get("data",{}).get("id")
    if not cid:
        print(f"  Container error: {d1}")
        return None

    print(f"  Container: {cid} — waiting 20s...")
    time.sleep(20)

    # Publish
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","creation_id":cid,"max_wait_seconds":60},
              "connectedAccountId":IG_ACCOUNT},
        timeout=90)
    d2 = r2.json()
    return d2.get("data",{}).get("id")

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Telegram Commands v2")

    offset = load_offset()
    print(f"  Current offset: {offset}")

    r = requests.get(f"{TG_BASE}/getUpdates",
        params={"offset":offset,"timeout":5,"limit":20}, timeout=15)
    updates = r.json().get("result",[])
    print(f"  Updates: {len(updates)}")

    new_offset = offset
    processed_any = False

    for update in updates:
        uid = update.get("update_id",0)
        if uid >= new_offset: new_offset = uid + 1

        msg = update.get("message",{})
        user_id = msg.get("from",{}).get("id")
        text = (msg.get("text") or "").strip()
        chat_id = msg.get("chat",{}).get("id")

        print(f"  Update {uid}: user={user_id} text='{text[:30]}'")

        if user_id != AUTHORIZED_USER:
            continue

        # Accept /story morning OR /story_morning OR /storymorning
        story_type = None
        text_lower = text.lower().replace("_","").replace(" ","")
        if text_lower.startswith("/storymorning") or text_lower == "/storymorning":
            story_type = "morning"
        elif text_lower.startswith("/storywin"):
            story_type = "win"
        elif text_lower.startswith("/storymatchday"):
            story_type = "matchday"
        elif text_lower.startswith("/story"):
            # /story morning, /story win, etc.
            parts = text.lower().split()
            if len(parts) > 1:
                t = parts[1].strip()
                if t in ["morning","win","matchday"]:
                    story_type = t
                else:
                    story_type = "morning"
            else:
                story_type = "morning"

        if not story_type:
            continue

        print(f"  → /story {story_type} command!")
        processed_any = True
        tg_send(chat_id, f"⏳ Generando story {story_type}... (30 sec)")

        # 1. Generate image
        img_path = gen_image(story_type)
        if not img_path:
            tg_send(chat_id, "❌ Errore generazione immagine")
            continue

        # 2. Upload to GitHub Releases
        filename = f"story_{story_type}_{int(time.time())}.jpg"
        image_url = upload_to_github(img_path, filename)
        if not image_url:
            tg_send(chat_id, "❌ Errore upload")
            continue

        print(f"  ✅ Image: {image_url[-50:]}")

        # 3. Publish via Composio
        post_id = publish_story_composio(image_url)

        if post_id:
            print(f"  ✅ Published! ID: {post_id}")
            tg_send(chat_id, f"✅ Story {story_type.upper()} pubblicata su Instagram!")
        else:
            print(f"  ❌ Publish failed")
            tg_send(chat_id, f"⚠️ Errore pubblicazione — riprova")

        time.sleep(2)

    # Always save new offset
    if new_offset > offset:
        save_offset(new_offset)
        print(f"  Saved offset: {new_offset}")

if __name__ == "__main__":
    main()
