"""
Persian Tipster — Weekly Content Generator
Ogni lunedì genera automaticamente:
- Pre-match intel per le partite della settimana (con quote live)
- Post educativo settimanale
- Story templates
- Aggiunge tutto allo scheduler
"""
import os, json, requests, base64, time
from datetime import datetime, timezone, timedelta

COMPOSIO_KEY = os.environ["COMPOSIO_API_KEY"]
OPENAI_KEY   = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")

IG_ACCOUNT   = "instagram_mease-bitter"
NOTIFY_USER  = 899950945
PUBLISHED_FILE = "published.json"
SCHEDULE_FILE  = "weekly_schedule.json"

ODDS_API_KEY = "d37c9bca5b04e8e1093e5827cc96bdc3"  # from earlier

TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ── Posting times (Unix timestamps helper) ──────────────────
def next_weekday_ts(weekday, hour_cet, minute_cet=30, weeks_ahead=0):
    """Get Unix timestamp for next occurrence of weekday at hour:minute CET"""
    now = datetime.now(timezone(timedelta(hours=2)))  # CET/CEST
    days_ahead = weekday - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    days_ahead += weeks_ahead * 7
    target = now.replace(hour=hour_cet, minute=minute_cet, second=0, microsecond=0)
    target = target + timedelta(days=days_ahead)
    return int(target.timestamp())

# ── OpenAI Image Generation (LOW quality = $0.011) ───────────
def generate_image(prompt):
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-1", "prompt": prompt,
              "size": "1024x1024", "quality": "low", "output_format": "jpeg"},
        timeout=60
    )
    data = r.json()
    if data.get("data"):
        return base64.b64decode(data["data"][0]["b64_json"])
    print(f"  Image error: {data.get('error','?')}")
    return None

# ── Upload image to Composio S3 via API ───────────────────────
def upload_image_bytes(img_bytes, filename):
    """Save image and upload to get s3key"""
    path = f"/tmp/{filename}"
    with open(path,"wb") as f: f.write(img_bytes)
    
    # Get presigned URL from Composio
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}
    r = requests.post(
        "https://backend.composio.dev/api/v2/actions/COMPOSIO_FILE_UPLOAD/execute",
        headers=headers,
        json={"input": {"file_path": path}},
        timeout=30
    )
    
    # Alternative: use the file upload endpoint directly
    r2 = requests.post(
        "https://backend.composio.dev/api/v3/files",
        headers={"x-api-key": COMPOSIO_KEY},
        files={"file": (filename, open(path,"rb"), "image/jpeg")},
        timeout=30
    )
    
    if r2.status_code == 200:
        data = r2.json()
        return data.get("s3key") or data.get("key")
    
    print(f"  Upload error: {r2.status_code} {r2.text[:100]}")
    return None

def create_ig_container(s3key, caption, media_type="IMAGE"):
    headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}
    r = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=headers,
        json={"input": {"ig_user_id": "me",
                        "image_file": {"mimetype":"image/jpeg","name":"post.jpg","s3key":s3key},
                        "caption": caption},
              "connectedAccountId": IG_ACCOUNT},
        timeout=30
    )
    data = r.json()
    return data.get("data", {}).get("id")

# ── Get upcoming matches from The Odds API ────────────────────
def get_upcoming_matches():
    matches = []
    
    # World Cup first (if active)
    r = requests.get("https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/",
        params={"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "h2h,totals",
                "oddsFormat": "decimal", "dateFormat": "unix"},
        timeout=15)
    
    if r.status_code == 200:
        for match in r.json():
            home, away = match.get("home_team",""), match.get("away_team","")
            if "Iran" in home or "Iran" in away:
                commence = match.get("commence_time", 0)
                now = int(time.time())
                if commence > now:  # future match
                    # Extract odds
                    h2h = {}
                    for bm in match.get("bookmakers",[])[:5]:
                        for mkt in bm.get("markets",[]):
                            if mkt.get("key")=="h2h":
                                for o in mkt.get("outcomes",[]):
                                    name = o.get("name")
                                    price = o.get("price",0)
                                    if name not in h2h: h2h[name]=[]
                                    h2h[name].append(price)
                    
                    avg_odds = {k: round(sum(v)/len(v),2) for k,v in h2h.items() if v}
                    matches.append({
                        "home": home, "away": away,
                        "ts": commence, "odds": avg_odds,
                        "competition": "FIFA World Cup 2026"
                    })
    
    # Sort by date
    matches.sort(key=lambda x: x["ts"])
    return matches[:3]  # max 3 matches per week

# ── Generate weekly content ───────────────────────────────────
def generate_prematch_post(match):
    home, away = match["home"], match["away"]
    odds = match["odds"]
    date_str = datetime.fromtimestamp(match["ts"], tz=timezone.utc).strftime("%d %b %Y")
    competition = match["competition"]
    
    # Generate image
    home_odd = odds.get(home, 0)
    away_odd = odds.get(away, 0)
    draw_odd = odds.get("Draw", 0)
    
    prompt = f"""Professional dark sports betting Instagram post.
    Black background with orange-red glow effect.
    Top gold bold text: PRE-MATCH INTEL
    Center large white text: {home.upper()} vs {away.upper()}
    Small text below: {date_str} · {competition}
    Three dark gold-bordered stat boxes:
    Left: '{home.upper()} WIN' with '{home_odd}' in gold large
    Center: 'DRAW' with '{draw_odd}' in grey
    Right: '{away.upper()} WIN' with '{away_odd}' in blue
    Bottom gold text: @persiantipster
    Thin red accent bars top and bottom.
    Professional sports analytics design. No people."""
    
    img_bytes = generate_image(prompt)
    if not img_bytes:
        return None
    
    # Generate caption
    caption = f"""PRE-MATCH INTEL 📊

{home} vs {away}
{date_str} · {competition}

Live odds from 30+ bookmakers:

{'🟢' if home_odd < 2 else '⚪'} {home} win: {home_odd}
⚪ Draw: {draw_odd}
{'🔴' if away_odd > 3 else '⚪'} {away} win: {away_odd}

The context that mainstream tipsters won't give you:
• {home} style: defensive, pragmatic, 1-0 wins
• Bookmakers underestimate Iranian football every time
• This is where +31% yield comes from

Full analysis drops on Telegram before kick-off.

📲 Free channel → link in bio
📊 persiantipster.blogabet.com

#{'iranworldcup' if 'Iran' in home or 'Iran' in away else 'iranianfootball'} #bettingtips #valuebetting #persiantipster #sportsbetting #prematchanalysis"""
    
    # Schedule 48h before match
    post_ts = match["ts"] - (48 * 3600)
    now_ts = int(time.time())
    if post_ts < now_ts:
        post_ts = now_ts + 3600  # if already past, post in 1 hour
    
    return {"img_bytes": img_bytes, "caption": caption, "ts": post_ts,
            "name": f"prematch_{home.lower().replace(' ','_')}_vs_{away.lower().replace(' ','_')}"}

def generate_educational_post():
    """Generate weekly educational carousel post"""
    topics = [
        ("ASIAN HANDICAP GUIDE", "Why removing the draw doubles your edge"),
        ("VALUE BETTING 101", "How to find edges the bookmakers miss"),
        ("IRANIAN FOOTBALL EXPLAINED", "The market nobody else is covering"),
        ("BANKROLL MANAGEMENT", "Why most bettors lose — and how to avoid it"),
        ("UNDERSTANDING ODDS", "Converting odds to probability"),
    ]
    
    # Pick based on week number
    week = datetime.now().isocalendar()[1]
    topic, subtitle = topics[week % len(topics)]
    
    prompt = f"""Professional dark educational sports betting Instagram post.
    Black background with subtle red glow.
    Top small gold text: PERSIAN TIPSTER EDUCATION
    Large bold gold title: {topic}
    White subtitle: {subtitle}
    5 bullet points in white text about the topic.
    Bottom: @persiantipster in gold.
    Clean professional design with gold accent lines.
    No people. Sports analytics aesthetic."""
    
    img_bytes = generate_image(prompt)
    if not img_bytes: return None
    
    caption = f"""📚 {topic}

{subtitle}

Swipe for the full breakdown →

This is the knowledge that separates profitable bettors from the other 95%.

I've been applying these principles on Iranian football markets for years.
Result: +31% yield over 756 documented picks on Blogabet.

📊 Full record → persiantipster.blogabet.com
📲 Free daily picks → link in bio

#valuebetting #bettingstrategy #persiantipster #bettingeducation #sportsbetting #footballbetting"""
    
    return {"img_bytes": img_bytes, "caption": caption,
            "ts": next_weekday_ts(0, 18, 30),  # Monday 18:30 CET
            "name": f"educational_{topic.lower().replace(' ','_')}"}

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE) as f: return json.load(f)
    return []

def save_schedule(schedule):
    with open(SCHEDULE_FILE,"w") as f: json.dump(schedule, f, indent=2)

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Weekly Generator starting...")
    
    schedule = load_schedule()
    published = load_published() if os.path.exists(PUBLISHED_FILE) else {}
    new_posts = []
    
    # 1. Pre-match intel for upcoming Iran matches
    print("\n📅 Checking upcoming matches...")
    matches = get_upcoming_matches()
    print(f"  Found {len(matches)} upcoming Iran matches")
    
    for match in matches:
        key = f"prematch_{match['home']}_{match['away']}_{match['ts']}"
        if any(s.get("name","").startswith(f"prematch_{match['home'].lower().replace(' ','_')}_vs") for s in schedule):
            print(f"  ⏭ {match['home']} vs {match['away']}: already scheduled")
            continue
        
        print(f"\n  Generating: {match['home']} vs {match['away']}")
        post = generate_prematch_post(match)
        if post:
            # Save image temporarily
            img_path = f"/tmp/{post['name']}.jpg"
            with open(img_path,"wb") as f: f.write(post["img_bytes"])
            
            # Upload to S3
            s3key = upload_image_bytes(post["img_bytes"], f"{post['name']}.jpg")
            
            if s3key:
                # Create Instagram container
                container_id = create_ig_container(s3key, post["caption"])
                if container_id:
                    schedule.append({
                        "id": container_id, "ts": post["ts"],
                        "name": post["name"], "type": "prematch"
                    })
                    new_posts.append(post["name"])
                    print(f"  ✅ Scheduled: {post['name']} (container: {container_id})")
                else:
                    print(f"  ❌ Container creation failed")
            else:
                print(f"  ❌ Upload failed")
    
    # 2. Weekly educational post
    print("\n📚 Generating educational post...")
    edu = generate_educational_post()
    edu_key = f"educational_week_{datetime.now().isocalendar()[1]}"
    
    if edu and edu_key not in [s.get("name","") for s in schedule]:
        img_path = f"/tmp/{edu['name']}.jpg"
        with open(img_path,"wb") as f: f.write(edu["img_bytes"])
        
        s3key = upload_image_bytes(edu["img_bytes"], f"{edu['name']}.jpg")
        if s3key:
            container_id = create_ig_container(s3key, edu["caption"])
            if container_id:
                schedule.append({
                    "id": container_id, "ts": edu["ts"],
                    "name": edu_key, "type": "educational"
                })
                new_posts.append(edu_key)
                print(f"  ✅ Educational post scheduled")
    
    save_schedule(schedule)
    
    # Notify via Telegram
    if new_posts and TELEGRAM_TOKEN:
        msg = f"🟠 WEEKLY GENERATOR\n\n✅ {len(new_posts)} nuovi post generati e schedulati:\n"
        for p in new_posts:
            msg += f"  • {p}\n"
        requests.post(f"{TG_BASE}/sendMessage",
            json={"chat_id": NOTIFY_USER, "text": msg, "disable_notification": True},
            timeout=10)
    
    print(f"\n✅ Done. Generated {len(new_posts)} new posts.")

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f: return json.load(f)
    return {}

if __name__ == "__main__":
    main()
