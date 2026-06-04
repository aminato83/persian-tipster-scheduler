"""
Persian Tipster — Weekly Content Generator v2
Copre: Azadegan League (Div 1), World Cup, altri sport iraniani.
Ogni lunedì genera post settimanali automaticamente.
"""
import os, json, requests, base64, time
from datetime import datetime, timezone, timedelta

COMPOSIO_KEY   = os.environ["COMPOSIO_API_KEY"]
OPENAI_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
ODDS_API_KEY   = "d37c9bca5b04e8e1093e5827cc96bdc3"

IG_ACCOUNT     = "instagram_mease-bitter"
NOTIFY_USER    = 899950945
PUBLISHED_FILE = "published.json"
SCHEDULE_FILE  = "weekly_schedule.json"

TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ── Timing helpers ───────────────────────────────────────────
def cet_ts(days_from_now, hour=18, minute=30):
    now = datetime.now(timezone(timedelta(hours=2)))
    target = now + timedelta(days=days_from_now)
    target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return int(target.timestamp())

# ── OpenAI Image (LOW quality = $0.011) ──────────────────────
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

# ── Upload image via Composio ─────────────────────────────────
def upload_image(img_bytes, fname):
    path = f"/tmp/{fname}"
    open(path,"wb").write(img_bytes)
    r = requests.post(
        "https://backend.composio.dev/api/v3/files",
        headers={"x-api-key": COMPOSIO_KEY},
        files={"file": (fname, open(path,"rb"), "image/jpeg")},
        timeout=30)
    if r.status_code in [200,201]:
        d = r.json()
        return d.get("s3key") or d.get("key")
    # Fallback: try v2
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/COMPOSIO_FILE_UPLOAD/execute",
        headers={"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"},
        json={"input": {"file_content": base64.b64encode(img_bytes).decode(),
                        "file_name": fname, "mime_type": "image/jpeg"}},
        timeout=30)
    d2 = r2.json()
    return d2.get("data",{}).get("s3key")

def create_container(s3key, caption):
    r = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers={"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"},
        json={"input": {"ig_user_id":"me",
                        "image_file":{"mimetype":"image/jpeg","name":"post.jpg","s3key":s3key},
                        "caption":caption},
              "connectedAccountId": IG_ACCOUNT},
        timeout=30)
    return r.json().get("data",{}).get("id")

# ── Get Azadegan League fixtures via SportDB ──────────────────
def get_azadegan_fixtures():
    """Get upcoming Azadegan League fixtures from SportDB"""
    try:
        # SportDB ID for Azadegan League
        r = requests.get(
            "https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id=4946",
            headers={"User-Agent": "PersianTipster/1.0"}, timeout=10)
        events = r.json().get("events", []) or []
        
        matches = []
        now_ts = int(time.time())
        
        for e in events[:5]:
            date_str = e.get("dateEvent","")
            time_str = e.get("strTime","") or "00:00:00"
            if date_str:
                try:
                    dt = datetime.fromisoformat(f"{date_str}T{time_str[:8]}").replace(
                        tzinfo=timezone.utc)
                    ts = int(dt.timestamp())
                    if ts > now_ts:
                        matches.append({
                            "home": e.get("strHomeTeam",""),
                            "away": e.get("strAwayTeam",""),
                            "ts": ts,
                            "date_str": date_str,
                            "competition": "Azadegan League (Division 1)",
                            "league_short": "DIV 1"
                        })
                except:
                    pass
        
        return matches[:3]
    except Exception as ex:
        print(f"  SportDB error: {ex}")
        return []

# ── Get World Cup Iran fixtures ───────────────────────────────
def get_wc_fixtures():
    try:
        r = requests.get(
            "https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id=134511",
            headers={"User-Agent":"PersianTipster/1.0"}, timeout=10)
        events = r.json().get("events",[]) or []
        now_ts = int(time.time())
        matches = []
        for e in events[:2]:
            date_str = e.get("dateEvent","")
            time_str = e.get("strTime","") or "00:00:00"
            if date_str:
                try:
                    dt = datetime.fromisoformat(f"{date_str}T{time_str[:8]}").replace(tzinfo=timezone.utc)
                    ts = int(dt.timestamp())
                    if ts > now_ts:
                        matches.append({
                            "home": e.get("strHomeTeam",""),
                            "away": e.get("strAwayTeam",""),
                            "ts": ts, "date_str": date_str,
                            "competition": "FIFA World Cup 2026",
                            "league_short": "WC 2026"
                        })
                except:
                    pass
        return matches
    except:
        return []

# ── Generate prematch post ────────────────────────────────────
def gen_prematch(match):
    home, away = match["home"], match["away"]
    comp = match["competition"]
    league_short = match["league_short"]
    date_str = match["date_str"]

    prompt = f"""Professional dark sports betting Instagram post.
Black background with red-orange atmospheric glow.
Bold gold top text: PRE-MATCH INTEL
Large white center text: {home.upper()} vs {away.upper()}
Small gold text: {date_str} · {comp}
Three dark boxes with gold borders showing WIN odds.
Bottom gold text: @persiantipster · Free analysis: link in bio
Thin red accent lines top and bottom.
Professional sports analytics design. No people or faces."""

    img = gen_image(prompt)
    if not img: return None

    caption = f"""PRE-MATCH INTEL 📊

{home} vs {away}
{comp}

⚽ {date_str}

Iranian football — the market European bookmakers underestimate every week.

This is where +31% yield comes from. Not from Premier League. From knowing what others don't.

Full analysis drops on Telegram before kick-off.

📲 Free channel → link in bio
📊 persiantipster.blogabet.com

#iranianfootball #{'azadegan' if 'Azadegan' in comp or 'Division' in comp else 'worldcup2026'} #footballbetting #valuebetting #persiantipster #bettingtips #sportsbetting #{"div1iran" if 'Div' in league_short else "iranworldcup"}"""

    post_ts = max(match["ts"] - 48*3600, cet_ts(1))
    return {"img":img, "caption":caption, "ts":post_ts,
            "name":f"prematch_{home[:10].lower().replace(' ','_')}_vs_{away[:10].lower().replace(' ','_')}"}

# ── Weekly educational topics ─────────────────────────────────
TOPICS = [
    ("AZADEGAN LEAGUE GUIDE", "Division 1 — The market European bettors ignore"),
    ("ASIAN HANDICAP vs 1X2", "Why smart bettors never use 1X2"),
    ("VALUE BETTING 101", "How to find edges the bookmakers miss"),
    ("BANKROLL MANAGEMENT", "Why most bettors lose — and how to avoid it"),
    ("IRANIAN FOOTBALL INSIDER", "5 things European bookmakers don't know"),
    ("UNDER MARKET STRATEGY", "Why Iranian matches stay tight — and how to profit"),
]

def gen_educational():
    week = datetime.now().isocalendar()[1]
    topic, subtitle = TOPICS[week % len(TOPICS)]

    prompt = f"""Dark professional educational sports betting Instagram post.
Black background with subtle red-orange glow.
Small top text: PERSIAN TIPSTER · EDUCATION
Large bold gold title: {topic}
White subtitle below: {subtitle}
Clean minimalist sports analytics design.
@persiantipster footer in gold.
No people. Professional dark aesthetic."""

    img = gen_image(prompt)
    if not img: return None

    caption = f"""📚 {topic}

{subtitle}

This is what separates profitable bettors from the rest.

I've been applying these principles on Iranian football, futsal, volleyball, basketball and handball for years.

Result: +31% yield. 756 documented picks. All verified on Blogabet.

Save this post — you'll want to come back to it.

📊 persiantipster.blogabet.com
📲 Free daily picks → link in bio

#valuebetting #bettingstrategy #persiantipster #bettingeducation #sportsbetting #iranianfootball #footballbetting"""

    return {"img":img, "caption":caption, "ts":cet_ts(0,18,30),
            "name":f"edu_week{datetime.now().isocalendar()[1]}"}

# ── Main ──────────────────────────────────────────────────────
def load_schedule():
    return json.load(open(SCHEDULE_FILE)) if os.path.exists(SCHEDULE_FILE) else []

def save_schedule(s):
    json.dump(s, open(SCHEDULE_FILE,"w"), indent=2)

def load_published():
    return json.load(open(PUBLISHED_FILE)) if os.path.exists(PUBLISHED_FILE) else {}

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Weekly Generator v2 starting...")

    schedule = load_schedule()
    new_posts = []

    # 1. Azadegan League pre-match intel
    print("\n📅 Fetching Azadegan League fixtures...")
    div1_matches = get_azadegan_fixtures()
    print(f"  Found {len(div1_matches)} upcoming Division 1 matches")

    # 2. World Cup fixtures (if still active)
    print("\n🏆 Fetching World Cup fixtures...")
    wc_matches = get_wc_fixtures()
    print(f"  Found {len(wc_matches)} upcoming WC matches")

    all_matches = div1_matches + wc_matches

    for match in all_matches:
        slug = f"prematch_{match['home'][:8]}_{match['away'][:8]}_{match['ts']}"
        if any(slug[:20] in s.get("name","") for s in schedule):
            print(f"  ⏭ Already scheduled: {match['home']} vs {match['away']}")
            continue

        print(f"\n  Generating: {match['home']} vs {match['away']} ({match['competition']})")
        post = gen_prematch(match)
        if not post: continue

        s3key = upload_image(post["img"], f"{post['name']}.jpg")
        if not s3key: print(f"  ❌ Upload failed"); continue

        cid = create_container(s3key, post["caption"])
        if cid:
            schedule.append({"id":cid,"ts":post["ts"],"name":post["name"],"type":"prematch"})
            new_posts.append(post["name"])
            print(f"  ✅ Scheduled: {post['name']} (container: {cid})")

    # 3. Educational post
    print("\n📚 Generating educational post...")
    edu_key = f"edu_week{datetime.now().isocalendar()[1]}"
    if edu_key not in [s.get("name","") for s in schedule]:
        edu = gen_educational()
        if edu:
            s3key = upload_image(edu["img"], f"{edu['name']}.jpg")
            if s3key:
                cid = create_container(s3key, edu["caption"])
                if cid:
                    schedule.append({"id":cid,"ts":edu["ts"],"name":edu_key,"type":"educational"})
                    new_posts.append(edu_key)
                    print(f"  ✅ Educational post scheduled")

    save_schedule(schedule)

    if new_posts and TELEGRAM_TOKEN:
        msg = f"🟠 WEEKLY GENERATOR\n\n✅ {len(new_posts)} nuovi post:\n"
        for p in new_posts: msg += f"  • {p}\n"
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id":NOTIFY_USER,"text":msg,"disable_notification":True}, timeout=10)

    print(f"\n✅ Done. {len(new_posts)} new posts generated.")

if __name__ == "__main__":
    main()
