"""
Persian Tipster — Telegram Scanner
Scansiona VIP e FREE channel ogni ora.
Scarica nuovi video, li processa come Reels brandizzati, li pubblica su Instagram.
"""
import os, json, requests, subprocess, time, base64
from datetime import datetime, timezone

BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
COMPOSIO_KEY = os.environ["COMPOSIO_API_KEY"]
OPENAI_KEY  = os.environ.get("OPENAI_API_KEY","")
GH_TOKEN    = os.environ.get("GITHUB_TOKEN","")
GH_REPO     = os.environ.get("GITHUB_REPOSITORY","")  # "user/repo"

VIP_CHANNEL  = -1003320798147
FREE_CHANNEL = -1001403950270
NOTIFY_USER  = 899950945
IG_ACCOUNT   = "instagram_mease-bitter"

SCAN_FILE      = "scan_state.json"
PUBLISHED_FILE = "published.json"
MAX_REELS_PER_RUN = 2   # max Reels da pubblicare per run (per non fare spam)
MAX_FILE_SIZE_MB  = 19  # Telegram Bot API limit

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

CAPTIONS = {
    "goal": "🔥 {label}\n\nIranian football. This is what inside knowledge looks like.\n\nEvery match. Every detail. Documented on Blogabet.\n\n📲 Free channel → link in bio\n📊 persiantipster.blogabet.com\n\n#iranianfootball #footballbetting #valuebetting #persiantipster #bettingtips #sportsbetting",
    "win":  "✅ ANOTHER WIN\n\n+31% yield over 756 picks. All verified.\n\n📲 Free daily tips → link in bio\n📊 persiantipster.blogabet.com\n\n#bettingtips #winningbets #persiantipster #valuebetting #sportsbetting #verified",
}

def load_state():
    if os.path.exists(SCAN_FILE):
        with open(SCAN_FILE) as f: return json.load(f)
    return {"vip_last_id": 0, "free_last_id": 0, "processed": []}

def save_state(state):
    with open(SCAN_FILE,"w") as f: json.dump(state, f, indent=2)

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        with open(PUBLISHED_FILE) as f: return json.load(f)
    return {}

def save_published(data):
    with open(PUBLISHED_FILE,"w") as f: json.dump(data, f, indent=2)

def tg_forward(chat_id, from_id, msg_id):
    r = requests.post(f"{TG}/forwardMessage",
        json={"chat_id": chat_id, "from_chat_id": from_id,
              "message_id": msg_id, "disable_notification": True},
        timeout=10)
    return r.json()

def get_file_url(file_id):
    r = requests.get(f"{TG}/getFile", params={"file_id": file_id}, timeout=10)
    fp = r.json().get("result", {}).get("file_path")
    if fp: return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    return None

def download_video(url, path):
    r = requests.get(url, timeout=60, stream=True)
    with open(path,"wb") as f:
        for chunk in r.iter_content(65536): f.write(chunk)
    return os.path.getsize(path)

def process_reel(raw_path, out_path):
    """Convert to 9:16 vertical with Persian Tipster branding"""
    vf = (
        "scale=1080:-2,"
        "pad=1080:1920:0:(oh-ih)/2:black,"
        "drawbox=x=0:y=0:w=1080:h=165:color=black@0.88:t=fill,"
        "drawbox=x=0:y=1755:w=1080:h=165:color=black@0.88:t=fill,"
        f"drawtext=text='PERSIAN TIPSTER':fontcolor=#FFD700:fontsize=55:"
        f"x=(w-text_w)/2:y=22:fontfile={FONT_BOLD},"
        f"drawtext=text='Iranian Sports Picks':fontcolor=#CCCCCC:fontsize=38:"
        f"x=(w-text_w)/2:y=90:fontfile={FONT_REG},"
        f"drawtext=text='@persiantipster':fontcolor=#FFD700:fontsize=50:"
        f"x=(w-text_w)/2:y=1770:fontfile={FONT_BOLD},"
        f"drawtext=text='Free daily tips - link in bio':fontcolor=white:fontsize=34:"
        f"x=(w-text_w)/2:y=1835:fontfile={FONT_REG}"
    )
    cmd = ["ffmpeg","-y","-err_detect","ignore_err","-i",raw_path,
           "-vf",vf,"-c:v","libx264","-crf","24","-preset","fast",
           "-c:a","aac","-b:a","128k","-ar","44100",
           "-movflags","+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 50000

def upload_to_github_releases(filepath, filename):
    """Upload file to GitHub release and return public URL"""
    if not GH_TOKEN or not GH_REPO: return None
    
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # Get or create release
    rel_url = f"https://api.github.com/repos/{GH_REPO}/releases/tags/media-assets"
    r = requests.get(rel_url, headers=headers, timeout=10)
    
    if r.status_code == 404:
        # Create release
        r2 = requests.post(f"https://api.github.com/repos/{GH_REPO}/releases",
            headers=headers,
            json={"tag_name": "media-assets", "name": "Media Assets",
                  "body": "Auto-uploaded media files", "draft": False, "prerelease": True},
            timeout=10)
        release = r2.json()
    else:
        release = r.json()
    
    release_id = release.get("id")
    if not release_id: return None
    
    # Delete existing asset with same name if exists
    assets = requests.get(f"https://api.github.com/repos/{GH_REPO}/releases/{release_id}/assets",
                         headers=headers, timeout=10).json()
    for asset in assets:
        if asset.get("name") == filename:
            requests.delete(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{asset['id']}",
                          headers=headers, timeout=10)
    
    # Upload
    upload_url = f"https://uploads.github.com/repos/{GH_REPO}/releases/{release_id}/assets?name={filename}"
    with open(filepath,"rb") as f:
        up = requests.post(upload_url,
            headers={**headers, "Content-Type": "video/mp4"},
            data=f, timeout=120)
    
    if up.status_code in [200,201]:
        owner, repo = GH_REPO.split("/")
        return f"https://github.com/{owner}/{repo}/releases/download/media-assets/{filename}"
    return None

def post_reel_via_composio(video_url, caption):
    """Create and publish Instagram Reel via Composio API"""
    composio_headers = {"x-api-key": COMPOSIO_KEY, "Content-Type": "application/json"}
    
    # Create container
    r1 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA/execute",
        headers=composio_headers,
        json={"input": {"ig_user_id": "me", "media_type": "REELS",
                        "video_url": video_url, "caption": caption},
              "connectedAccountId": IG_ACCOUNT},
        timeout=30)
    
    d1 = r1.json()
    container_id = d1.get("data", {}).get("id")
    if not container_id:
        print(f"  ❌ Container creation failed: {d1}")
        return None
    
    print(f"  Container: {container_id} — waiting 30s...")
    time.sleep(30)
    
    # Publish
    r2 = requests.post(
        "https://backend.composio.dev/api/v2/actions/INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH/execute",
        headers=composio_headers,
        json={"input": {"ig_user_id": "me", "creation_id": container_id,
                        "max_wait_seconds": 90},
              "connectedAccountId": IG_ACCOUNT},
        timeout=120)
    
    d2 = r2.json()
    post_id = d2.get("data", {}).get("id")
    return post_id

def notify_telegram(message):
    requests.post(f"{TG}/sendMessage",
        json={"chat_id": NOTIFY_USER, "text": message, "disable_notification": True},
        timeout=10)

def scan_channel(chat_id, channel_name, last_id, state, published, reels_published):
    """Scan channel for new videos starting from last_id+1"""
    print(f"\n📡 Scanning {channel_name} from msg {last_id+1}...")
    found_videos = []
    
    # Scan next 50 messages
    for msg_id in range(last_id + 1, last_id + 51):
        if reels_published >= MAX_REELS_PER_RUN:
            break
            
        res = tg_forward(NOTIFY_USER, chat_id, msg_id)
        if not res.get("ok"):
            err = res.get("description","")
            if "not found" in err.lower():
                continue  # message doesn't exist, keep going
            elif "too many" in err.lower():
                time.sleep(3)
                continue
            continue
        
        msg = res["result"]
        
        if msg.get("video"):
            v = msg["video"]
            size_mb = v.get("file_size", 0) / 1024 / 1024
            duration = v.get("duration", 0)
            file_id = v["file_id"]
            caption = msg.get("caption", "")
            
            key = f"{channel_name}_{msg_id}"
            
            if key in state.get("processed", []):
                print(f"  ⏭ {channel_name} MSG{msg_id}: already processed")
                continue
                
            if size_mb > MAX_FILE_SIZE_MB:
                print(f"  ⚠️ {channel_name} MSG{msg_id}: {size_mb:.1f}MB too large, skipping")
                state["processed"].append(key)
                continue
            
            print(f"  🎥 {channel_name} MSG{msg_id}: {duration}s {size_mb:.1f}MB")
            found_videos.append({
                "key": key, "file_id": file_id, "duration": duration,
                "size_mb": size_mb, "caption": caption, "msg_id": msg_id,
                "channel": channel_name
            })
        
        # Update last_id as we go
        if msg_id > last_id:
            if channel_name == "VIP":
                state["vip_last_id"] = msg_id
            else:
                state["free_last_id"] = msg_id
        
        time.sleep(0.3)  # rate limit
    
    # Process found videos
    for video in found_videos:
        if reels_published >= MAX_REELS_PER_RUN:
            print(f"  ⏸ Max reels per run reached, queuing for next hour")
            break
        
        print(f"\n  Processing {video['key']}...")
        
        try:
            # Download
            dl_url = get_file_url(video["file_id"])
            if not dl_url:
                print(f"  ❌ Could not get file URL")
                state["processed"].append(video["key"])
                continue
            
            raw_path = f"/tmp/raw_{video['msg_id']}.mp4"
            out_path = f"/tmp/reel_{video['msg_id']}.mp4"
            
            size = download_video(dl_url, raw_path)
            print(f"  ✅ Downloaded: {size//1024}KB")
            
            # Process with ffmpeg
            if not process_reel(raw_path, out_path):
                print(f"  ❌ ffmpeg failed")
                state["processed"].append(video["key"])
                continue
            
            out_size = os.path.getsize(out_path)
            print(f"  ✅ Processed: {out_size//1024}KB")
            
            # Upload to GitHub Releases for public URL
            filename = f"reel_{video['channel']}_{video['msg_id']}.mp4"
            video_url = upload_to_github_releases(out_path, filename)
            
            if not video_url:
                print(f"  ❌ Upload failed")
                state["processed"].append(video["key"])
                continue
            
            print(f"  ✅ Public URL ready")
            
            # Generate caption with OpenAI or use template
            cap_type = "win" if any(w in video["caption"].lower() for w in ["won","win","goal","score","✅"]) else "goal"
            label = video["caption"][:50] if video["caption"] else f"Iranian Football — {video['channel']}"
            caption = CAPTIONS[cap_type].format(label=label)
            
            # Post to Instagram
            print(f"  📱 Publishing Reel...")
            post_id = post_reel_via_composio(video_url, caption)
            
            if post_id:
                published[video["key"]] = {
                    "type": "reel", "channel": video["channel"],
                    "msg_id": video["msg_id"], "post_id": post_id,
                    "published_at": datetime.now(timezone.utc).isoformat()
                }
                save_published(published)
                state["processed"].append(video["key"])
                reels_published += 1
                
                notify_telegram(
                    f"🎬 REEL PUBBLICATO!\n"
                    f"📹 {video['channel']} MSG{video['msg_id']}\n"
                    f"⏱ {video['duration']}s\n"
                    f"📸 Instagram ID: {post_id}"
                )
                print(f"  ✅ Published! ID: {post_id}")
            else:
                print(f"  ❌ Publishing failed")
                state["processed"].append(video["key"])
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            state["processed"].append(video["key"])
        
        finally:
            # Cleanup
            for p in [raw_path, out_path]:
                if os.path.exists(p): os.remove(p)
        
        time.sleep(5)  # small pause between reels
    
    return reels_published

def main():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] Telegram Scanner starting...")
    
    state = load_state()
    published = load_published()
    reels_published = 0
    
    # Scan VIP channel
    reels_published = scan_channel(
        VIP_CHANNEL, "VIP",
        state.get("vip_last_id", 0),
        state, published, reels_published
    )
    
    # Scan FREE channel  
    if reels_published < MAX_REELS_PER_RUN:
        reels_published = scan_channel(
            FREE_CHANNEL, "FREE",
            state.get("free_last_id", 0),
            state, published, reels_published
        )
    
    save_state(state)
    print(f"\n✅ Done. Published {reels_published} Reels this run.")

if __name__ == "__main__":
    main()
