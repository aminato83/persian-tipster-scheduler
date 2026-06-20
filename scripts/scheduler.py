"""
Persian Tipster — Master Scheduler v4
Motore: HTML/CSS + Playwright (testo perfetto) + libreria sfondi cinematografici + font Teko.
Genera e pubblica nello stesso momento del trigger — niente container che scadono.
"""
import os, json, time, requests, asyncio, random, urllib.parse
from datetime import datetime, timezone

COMPOSIO_KEY = os.environ["COMPOSIO_API_KEY"]
WINDOW_SEC   = 900
IG_ACCOUNT   = "instagram_mease-bitter"
PUBLISHED_FILE = "published.json"

RAW_BASE = "https://raw.githubusercontent.com/aminato83/persian-tipster-scheduler/main/assets/backgrounds/"

BACKGROUNDS = {
    "pretmatch": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_37%20%282%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_37%20%281%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_13_05%20%283%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_13_05%20%282%29.png",
    ],
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
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_38_44%20%281%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_20_20%20%282%29.png",
    ],
    "educational": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_40_38%20%283%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_40_39%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_40_37%20%281%29.png",
    ],
    "story": [
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_42_38%20%284%29.png",
        RAW_BASE + "ChatGPT%20Image%2019%20giu%202026%2C%2015_13_06%20%284%29.png",
    ],
}

GOOGLE_FONTS_IMPORT = "family=Teko:wght@500;600;700&family=Inter:wght@400;600;800"
TITLE_FONT = "'Teko', sans-serif"

def get_bg(category):
    return random.choice(BACKGROUNDS.get(category, BACKGROUNDS["pretmatch"]))

SCHEDULE = [
    {
        "name": "belgium_matchday",
        "ts": 1782061200,
        "category": "matchday",
        "label": "Match Day",
        "title": "BELGIUM<br>vs IRAN",
        "sub": "June 21 &middot; 21:00 CET &middot; Group G",
        "footer_ctx": "Iran fresh off 2-2 vs New Zealand &middot; full pick on Telegram",
        "caption": (
            "MATCH DAY\n\nBelgium vs Iran - TODAY 21:00 CET\nFIFA World Cup 2026 - Group G\n\n"
            "Iran showed they can compete after that 2-2 with New Zealand. "
            "Belgium have the firepower, but Iran's low block has already "
            "proven it can frustrate good teams.\n\nFull pick on Telegram. Follow live on Stories.\n\n"
            "Free channel -> link in bio\n#belgiumvsiran #worldcup2026 #FIFA2026 #persiantipster #sportsbetting"
        ),
    },
    {
        "name": "egypt_intel",
        "ts": 1782408600,
        "category": "pretmatch",
        "label": "Pre-Match Intel",
        "title": "EGYPT<br>vs IRAN",
        "sub": "June 27 &middot; 05:00 CET &middot; Group G",
        "footer_ctx": "Decisive match for knockout hopes &middot; Lumen Field, Seattle",
        "caption": (
            "EGYPT vs IRAN - PRE-MATCH INTEL\n\nJune 27, 05:00 CET - Lumen Field, Seattle\n"
            "FIFA World Cup 2026 - Group G - The decisive match\n\n"
            "Egypt: 2.20 avg (slight favorites)\nDraw: 3.10 avg\nIran: 3.90 avg\n\n"
            "Both teams could be fighting for second place in the group. "
            "Salah vs Iran's defense is the matchup that decides this game.\n\n"
            "Full pick on Telegram before kick-off.\n\nFree channel -> link in bio\n"
            "#egyptvsiran #worldcup2026 #FIFA2026 #bettingtips #persiantipster #valuebetting"
        ),
    },
    {
        "name": "egypt_matchday",
        "ts": 1782496800,
        "category": "matchday",
        "label": "Match Day Tonight",
        "title": "EGYPT<br>vs IRAN",
        "sub": "Kicks off 05:00 CET",
        "footer_ctx": "Iran's biggest match of the group stage &middot; pick live on Telegram",
        "caption": (
            "MATCH DAY TONIGHT\n\nEgypt vs Iran - kicks off 05:00 CET\n\n"
            "This is the moment. A win or the right draw and Iran's knockout stage dream is still alive.\n\n"
            "Pick already live on Telegram. Set an alarm or follow Stories for the result first thing.\n\n"
            "Free channel -> link in bio\n#egyptvsiran #worldcup2026 #FIFA2026 #persiantipster #sportsbetting"
        ),
    },
]

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f: return json.load(f)
    return {}

def save_published(data):
    with open(PUBLISHED_FILE,"w") as f: json.dump(data, f, indent=2)

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
.content {{ position:absolute; top:120px; left:0; width:1080px; text-align:center; padding:0 50px; }}
.label {{ color:#ddd; font-size:26px; font-weight:600; letter-spacing:5px; text-transform:uppercase; margin-bottom:10px; }}
.title {{ font-family:{TITLE_FONT}; font-weight:700; font-size:120px; color:#ffd000;
  text-shadow: 0 0 40px rgba(255,180,0,0.7), 0 4px 0 rgba(0,0,0,0.6); line-height:0.95; letter-spacing:1px; }}
.sub {{ color:#fff; font-size:30px; font-weight:700; text-shadow:0 2px 8px rgba(0,0,0,0.9); margin-top:8px; }}
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
  <div class="title">{post["title"]}</div>
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
    html_path = f"/tmp/{post['name']}.html"
    img_path = f"/tmp/{post['name']}.png"
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
    if not cid:
        print(f"  Container error: {r1.text[:200]}")
        return None
    print(f"  Container: {cid} - waiting 10s...")
    time.sleep(10)
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=headers,
        json={"input":{"ig_user_id":"me","creation_id":cid,"max_wait_seconds":90},
              "connectedAccountId": IG_ACCOUNT}, timeout=120)
    return r2.json().get("data",{}).get("id")

def main():
    now = int(time.time())
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Checking schedule...")

    published = load_published()

    for post in SCHEDULE:
        name = post["name"]
        diff = now - post["ts"]

        if 0 <= diff <= WINDOW_SEC and name not in published:
            print(f"  -> Generating + publishing: {name}")
            img_path = asyncio.run(render_image(post))
            filename = f"{name}.png"
            image_url = upload_to_github(img_path, filename)
            if not image_url:
                print(f"  FAILED: upload error for {name}")
                continue
            ig_id = publish_via_composio(image_url, post["caption"])
            if ig_id:
                published[name] = {
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "instagram_post_id": ig_id
                }
                save_published(published)
                print(f"  PUBLISHED! Instagram ID: {ig_id}")
            else:
                print(f"  FAILED to publish {name}")

        elif diff < 0:
            h = abs(diff)//3600
            m = (abs(diff)%3600)//60
            print(f"  Waiting: {name} in {h}h {m}m")
        elif name in published:
            print(f"  Done: {name}")

if __name__ == "__main__":
    main()
