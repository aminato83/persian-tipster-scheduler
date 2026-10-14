"""Small channel publisher. Secrets stay in GitHub; no inbox polling or paid services."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, os, subprocess, urllib.request, urllib.error
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[1]
ALLOWED = {'persiantipster': (-1001403950270, 'tipster_persian'),
           'contropronostico': (-1003584792002, 'controprono')}

class ApiError(Exception):
    def __init__(self, code, retry_after=None):
        self.code, self.retry_after = code, retry_after
        super().__init__(str(code))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

class Telegram:
    def __init__(self, token):
        if not token: raise ApiError('missing_existing_bot_secret')
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)
    def call(self, method, data=None):
        if method not in {'getMe', 'getChat', 'getChatMember', 'getChatMemberCount', 'sendMessage', 'pinChatMessage'}:
            raise ApiError('method_not_allowed')
        req = urllib.request.Request('https://api.telegram.org/bot'+self.token+'/'+method,
            data=json.dumps(data or {}).encode(), headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(req, timeout=25) as r: body = json.load(r)
        except urllib.error.HTTPError as e:
            retry = None
            try: retry = json.load(e).get('parameters',{}).get('retry_after')
            except Exception: pass
            raise ApiError(e.code, retry) from None
        except Exception: raise ApiError('uncertain_network_result') from None
        if not body.get('ok'):
            raise ApiError(body.get('error_code','unexpected_response'),body.get('parameters',{}).get('retry_after'))
        return body.get('result')

class GitStore:
    def __init__(self, root):
        self.root = root
        self.path = root/'marketing/telegram-ledger.json'
        self.path.parent.mkdir(exist_ok=True)
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {'version':1,'actions':{}}
    def persist(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        tmp.replace(self.path)
        for args in [['git','add','marketing/telegram-ledger.json'],
                     ['git','commit','-m','Record Telegram pilot state [skip ci]'],
                     ['git','push','origin','HEAD:main']]:
            p=subprocess.run(args,cwd=self.root,capture_output=True,text=True)
            if p.returncode: raise RuntimeError('state_persistence_failed_'+args[1])

def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def now_iso(now): return now.astimezone(timezone.utc).isoformat()
def action_key(item):
    return '|'.join([item['project_id'],item['id'],str(item['version']),'send_channel_message'])

def validate_config(config):
    assert config['campaign_id']=='pilot_2026_10'
    assert isinstance(config.get('enabled',False),bool)
    assert dt(config['expires_at']) <= dt('2026-10-29T00:00:00Z')
    ids=set()
    for item in config['posts']:
        assert item['project_id'] in ALLOWED
        assert item['id'] not in ids; ids.add(item['id'])
        assert item['kind'] in ['intro','scheduled']
        assert 1 <= len(item['text'].encode('utf-16-le'))//2 <= 4096
        assert item['version']>=1 and item['sources']
        assert dt(item['expires_at']) <= dt(config['expires_at'])
        for row in item.get('buttons',[]):
            for button in row:
                u=urlsplit(button['url'])
                assert u.scheme=='https' and not u.username and not u.password
                assert (u.hostname in {'persiantipster.com','contropronostico.com'} or
                        (u.hostname=='t.me' and u.path in {'/Persian_Tips','/controprono'}) or
                        (u.hostname=='persiantipster.blogabet.com' and u.path=='/pick/49381757/hepco-arak-saipa-tehran'))
                assert set(button)=={'text','url'}

def access(api, project, bot_id):
    expected_id, expected_name=ALLOWED[project]
    chat=api.call('getChat',{'chat_id':expected_id})
    if chat.get('id')!=expected_id or chat.get('type')!='channel' or chat.get('username','').lower()!=expected_name:
        raise ApiError('destination_identity_mismatch')
    member=api.call('getChatMember',{'chat_id':expected_id,'user_id':bot_id})
    if member.get('status') not in ['administrator','creator'] or not member.get('can_post_messages'):
        raise ApiError('channel_publish_permission_missing')
    return chat,member

def publish(config, store, api, mode, now=None):
    now=now or datetime.now(timezone.utc)
    validate_config(config)
    report={'campaign_id':config['campaign_id'],'checked_at':now_iso(now),'mode':mode,'sent':[],'skipped':[],'blocked':[],
            'new_paid_tools':0,'paid_ai_calls':0,'inbox_polling':False}
    if now>=dt(config['expires_at']): report['expired']=True; return report
    bot=api.call('getMe')
    report['bot_username']=bot.get('username')
    if mode=='verify':
        report['channels']=[]
        for project in ALLOWED:
            try:
                chat,member=access(api,project,bot['id'])
                report['channels'].append({'project':project,'can_publish':True,'username':chat['username'],
                    'can_pin':bool(member.get('can_edit_messages')),
                    'member_count_observed':api.call('getChatMemberCount',{'chat_id':chat['id']})})
            except ApiError as e: report['channels'].append({'project':project,'can_publish':False,'error_code':e.code})
        return report
    assert mode in ['publish_due','publish_intro']
    if not config.get('enabled',False):
        report['activation_required']=True
        return report
    for item in config['posts']:
        if item['kind']!=('intro' if mode=='publish_intro' else 'scheduled'): continue
        project=item['project_id']; key=action_key(item)
        if not item.get('publication_ready',False):
            report['skipped'].append({'id':item['id'],'reason':'content_review_required'}); continue
        if not config['enabled_projects'].get(project):
            report['skipped'].append({'id':item['id'],'reason':'project_not_enabled'}); continue
        if now<dt(item['due_at']): continue
        previous=store.state['actions'].get(key)
        if previous and previous['state'] not in ['retryable']:
            report['skipped'].append({'id':item['id'],'reason':previous['state']}); continue
        if previous and previous.get('next_attempt_at') and now<dt(previous['next_attempt_at']): continue
        if now>=dt(item['expires_at']):
            report['skipped'].append({'id':item['id'],'reason':'message_expired'}); continue
        try: chat,member=access(api,project,bot['id'])
        except ApiError as e:
            report['blocked'].append({'id':item['id'],'error_code':e.code}); continue
        attempts=(previous or {}).get('attempts',0)+1
        if attempts>3:
            report['blocked'].append({'id':item['id'],'error_code':'attempt_limit'}); continue
        record={'state':'processing','attempts':attempts,'claimed_at':now_iso(now),'chat_id':chat['id']}
        store.state['actions'][key]=record
        store.persist() # Claim is durable before the API can send anything.
        payload={'chat_id':chat['id'],'text':item['text'],'disable_notification':True,
                 'allow_paid_broadcast':False,'link_preview_options':{'is_disabled':True}}
        if item.get('buttons'): payload['reply_markup']={'inline_keyboard':item['buttons']}
        try:
            message=api.call('sendMessage',payload)
            if message.get('chat',{}).get('id')!=chat['id'] or message.get('text')!=item['text'] or not message.get('message_id'):
                raise ApiError('uncertain_delivery_confirmation')
            record.update(state='confirmed',message_id=message['message_id'],confirmed_at=now_iso(now),
                          public_url='https://t.me/'+chat['username']+'/'+str(message['message_id']))
        except ApiError as e:
            record['error_code']=e.code
            if e.code==429:
                record.update(state='retryable',next_attempt_at=now_iso(now+timedelta(seconds=max(60,e.retry_after or 60))))
            elif isinstance(e.code,int) and 400<=e.code<500: record['state']='failed'
            else: record['state']='uncertain'
            store.persist()
            report['blocked'].append({'id':item['id'],'error_code':e.code,'state':record['state']}); continue
        store.persist() # A failure here leaves the remote durable claim; never resend blindly.
        if item.get('pin') and member.get('can_edit_messages'):
            try:
                api.call('pinChatMessage',{'chat_id':chat['id'],'message_id':record['message_id'],'disable_notification':True})
                record['pin_state']='confirmed'
            except ApiError as e: record['pin_state']='requires_review'; record['pin_error_code']=e.code
            store.persist()
        report['sent'].append({'id':item['id'],'project':project,'public_url':record['public_url'],
                               'pin_state':record.get('pin_state')})
    return report

def main():
    config=json.loads((BASE/'marketing/telegram-pilot.json').read_text(encoding='utf-8'))
    mode=os.environ.get('MARKETING_MODE','verify')
    store=GitStore(BASE)
    api=Telegram(os.environ.get('TELEGRAM_BOT_TOKEN',''))
    try: report=publish(config,store,api,mode)
    except Exception as e:
        report={'mode':mode,'error':str(e) if isinstance(e,ApiError) else type(e).__name__,
                'messages_may_require_reconciliation':True}
    path=BASE/'telegram-pilot-report.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as f:
            f.write('## Telegram pilot\n\n```json\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n```\n')
    if report.get('error') or report.get('blocked'): raise SystemExit(2)

if __name__=='__main__': main()
