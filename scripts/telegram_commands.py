"""
Persian Tipster — Telegram Command Handler
Gira ogni 2 minuti su GitHub Actions.
Comandi supportati:
  /story morning   → story mattutina
  /story win       → story vittoria
  /story matchday  → story giorno partita
"""
import os, json, requests, time, base64
from datetime import datetime, timezone

TG_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_KEY    = os.environ["OPENAI_API_KEY"]
COMPOSIO_KEY  = os.environ["COMPOSIO_API_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
GH_TOKEN      = os.environ.get("GITHUB_TOKEN","")
GH_REPO       = os.environ.get("GITHUB_REPOSITORY","")

AUTHORIZED_USER = 899950945
TG_BASE = f"https://api.telegram.org/bot{TG_TOKEN}"
OFFSET_FILE = "telegram_offset.json"
IG_ACCOUNT  = "instagram_mease-bitter"

# ── State ─────────────────────────────────────────────────────
def load_offset():
    if os.path.exists(OFFSET_FILE):
        return json.load(open(OFFSET_FILE)).get("offset", 0)
    return 0

def save_offset(offset):
    json.dump({"offset": offset}, open(OFFSET_FILE, "w"))

def tg_send(chat_id, text):
    requests.post(f"{TG_BASE}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_notification": True}, timeout=10)

# ── Generate story image (LOW = $0.011) ───────────────────────
PROMPTS = {
    "morning": "Vertical 9:16 dark sports betting Instagram Story. Black background deep red-orange glow. Large bold gold text: PICKS ARE LIVE. White text: Free daily Iranian sports analysis on Telegram. Small text: Football Futsal Volleyball Basketball Handball. Bottom: @persiantipster link in bio. Dark cinematic luxury style. No people.",
    "win":     "Vertical 9:16 dark sports betting Instagram Story. Black gold green celebration. Confetti. Huge bold gold text: WE WON. White: Another verified win on Blogabet. Small: plus 31 percent yield 756 picks All verified. Bottom: @persiantipster persiantipster.blogabet.com. No people.",
    "matchday":"Vertical 9:16 dark sports betting Instagram Story. Black background orange-red fire glow. Bold gold text: MATCH DAY. White: BIG MATCH TODAY. Gold: Iranian Football. Text: Full analysis on Telegram link in bio. Fire particles. @persiantipster. No people.",
}

def gen_image(story_type):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
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

# ── Upload image to GitHub Releases ───────────────────────────
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
    # Delete existing asset with same name
    assets = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/{rid}/assets",headers=headers,timeout=10).json()
    for a in (assets if isinstance(assets,list) else []):
        if a.get("name") == filename:
            requests.delete(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",headers=headers,timeout=10)
    # Upload
    up_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{rid}/assets?name={filename}"
    with open(path,"rb") as f:
        up = requests.post(up_url,headers={**headers,"Content-Type":"image/jpeg"},data=f,timeout=60)
    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        return f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
    return None

# ── Publish story via Claude API + Composio MCP ───────────────
def publish_story_via_claude(story_type, image_url):
    """Call Claude API which uses Composio MCP to publish the story"""
    prompt = f"""Publish an Instagram Story for @persiantipster right now.

Image URL (already generated): {image_url}

Steps:
1. Call INSTAGRAM_POST_IG_USER_MEDIA with:
   - ig_user_id: "me"
   - media_type: "STORIES"  
   - image_url: "{image_url}"
2. Call INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH with the container ID
3. Reply with "✅ Story {story_type} published!" and the Instagram post ID

Do it now."""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role":"user","content":prompt}],
            "mcp_servers": [{
                "type": "url",
                "url": "https://connect.composio.dev/mcp",
                "name": "composio",
                "authorization_token": COMPOSIO_KEY
            }]
        },
        timeout=120
    )
    return r.json()

# ── Main ──────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Telegram Command Handler")

    offset = load_offset()
    r = requests.get(f"{TG_BASE}/getUpdates",
        params={"offset": offset, "timeout": 5, "limit": 20}, timeout=15)
    updates = r.json().get("result", [])
    print(f"  Updates: {len(updates)}")

    new_offset = offset
    for update in updates:
        uid = update.get("update_id", 0)
        if uid >= new_offset: new_offset = uid + 1

        msg = update.get("message", {})
        user_id = msg.get("from", {}).get("id")
        text = (msg.get("text") or "").strip()
        chat_id = msg.get("chat", {}).get("id")

        if user_id != AUTHORIZED_USER or not text.startswith("/story"):
            continue

        # Parse: /story morning | /story win | /story matchday
        parts = text.lower().split()
        story_type = parts[1] if len(parts) > 1 else "morning"
        if story_type not in ["morning","win","matchday"]:
            story_type = "morning"

        print(f"  Command: /story {story_type}")
        tg_send(chat_id, f"⏳ Generating {story_type} story (~30 sec)...")

        # 1. Generate image
        img_path = gen_image(story_type)
        if not img_path:
            tg_send(chat_id, "❌ Image generation failed")
            continue

        # 2. Upload to GitHub
        filename = f"story_{story_type}_{int(time.time())}.jpg"
        image_url = upload_to_github(img_path, filename)
        if not image_url:
            tg_send(chat_id, "❌ Upload failed")
            continue

        print(f"  Image ready: {image_url[-50:]}")

        # 3. Publish via Claude API + Composio MCP
        print("  Calling Claude API to publish story...")
        result = publish_story_via_claude(story_type, image_url)

        # Check if published
        content_text = " ".join(
            block.get("text","") for block in result.get("content",[])
            if block.get("type") == "text"
        )
        print(f"  Claude response: {content_text[:200]}")

        if "published" in content_text.lower() or "✅" in content_text:
            tg_send(chat_id, f"✅ Story {story_type.upper()} pubblicata!")
            print("  ✅ Published!")
        else:
            tg_send(chat_id, f"⚠️ Controlla Instagram — story potrebbe essere pubblicata")

    if new_offset > offset:
        save_offset(new_offset)

if __name__ == "__main__":
    main()
