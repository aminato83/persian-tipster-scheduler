import json, os, urllib.request, urllib.error
from pathlib import Path

token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
report = {"mode": "read_only", "messages_sent": 0, "channels": []}

def call(method, payload=None):
    if method not in {"getMe", "getChat", "getChatMember", "getChatMemberCount"}:
        raise RuntimeError("read_only_method_required")
    req = urllib.request.Request("https://api.telegram.org/bot" + token + "/" + method,
        data=json.dumps(payload or {}).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        return {"ok": False, "error_code": e.code}
    except Exception:
        return {"ok": False, "error_code": "network_error"}
    return data

if not token:
    report["error"] = "existing_bot_secret_missing"
else:
    me = call("getMe")
    if not me.get("ok"):
        report["error"] = "bot_unavailable"
        report["error_code"] = me.get("error_code")
    else:
        bot = me["result"]
        report["bot_username"] = bot.get("username")
        for handle in ["@tipster_persian", "@controprono"]:
            row = {"handle": handle}
            chat = call("getChat", {"chat_id": handle})
            if not chat.get("ok"):
                row["error_code"] = chat.get("error_code")
                row["admin_verified"] = False
            else:
                c = chat["result"]
                row.update(chat_id=c["id"], type=c["type"], username=c.get("username"), title=c.get("title"))
                member = call("getChatMember", {"chat_id": c["id"], "user_id": bot["id"]})
                m = member.get("result", {})
                row.update(status=m.get("status"), admin_verified=m.get("status") in ["creator", "administrator"],
                    can_post_messages=bool(m.get("can_post_messages")), can_edit_messages=bool(m.get("can_edit_messages")))
                if not member.get("ok"): row["membership_error_code"] = member.get("error_code")
                count = call("getChatMemberCount", {"chat_id": c["id"]})
                if count.get("ok"): row["member_count_observed"] = count["result"]
            report["channels"].append(row)
Path("telegram-access-report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
