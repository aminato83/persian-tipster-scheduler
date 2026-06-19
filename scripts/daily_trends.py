"""
Persian Tipster — Daily Trends Engine
Gira ogni giorno: cerca il momento piu caldo del Mondiale su Reddit,
lo collega al nostro angolo scommesse, genera + pubblica un post.
"""
import os, json, time, requests, asyncio, random
from datetime import datetime, timezone

COMPOSIO_KEY = os.environ["COMPOSIO_API_KEY"]
IG_ACCOUNT   = "instagram_mease-bitter"
PUBLISHED_FILE = "published.json"

RAW_BASE = "https://raw.githubusercontent.com/aminato83/persian-tipster-scheduler/main/assets/backgrounds/"
BACKGROUNDS = {
    "matchday": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_37%20%283%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_38_45%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_20_21%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_20_21%20%283%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_20_20%20%281%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2014_59_31.png",
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
    return random.choice(BACKGROUNDS.get(category, BACKGROUNDS["matchday"]))

# Calendario partite Iran World Cup 2026 (date note)
IRAN_MATCHES = [
    {"date": "2026-06-15", "opponent": "New Zealand", "result": "2-2 draw"},
    {"date": "2026-06-21", "opponent": "Belgium", "result": None},
    {"date": "2026-06-27", "opponent": "Egypt", "result": None},
]

def get_top_worldcup_story():
    """Segnale affidabile basato sul calendario reale Iran invece di scraping Reddit
       (Reddit blocca le richieste da datacenter/cloud IP - anti-bot standard)."""
    today = datetime.now(timezone.utc).date()

    for m in IRAN_MATCHES:
        match_date = datetime.strptime(m["date"], "%Y-%m-%d").date()
        days_diff = (match_date - today).days

        if days_diff == 0:
            return {"title": f"Iran vs {m['opponent']} - TODAY",
                    "score": 9999, "is_iran_specific": True, "type": "matchday"}
        elif days_diff == 1:
            return {"title": f"Iran vs {m['opponent']} - tomorrow",
                    "score": 9999, "is_iran_specific": True, "type": "preview"}
        elif -1 <= days_diff <= -1 and m.get("result"):
            return {"title": f"Iran {m['result']} vs {m['opponent']}",
                    "score": 9999, "is_iran_specific": True, "type": "recap"}

    return None

def build_post_content(story):
    if not story:
        title = "World Cup 2026 is delivering every single day"
        is_iran = False
    else:
        title = story["title"]
        is_iran = story.get("is_iran_specific", False)

    if is_iran:
        label = "Iran Trending Today"
        title_html = "IRAN IS<br>TRENDING"
        caption = (
            f"IRAN IS TRENDING TODAY\n\n{title}\n\n"
            "This is the conversation right now. We're already looking at "
            "what it means for the next match and the next pick.\n\n"
            "Daily Iranian sports analysis, zero hype, just numbers.\n\n"
            "Free channel -> link in bio\n"
            "#iranworldcup #worldcup2026 #FIFA2026 #persiantipster #sportsbetting"
        )
    else:
        label = "Trending Today"
        title_html = "WORLD CUP<br>WATCH"
        caption = (
            f"TRENDING TODAY\n\n{title}\n\n"
            "The World Cup is delivering drama every single matchday. "
            "While everyone reacts to the headlines, we're already looking at "
            "what it means for tomorrow's odds.\n\n"
            "Daily picks, real analysis, zero hype.\n\n"
            "Free channel -> link in bio\n"
            "#worldcup2026 #FIFA2026 #persiantipster #sportsbetting #bettingtips"
        )

    return {
        "category": "matchday",
        "label": label,
        "title_html": title_html,
        "sub": title[:70],
        "footer_ctx": "Daily Iranian sports analysis & picks on Telegram",
        "caption": caption,
    }

def build_html(post):
    bg_url = get_bg(post["category"])
    return f"""<!DOCTYPE html><html><head><style>
@import url('https://fonts.googleapis.com/css2?{GOOGLE_FONTS_IMPORT}&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1080px; height:1350px; position:relative; font-family:'Inter',sans-serif; overflow:hidden; }}
.bg {{ position:absolute; top:0; left:0; width:1080px; height:1350px; object-fit:cover; }}
.scrim {{ position:absolute; top:0; left:0; width:1080px; height:1350px;
  background: linear-gradient(to bottom, rgba(5,5,5,0.85) 0%, rgba(5,5,5,0.2) 30%, rgba(5,5,5,0.15) 55%, rgba(5,5,5,0.85) 80%, rgba(5,5,5,0.97) 100%); }}
.topbar {{ position:absolute; top:0; left:0; width:1080px; height:10px; background:linear-gradient(90deg,#ff3b1f,#ffae00); }}
.botbar {{ position:absolute; bottom:0; left:0; width:1080px; height:10px; background:linear-gradient(90deg,#ffae00,#ff3b1f); }}
.badge {{ position:absolute; top:40px; right:40px; border:2px solid #ffd000; border-radius:8px;
  padding:8px 16px; color:#ffd000; font-weight:800; font-size:20px; letter-spacing:1px; background:rgba(0,0,0,0.55); }}
.content {{ position:absolute; top:120px; left:0; width:1080px; text-align:center; padding:0 60px; }}
.label {{ color:#ddd; font-size:26px; font-weight:600; letter-spacing:5px; text-transform:uppercase; margin-bottom:10px; }}
.title {{ font-family:{TITLE_FONT}; font-weight:700; font-size:110px; color:#ffd000;
  text-shadow: 0 0 40px rgba(255,180,0,0.7), 0 4px 0 rgba(0,0,0,0.6); line-height:0.95; letter-spacing:1px; }}
.sub {{ color:#fff; font-size:28px; font-weight:600; text-shadow:0 2px 8px rgba(0,0,0,0.9); margin-top:14px; line-height:1.3; }}
.footer {{ position:absolute; bottom:50px; left:0; width:1080px; text-align:center; }}
.footer .ctx {{ color:#cfcfcf; font-size:23px; margin-bottom:10px; }}
.footer .handle {{ color:#ffd000; font-size:30px; font-weight:800; letter-spacing:1px; font-family:{TITLE_FONT}; }}
</style></head><body>
<img class="bg" src="{bg_url}">
<div class="scrim"></div>
<div class="topbar"></div>
<div class="badge">PERSIAN TIPSTER</div>
<div class="content">
  <div class="label">{post["label"]}</div>
  <div class="title">{post["title_html"]}</div>
  <div class="sub">{post["sub"]}</div>
</div>
<div class="footer">
  <div class="ctx">{post["footer_ctx"]}</div>
  <div class="handle">@tipster_persian</div>
</div>
<div class="botbar"></div>
</body></html>"""

async def render_image(post):
    from playwright.async_api import async_playwright
    html_path = "/tmp/daily_trend.html"
    img_path = "/tmp/daily_trend.png"
    with open(html_path,"w") as f:
        f.write(build_html(post))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":1080,"height":1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=img_path)
        await browser.close()
    return img_path

def upload_to_github(path, filename):
    GH_TOKEN = os.environ.get("GITHUB_TOKEN","")
    GH_REPO  = os.environ.get("GITHUB_REPOSITORY","")
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

def publish_via_composio(image_url, caption):
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}
    r1 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=headers,
        json={"input": {"ig_user_id":"me","image_url":image_url,"caption":caption},
              "connectedAccountId": IG_ACCOUNT}, timeout=30)
    cid = r1.json().get("data",{}).get("id")
    if not cid: return None
    time.sleep(10)
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","creation_id":cid,"max_wait_seconds":90},
              "connectedAccountId": IG_ACCOUNT}, timeout=120)
    return r2.json().get("data",{}).get("id")

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f: return json.load(f)
    return {}

def save_published(data):
    with open(PUBLISHED_FILE,"w") as f: json.dump(data, f, indent=2)

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    name = f"daily_trend_{today}"
    print(f"[{datetime.now(timezone.utc)}] Daily trend check: {name}")

    published = load_published()
    if name in published:
        print("  Already published today")
        return

    story = get_top_worldcup_story()
    print(f"  Signal: {story}")

    if not story:
        print("  Nessun segnale Iran oggi - skip (rispetta cadenza 1 post/giorno max, qualita > quantita)")
        return

    post = build_post_content(story)
    img_path = asyncio.run(render_image(post))
    image_url = upload_to_github(img_path, f"{name}.png")
    if not image_url:
        print("  FAILED: upload error")
        return

    ig_id = publish_via_composio(image_url, post["caption"])
    if ig_id:
        published[name] = {
            "published_at": datetime.now(timezone.utc).isoformat(),
            "instagram_post_id": ig_id,
            "source_story": story
        }
        save_published(published)
        print(f"  PUBLISHED! IG ID: {ig_id}")
    else:
        print("  FAILED to publish")

if __name__ == "__main__":
    main()
