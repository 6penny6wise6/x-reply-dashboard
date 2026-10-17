import json, html, urllib.parse as u, datetime, zoneinfo
d=json.load(open('dashboard.json'))
now=datetime.datetime.now(zoneinfo.ZoneInfo('America/Chicago')).strftime('%a %b %-d, %-I:%M %p CT')
d['updated']=now; json.dump(d,open('dashboard.json','w'),ensure_ascii=False,indent=1)
secs=sorted(d['sections'],key=lambda s:(-len(s['replies']),-s.get('stats',{}).get('views',0)))
total=sum(len(s['replies']) for s in secs)
E=html.escape
def fmt(n): return f"{n/1000:.1f}K" if n>=1000 else str(n)
SJS=r'''<script>
var SS=__SS__;
function fmt(t){return new Date(t).toLocaleTimeString("en-US",{timeZone:"America/Chicago",hour:"numeric",minute:"2-digit"})+" CT"}
function scanSt(){var el=document.getElementById("scanst");if(!el)return;
 var base=SS&&SS.state=="running"?"⏳ Scan running since "+fmt(SS.started_ms):SS&&SS.state=="done"?"✅ Last scan finished "+fmt(SS.finished_ms)+(SS.note?" ("+SS.note+")":""):SS&&SS.state=="error"?"⚠️ Last scan failed "+fmt(SS.finished_ms)+(SS.note?": "+SS.note:""):"";
 fetch("https://api.github.com/repos/6penny6wise6/x-reply-dashboard/actions/workflows/scan-now.yml/runs?per_page=1").then(function(r){return r.json()}).then(function(j){var w=j.workflow_runs&&j.workflow_runs[0],t="";
  if(w){var ts=Date.parse(w.created_at);if(w.status!="completed")t="⏳ Scan request sending ("+fmt(ts)+")";else if(w.conclusion=="success"){if(!SS||!SS.started_ms||SS.started_ms<ts-60000)t="⏳ Scan requested "+fmt(ts)+", running now (results in a few min)"}else t="⚠️ Scan request failed "+fmt(ts)}
  el.textContent=t||base||"Tap Scan now, then Run workflow on GitHub"}).catch(function(){el.textContent=base||"Tap Scan now, then Run workflow on GitHub"})}
scanSt();setInterval(scanSt,20000);</script>'''
JS=r'''<script>
var BUILT=__BUILT__,RIDDLE=__RIDDLE__;
function ct(){var p={};new Intl.DateTimeFormat("en-US",{timeZone:"America/Chicago",hour12:false,hour:"2-digit",minute:"2-digit",second:"2-digit"}).formatToParts(new Date()).forEach(function(x){p[x.type]=+x.value});return {h:p.hour%24,m:p.minute,s:p.second}}
function hms(x){var h=Math.floor(x/3600),m=Math.floor(x%3600/60),s=x%60;return (h?h+":"+(m<10?"0":""):"")+m+":"+(s<10?"0":"")+s}
function ago(t){if(!t)return "";return " · last updated "+hms(Math.max(0,Math.floor((Date.now()-t)/1000)))+" ago"}
function until(now,h){var t=h*3600-now;if(t<=0)t+=86400;return t}
function tick(){var c=ct(),now=c.h*3600+c.m*60+c.s,r,q;
 if(c.h<8||now>=22*3600+55*60)r="💬 Next reply check in "+hms(until(now,8))+" (8 AM CT)";else{var n=Math.ceil((now+1)/300)*300;r="💬 Next reply check in "+hms(n-now)}
 if(c.h<7||now>=22*3600)q="🎯 Next riddle scan in "+hms(until(now,7))+" (7 AM CT)";else{q="🎯 Next riddle scan in ~"+hms((c.h+1)*3600-now)}
 document.getElementById("cd2").textContent=r+ago(BUILT);document.getElementById("cd1").textContent=q+ago(RIDDLE)}
tick();setInterval(tick,1000);</script>'''
out=[f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="120"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><script>(function(){{var u=new URL(location.href);var r=+u.searchParams.get("r")||0;if(Date.now()-r>60000){{u.searchParams.set("r",Date.now());location.replace(u.toString());}}}})();</script><style>.cd{{background:#16181c;border:1px solid #2f3336;border-radius:10px;padding:8px 12px;margin:8px 0;font-size:14px;color:#71767b}}</style><title>Reply Dashboard ({total})</title>
<style>body{{font-family:-apple-system,system-ui;background:#0f1419;color:#e7e9ea;padding:16px;max-width:640px;margin:auto}}
h1{{font-size:22px;margin-bottom:4px}}details{{background:#16202a;border-radius:14px;margin:12px 0;overflow:hidden}}
summary{{list-style:none;padding:14px;cursor:pointer}}summary::-webkit-details-marker{{display:none}}
.t{{display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:17px}}
.t:before{{content:"▸";margin-right:8px;color:#8b98a5}}details[open] .t:before{{content:"▾"}}.tt{{flex:1}}
.b{{background:#1d9bf0;border-radius:99px;padding:2px 10px;font-size:14px;color:#fff}}.z{{background:#2f3336}}
.st{{color:#8b98a5;font-size:13px;margin:4px 0 0 18px}}a{{color:#1d9bf0;text-decoration:none}}
.in{{padding:0 14px 12px}}.r{{border-top:1px solid #2f3336;padding:10px 0}}.q{{color:#8b98a5;font-size:14px}}
.d{{font-size:15px;margin:6px 0}}.btn{{display:block;text-align:center;background:#1d9bf0;color:#fff;border-radius:99px;padding:10px;font-weight:600}}
.tabs{{display:flex;gap:8px;margin:12px 0;position:sticky;top:0;background:#0f1419;padding:6px 0;z-index:5}}.tabs button{{flex:1;background:#16202a;color:#e7e9ea;border:0;border-radius:12px;padding:10px;font-size:15px;font-weight:600}}.tabs button.on{{background:#1d9bf0}}.ctl{{margin:8px 0}}.ctl button{{background:#2f3336;color:#e7e9ea;border:0;border-radius:99px;padding:6px 12px;margin-right:6px}}</style></head><body>
<h1>Reply Dashboard <span class="b">{total} to reply</span></h1><div class="q">🔎 Last scanned X: <b>{E(d.get('last_scanned') or now)}</b> · page built {now}</div><button onclick="location.href=location.pathname+'?r='+Date.now()" style="width:100%;margin:10px 0 0;background:#00ba7c;color:#fff;border:0;border-radius:99px;padding:10px;font-size:16px;font-weight:600">🔄 Refresh</button>
<div class="ctl"><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">Expand all</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">Collapse all</button></div>''']
opps=d.get('opportunities',[])
nrep=total
out.append(f'<div class="tabs"><button id="b1" onclick="tab(1)">🎯 New posts <span class="b{" z" if not opps else ""}">{len(opps)}</span></button><button id="b2" onclick="tab(2)">💬 Replies &amp; likes <span class="b{" z" if not nrep else ""}">{nrep}</span></button></div><div id="t1"><div class="cd" id="cd1">⏱️ …</div><a target="_blank" rel="noopener" class="btn" style="display:block;text-align:center;background:#1d9bf0;margin:6px 0" href="https://github.com/6penny6wise6/x-reply-dashboard/actions/workflows/scan-now.yml">🔍 Scan now</a><div class="cd" id="scanst">Scan status: checking…</div>')
out.append(f'<h2 style="font-size:18px;margin:18px 0 4px">🎯 New posts to answer <span class="b{" z" if not opps else ""}">{len(opps)}</span></h2><div class="q">Save the image (press and hold, then Save to Photos), tap Post reply, then attach it.</div>')
for o in opps:
    st=o['stats']; link='https://x.com/intent/post?in_reply_to='+o['id']+'&text='+u.quote(o['caption'],safe='')
    nt=f'<div class="q" style="color:#ffad1f">⚠️ {E(o["note"])}</div>' if o.get('note') else ''
    out.append(f'<details><summary><div class="t"><span class="tt">{E(o["title"])}</span><span class="b">new</span></div><div class="st">@{E(o["author"])} · 👁 {fmt(st["views"])} · ❤️ {st["likes"]} · 💬 {st["replies"]}</div></summary><div class="in"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{o["author"]}/status/{o["id"]}">Open original post ↗</a></div><div class="d"><b>Q:</b> {E(o["question"])}<br><b>A:</b> {E(o["answer"])}</div>{nt}<img src="{o["image"]}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0"><div class="d">{E(o["caption"])}</div><a target="_blank" rel="noopener" class="btn" href="{link}">Post reply to @{E(o["author"])}</a></div></details>')
if not opps: out.append('<div class="q">Nothing new right now. The next scan runs within the hour, or tap Scan now.</div>')
out.append('</div><div id="t2" style="display:none"><div class="cd" id="cd2">⏱️ …</div>')
allr=[dict(r,thread=s['title']) for s in secs for r in s['replies']]
allr.sort(key=lambda r:-(r.get('views') or 0))
bs=[allr[i:i+8] for i in range(0,len(allr),8)]
if bs:
    out.append('<h2 style="font-size:17px;margin:14px 0 6px">✅ Batch approval</h2><div class="q">Top-viewed comments first. Untick Drop on anything you don\'t want, then tap Approve all and paste the copied message into approver1 bot\'s chat. Nothing posts from this page.</div>')
for bi,b in enumerate(bs,1):
    out.append(f'<details class="batch"{" open" if bi==1 else ""}><summary><div class="t"><span class="tt">Batch {bi} of {len(bs)}</span><span class="b">{len(b)}</span></div></summary><div class="in" id="batch{bi}">')
    for r in b:
        out.append(f'<div class="r bi" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"])}"><div class="q">{E(r["thread"])} · 👁 {fmt(r.get("views") or 0)}</div><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{r["handle"]}/status/{r["id"]}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div><div class="d">{E(r["draft"])}</div><label style="display:flex;gap:8px;align-items:center;font-size:15px"><input type="checkbox" class="drop" onchange="this.closest(\'.bi\').style.opacity=this.checked?.4:1"> Drop</label></div>')
    out.append(f'<button class="btn" style="width:100%;background:#00ba7c;border:0;font-size:17px;padding:12px" onclick="approve({bi},{len(bs)})">✅ Approve all (batch {bi})</button><div class="q" id="ok{bi}"></div></div></details>')
if bs: out.append('<h2 style="font-size:17px;margin:18px 0 6px">✋ Manual (Like / Reply links)</h2>')
out.append("""<script>function approve(n,t){var items=[].slice.call(document.querySelectorAll('#batch'+n+' .bi')).filter(function(e){return !e.querySelector('.drop').checked});
var dropped=document.querySelectorAll('#batch'+n+' .drop:checked').length;
var msg='APPROVE batch '+n+' of '+t+' ('+items.length+' replies + likes'+(dropped?', '+dropped+' dropped':'')+')\\n'+items.map(function(e,i){return (i+1)+'. reply_to '+e.dataset.id+' (@'+e.dataset.h+'): '+e.dataset.d}).join('\\n');
var ok=document.getElementById('ok'+n);function done(){ok.textContent='Copied, paste it into approver1 bot\\'s chat'}
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(msg).then(done,fb)}else fb();
function fb(){var ta=document.createElement('textarea');ta.value=msg;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');done()}catch(e){ok.textContent='Copy failed, select and copy this:';var p=document.createElement('pre');p.style.whiteSpace='pre-wrap';p.textContent=msg;ok.appendChild(p)}document.body.removeChild(ta)}}</script>""")
for s in secs:
    n=len(s['replies']); st=s.get('stats')
    sl=f'<div class="st">👁 {fmt(st["views"])} views · ❤️ {st["likes"]} · 💬 {st["replies"]} replies</div>' if st else ''
    out.append(f'<details><summary><div class="t"><span class="tt">{E(s["title"])}</span><span class="b{" z" if n==0 else ""}">{n if n else "✓"}</span></div>{sl}</summary><div class="in"><div class="q"><a target="_blank" rel="noopener" href="{s["my_comment"]}">Open my comment ↗</a></div>')
    for r in s['replies']:
        link='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'],safe='')
        out.append(f'<div class="r"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{r["handle"]}/status/{r["id"]}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div><div class="d">{E(r["draft"])}</div><div style="display:flex;gap:8px"><a target="_blank" rel="noopener" class="btn" style="flex:0 0 30%;background:#f91880" href="https://x.com/intent/like?tweet_id={r["id"]}">❤️ Like</a><a target="_blank" rel="noopener" class="btn" style="flex:1" href="{link}">Reply to @{E(r["handle"])}</a></div></div>')
    if n==0: out.append('<div class="q" style="padding-top:8px">All caught up ✅</div>')
    out.append('</div></details>')
out.append(SJS.replace('__SS__',json.dumps(d.get('scan_status'))))
out.append(JS.replace('__BUILT__',str(int(__import__('time').time()*1000))).replace('__RIDDLE__',str(d.get('last_riddle_scan_ms') or 0)))
out.append('</div><script>function tab(n){for(const i of [1,2]){document.getElementById("t"+i).style.display=i==n?"":"none";document.getElementById("b"+i).className=i==n?"on":""}localStorage.tab=n}tab(+(localStorage.tab||1))</script></body></html>')
import seal; seal.publish('\n'.join(out))  # encrypted publish; never write plaintext index.html
print(total)
