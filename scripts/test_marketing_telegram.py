import unittest
from datetime import datetime,timezone
from copy import deepcopy
from marketing_telegram import publish, ApiError, ALLOWED

NOW=datetime(2026,10,14,12,0,tzinfo=timezone.utc)
def config():
 return {'campaign_id':'pilot_2026_10','enabled':True,'expires_at':'2026-10-28T23:59:00Z',
  'enabled_projects':{'persiantipster':True,'contropronostico':False},'posts':[
   {'project_id':'persiantipster','id':'pt_intro','version':1,'kind':'intro','text':'VIP: 30 days.',
    'sources':['owner'],'due_at':'2026-10-14T00:00:00Z','expires_at':'2026-10-28T23:59:00Z','pin':True}]}
class Store:
 def __init__(self): self.state={'actions':{}}; self.snapshots=[]; self.fail=False
 def persist(self):
  if self.fail: raise RuntimeError('persistence_failed')
  self.snapshots.append(deepcopy(self.state))
class Api:
 def __init__(self,store): self.store=store; self.sent=0; self.error=None; self.admin=True; self.wrong=False; self.payloads=[]
 def call(self,method,payload=None):
  if method=='getMe': return {'id':123,'username':'TestBot'}
  if method=='getChat': return {'id':1 if self.wrong else ALLOWED['persiantipster'][0],'type':'channel','username':'tipster_persian'}
  if method=='getChatMember': return {'status':'administrator' if self.admin else 'member','can_post_messages':self.admin,'can_edit_messages':True}
  if method=='sendMessage':
   assert self.store.snapshots[-1]['actions']['persiantipster|pt_intro|1|send_channel_message']['state']=='processing'
   self.sent+=1
   self.payloads.append(payload)
   if self.error: raise self.error
   return {'chat':{'id':ALLOWED['persiantipster'][0]},'message_id':99,'text':payload['text']}
  if method=='pinChatMessage': return True
  if method=='getChatMemberCount': return 12
class Tests(unittest.TestCase):
 def setUp(self): self.c=config();self.s=Store();self.a=Api(self.s)
 def run_publish(self): return publish(self.c,self.s,self.a,'publish_intro',NOW)
 def test_success_and_duplicate(self):
  self.assertEqual(len(self.run_publish()['sent']),1);self.run_publish();self.assertEqual(self.a.sent,1)
 def test_timeout_is_not_retried(self):
  self.a.error=ApiError('uncertain_network_result');self.run_publish();self.a.error=None;self.run_publish();self.assertEqual(self.a.sent,1)
 def test_persist_failure_prevents_send(self):
  self.s.fail=True
  with self.assertRaises(RuntimeError):self.run_publish()
  self.assertEqual(self.a.sent,0)
 def test_wrong_channel_prevents_send(self):
  self.a.wrong=True;self.run_publish();self.assertEqual(self.a.sent,0)
 def test_permission_loss_prevents_send(self):
  self.a.admin=False;self.run_publish();self.assertEqual(self.a.sent,0)
 def test_claim_after_restart_prevents_send(self):
  self.s.state['actions']['persiantipster|pt_intro|1|send_channel_message']={'state':'processing'}
  self.run_publish();self.assertEqual(self.a.sent,0)
 def test_disabled_project_prevents_send(self):
  self.c['enabled_projects']['persiantipster']=False;self.run_publish();self.assertEqual(self.a.sent,0)
 def test_activation_required_prevents_send(self):
  self.c['enabled']=False;self.run_publish();self.assertEqual(self.a.sent,0)
 def test_expired_message_prevents_send(self):
  self.c['posts'][0]['expires_at']='2026-10-14T11:00:00Z';self.run_publish();self.assertEqual(self.a.sent,0)
 def test_rate_limit_is_delayed(self):
  self.a.error=ApiError(429,120);self.run_publish();self.a.error=None;self.run_publish();self.assertEqual(self.a.sent,1)
 def test_paid_broadcast_never_enabled(self):
  self.run_publish();self.assertIs(self.a.payloads[0]['allow_paid_broadcast'],False)
 def test_unapproved_destination_link_prevents_send(self):
  self.c['posts'][0]['buttons']=[[{'text':'VIP','url':'https://t.me.evil.example/Persian_Tips'}]]
  with self.assertRaises(AssertionError):self.run_publish()
  self.assertEqual(self.a.sent,0)
if __name__=='__main__':unittest.main()
