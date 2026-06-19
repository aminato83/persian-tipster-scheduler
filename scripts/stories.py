"""
Persian Tipster — Stories System v4
Motore: HTML/CSS + Playwright (testo perfetto) + libreria sfondi + font Teko.
Pubblica via Instagram Graph API diretta (Composio v2 retired per Stories).
"""
import os, json, requests, time, asyncio, random
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
STORY_TYPE     = os.environ.get("STORY_TYPE","morning")
GH_TOKEN       = os.environ.get("GITHUB_TOKEN","")
GH_REPO        = os.environ.get("GITHUB_REPOSITORY","")
IG_TOKEN       = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID     = os.environ.get("IG_USER_ID","36000867572895127")

NOTIFY_USER = 899950945
TG_BASE     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
IG_BASE     = "https://graph.facebook.com/v21.0"
TELEGRAM_LINK = "t.me/tipster_persian"

RAW_BASE = "https://raw.githubusercontent.com/aminato83/persian-tipster-scheduler/main/assets/backgrounds/"
BACKGROUNDS = {
    "story": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_38%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_13_06%20%284%29.png",
    ],
    "matchday": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_37%20%283%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_38_45%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_20_21%20%284%29.png",
    ],
    "win": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_40_38%20%282%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_38_44%20%282%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_38_45%20%283%29.png",
    ],
}
GOOGLE_FONTS_IMPORT = "family=Teko:wght@500;600;700&family=Inter:wght@400;600;800"
TITLE_FONT = "'Teko', sans-serif"

def get_bg(category):
    return random.choice(BACKGROUNDS.get(category, BACKGROUNDS["story"]))

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

def get_story_content():
    if STORY_TYPE == "morning":
        return {
            "category": "story",
            "label": "Daily Update",
            "title_html": "PICKS ARE<br>LIVE",
            "sub": "Free daily Iranian sports analysis",
            "link_text": TELEGRAM_LINK,
        }
    elif STORY_TYPE == "matchday":
        match = get_matches_today()
        mt = f"{match['home']} vs {match['away']}" if match else "BIG MATCH TODAY"
        league = match["league"] if match else "Iranian Football"
        return {
            "category": "matchday",
            "label": "Match Day",
            "title_html": mt.upper().replace(" VS ", "<br>VS<br>"),
            "sub": league,
            "link_text": TELEGRAM_LINK,
        }
    elif STORY_TYPE == "win":
        return {
            "category": "win",
            "label": "Verified Win",
            "title_html": "WE WON",
            "sub": "+31% yield · 756 picks · All verified",
            "link_text": TELEGRAM_LINK,
        }
    else:
        return {
            "category": "story",
            "label": "Free Daily Tips",
            "title_html": "JOIN<br>FREE",
            "sub": "Football · Volleyball · Futsal & more",
            "link_text": TELEGRAM_LINK,
        }

def build_html(content):
    bg_url = get_bg(content["category"])
    return f"""<!DOCTYPE html><html><head><style>
@import url('https://fonts.googleapis.com/css2?{GOOGLE_FONTS_IMPORT}&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1080px; height:1920px; position:relative; font-family:'Inter',sans-serif; overflow:hidden; }}
.bg {{ position:absolute; top:0; left:0; width:1080px; height:1920px; object-fit:cover; }}
.scrim {{ position:absolute; top:0; left:0; width:1080px; height:1920px;
  background: linear-gradient(to bottom, rgba(5,5,5,0.88) 0%, rgba(5,5,5,0.25) 25%, rgba(5,5,5,0.2) 60%, rgba(5,5,5,0.88) 82%, rgba(5,5,5,0.98) 100%); }}
.topbar {{ position:absolute; top:0; left:0; width:1080px; height:12px; background:linear-gradient(90deg,#ff3b1f,#ffae00); }}
.botbar {{ position:absolute; bottom:0; left:0; width:1080px; height:12px; background:linear-gradient(90deg,#ffae00,#ff3b1f); }}
.badge {{ position:absolute; top:60px; left:0; width:1080px; text-align:center;
  color:#ffd000; font-weight:800; font-size:24px; letter-spacing:3px; }}
.content {{ position:absolute; top:680px; left:0; width:1080px; text-align:center; padding:0 60px; }}
.label {{ color:#ddd; font-size:30px; font-weight:600; letter-spacing:6px; text-transform:uppercase; margin-bottom:18px; }}
.title {{ font-family:{TITLE_FONT}; font-weight:700; font-size:130px; color:#ffd000;
  text-shadow: 0 0 50px rgba(255,180,0,0.7), 0 5px 0 rgba(0,0,0,0.6); line-height:0.95; letter-spacing:1px; }}
.sub {{ color:#fff; font-size:36px; font-weight:600; text-shadow:0 2px 8px rgba(0,0,0,0.9); margin-top:24px; }}
.linkbox {{ position:absolute; bottom:170px; left:50%; transform:translateX(-50%);
  border:3px solid #ffd000; border-radius:50px; padding:22px 50px; background:rgba(0,0,0,0.55); }}
.linkbox .txt {{ color:#ffd000; font-family:{TITLE_FONT}; font-weight:700; font-size:44px; letter-spacing:1px; }}
.footer {{ position:absolute; bottom:60px; left:0; width:1080px; text-align:center; }}
.footer .handle {{ color:#cfcfcf; font-size:26px; font-weight:600; letter-spacing:1px; }}
</style></head><body>
<img class="bg" src="{bg_url}">
<div class="scrim"></div>
<div class="topbar"></div>
<div class="badge">PERSIAN TIPSTER</div>
<div class="content">
  <div class="label">{content["label"]}</div>
  <div class="title">{content["title_html"]}</div>
  <div class="sub">{content["sub"]}</div>
</div>
<div class="linkbox"><div class="txt">{content["link_text"]}</div></div>
<div class="footer"><div class="handle">Tap link above for free daily picks</div></div>
<div class="botbar"></div>
</body></html>"""

async def render_image(content):
    from playwright.async_api import async_playwright
    html_path = "/tmp/story.html"
    img_path = "/tmp/story.png"
    with open(html_path,"w") as f:
        f.write(build_html(content))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":1080,"height":1920})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=img_path)
        await browser.close()
    return img_path

def upload_to_github(path, filename):
    if not GH_TOKEN or not GH_REPO: return None
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/tags/media-assets", headers=headers, timeout=10)
    if r.status_code == 404:
        r2 = requests.post(f"https://api.github.com/repos/{GH_REPO}/releases", headers=headers,
            json={"tag_name":"media-assets","name":"Media Assets","draft":False,"prerelease":True}, timeout=10)
        release = r2.json()
    else:
        release = r.json()
    rid = release.get("id")
    if not rid: return None
    assets = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/{rid}/assets", headers=headers, timeout=10).json()
    for a in (assets if isinstance(assets,list) else []):
        if a.get("name") == filename:
            requests.delete(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}", headers=headers, timeout=10)
    up_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{rid}/assets?name={filename}"
    with open(path,"rb") as f:
        up = requests.post(up_url, headers={**headers,"Content-Type":"image/png"}, data=f, timeout=60)
    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        return f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
    return None

def publish_story(image_url):
    r1 = requests.post(f"{IG_BASE}/{IG_USER_ID}/media",
        params={"image_url": image_url, "media_type": "STORIES", "access_token": IG_TOKEN}, timeout=30)
    if r1.status_code != 200:
        print(f"  Container error: {r1.text[:200]}")
        return None
    cid = r1.json().get("id")
    if not cid: return None
    print(f"  Container: {cid} - waiting 20s...")
    time.sleep(20)
    r2 = requests.post(f"{IG_BASE}/{IG_USER_ID}/media_publish",
        params={"creation_id": cid, "access_token": IG_TOKEN}, timeout=30)
    if r2.status_code != 200:
        print(f"  Publish error: {r2.text[:200]}")
        return None
    return r2.json().get("id")

def notify(msg):
    if TELEGRAM_TOKEN:
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":NOTIFY_USER,"text":msg,"disable_notification":True}, timeout=10)

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Stories v4 - type: {STORY_TYPE}")
    content = get_story_content()
    print(f"  Generating image (background+Teko)...")
    img_path = asyncio.run(render_image(content))
    filename = f"story_{STORY_TYPE}_{int(time.time())}.png"
    image_url = upload_to_github(img_path, filename)
    if not image_url:
        print("  FAILED: upload error")
        return
    print("  Publishing Story...")
    post_id = publish_story(image_url)
    if post_id:
        print(f"  PUBLISHED! ID: {post_id}")
        notify(f"Story pubblicata\nTipo: {STORY_TYPE}\nID: {post_id}")
    else:
        print("  FAILED to publish")

if __name__ == "__main__":
    main()
