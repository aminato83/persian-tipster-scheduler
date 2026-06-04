"""
Persian Tipster — Stories System
Pubblica automaticamente:
- Story mattutina ogni giorno alle 08:30 CET
- Story match day quando c'è una partita oggi
- Story win quando si pubblica un win post
"""
import os, json, requests, base64, time
from datetime import datetime, timezone, timedelta

COMPOSIO_KEY   = os.environ["COMPOSIO_API_KEY"]
OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
STORY_TYPE     = os.environ.get("STORY_TYPE","morning")  # morning / matchday / win

IG_ACCOUNT  = "instagram_mease-bitter"
NOTIFY_USER = 899950945
TG_BASE     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ── Image generation (LOW = $0.011) ──────────────────────────
def gen_story_image(prompt):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model":"gpt-image-1","prompt":prompt,
              "size":"1024x1024","quality":"low","output_format":"jpeg"},
        timeout=60)
    d = r.json()
    if d.get("data"):
        return base64.b64decode(d["data"][0]["b64_json"])
    print(f"  Image error: {d.get('error','unknown')}")
    return None

# ── Upload to Composio ────────────────────────────────────────
def upload_image(img_bytes, fname):
    path = f"/tmp/{fname}"
    open(path,"wb").write(img_bytes)
    r = requests.post(
        "https://backend.composio.dev/api/v3/files",
        headers={"x-api-key": COMPOSIO_KEY},
        files={"file":(fname, open(path,"rb"), "image/jpeg")},
        timeout=30)
    if r.status_code in [200,201]:
        d = r.json()
        return d.get("s3key") or d.get("key")
    return None

# ── Create and publish Instagram Story ───────────────────────
def publish_story(s3key):
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}

    # Create container
    r1 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=headers,
        json={"input": {"ig_user_id":"me",
                        "media_type":"STORIES",
                        "image_file":{"mimetype":"image/jpeg",
                                      "name":"story.jpg","s3key":s3key}},
              "connectedAccountId": IG_ACCOUNT},
        timeout=30)
    d1 = r1.json()
    cid = d1.get("data",{}).get("id")
    if not cid:
        print(f"  Container error: {d1}")
        return None

    print(f"  Container: {cid} — waiting 15s...")
    time.sleep(15)

    # Publish
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","creation_id":cid,"max_wait_seconds":60},
              "connectedAccountId": IG_ACCOUNT},
        timeout=90)
    d2 = r2.json()
    return d2.get("data",{}).get("id")

# ── Check for matches today ───────────────────────────────────
def get_matches_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    matches = []
    
    # Check Azadegan League (SportDB ID 4946) and Iran national (ID 134511)
    for team_id in [4946, 134511]:
        try:
            r = requests.get(
                f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}",
                headers={"User-Agent":"PersianTipster/1.0"}, timeout=8)
            events = r.json().get("events",[]) or []
            for e in events:
                if e.get("dateEvent","") == today:
                    matches.append({
                        "home": e.get("strHomeTeam",""),
                        "away": e.get("strAwayTeam",""),
                        "time": e.get("strTime",""),
                        "league": e.get("strLeague","")
                    })
        except:
            pass
    return matches

# ── Story prompts ─────────────────────────────────────────────
def get_story_config():
    stype = STORY_TYPE
    now = datetime.now(timezone(timedelta(hours=2)))

    if stype == "morning":
        prompt = """Vertical 9:16 dark sports betting Instagram Story.
Black background with deep red-orange atmospheric glow from bottom.
Center: smartphone icon in gold.
Bold gold large text: PICKS ARE LIVE
White text below: Free daily analysis on Telegram
Small text: Iranian Football · Futsal · Volleyball · Basketball · Handball
Bottom gold text: @persiantipster · link in bio
Swipe up arrow at bottom. Dark cinematic style. No people."""

        caption = "📲 Daily picks are live on Telegram\n\n🆓 Free channel → link in bio\n\n#persiantipster #bettingtips #iranianfootball"
        return prompt, caption

    elif stype == "matchday":
        matches = get_matches_today()
        if matches:
            m = matches[0]
            match_text = f"{m['home']} vs {m['away']}"
            league_text = m.get("league","Iranian Football")
        else:
            match_text = "BIG MATCH TODAY"
            league_text = "Iranian Football"

        prompt = f"""Vertical 9:16 dark sports betting Instagram Story.
Black background with dramatic orange-red fire glow from bottom center.
Bold large gold text at top: MATCH DAY
Center white text: {match_text.upper()}
Gold text below: {league_text}
White text: Full analysis on Telegram
Fire particles rising from bottom. Dramatic atmosphere.
Bottom: @persiantipster · link in bio
Dark cinematic sports broadcast style. No people."""

        caption = f"⚽ MATCH DAY\n\n{match_text}\n{league_text}\n\nFull analysis on Telegram before kick-off.\n📲 link in bio\n\n#persiantipster #matchday #iranianfootball"
        return prompt, caption

    elif stype == "win":
        prompt = """Vertical 9:16 dark sports betting Instagram Story.
Black background with bright gold and green celebration atmosphere.
Confetti particles falling. Gold stars.
Bold large gold text: WE WON ✅
White text below: Another verified win
Small text: +31% yield · 756 documented picks
Celebration energy. Dark luxury sports aesthetic.
Bottom: @persiantipster · persiantipster.blogabet.com
No people."""

        caption = "✅ WE WON\n\nAnother verified pick. Another documented win.\n\n📊 Full record → persiantipster.blogabet.com\n📲 Free channel → link in bio\n\n#win #persiantipster #verified #bettingtips"
        return prompt, caption

    else:
        # Default: subscribe CTA
        prompt = """Vertical 9:16 dark sports betting Instagram Story.
Black background with subtle red glow.
Persian Tipster logo badge in gold.
Bold text: FREE DAILY TIPS
White subtitle: Iranian sports picks every day
Three bullet points: Football · Futsal · Volleyball & more
CTA: Join free on Telegram · link in bio
Bottom: @persiantipster
Clean dark professional style. No people."""

        caption = "📊 Free daily Iranian sports tips\n\n⚽ Football\n🏐 Volleyball\n🤾 Futsal & more\n\n📲 Join free → link in bio\n\n#persiantipster #freepicks #iranianfootball"
        return prompt, caption

# ── Notify Telegram ───────────────────────────────────────────
def notify(msg):
    if TELEGRAM_TOKEN:
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":NOTIFY_USER,"text":msg,"disable_notification":True},
            timeout=10)

# ── Main ──────────────────────────────────────────────────────
def main():
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"[{now_str}] Stories — type: {STORY_TYPE}")

    prompt, caption = get_story_config()

    print("  Generating story image...")
    img = gen_story_image(prompt)
    if not img:
        print("  ❌ Image generation failed")
        return

    print("  Uploading...")
    fname = f"story_{STORY_TYPE}_{int(time.time())}.jpg"
    s3key = upload_image(img, fname)
    if not s3key:
        print("  ❌ Upload failed")
        return

    print("  Publishing story...")
    post_id = publish_story(s3key)

    if post_id:
        print(f"  ✅ Story published! ID: {post_id}")
        notify(f"📸 STORY PUBBLICATA\nTipo: {STORY_TYPE}\nID: {post_id}")
    else:
        print("  ❌ Publishing failed")

if __name__ == "__main__":
    main()
