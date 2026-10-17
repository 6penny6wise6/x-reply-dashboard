import json, html, urllib.parse as u, datetime, zoneinfo, re, time
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
# Manual mode: localStorage done flags + posted status IDs + last-selected
MAN=r'''<script>
function _lsGet(k,fb){try{var v=localStorage.getItem(k);return v?JSON.parse(v):fb}catch(e){return fb}}
function _lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function isDone(kind,id){var m=_lsGet("xdash_done",{});return !!m[kind+":"+id]}
function setDone(kind,id,on){var m=_lsGet("xdash_done",{});if(on)m[kind+":"+id]=1;else delete m[kind+":"+id];_lsSet("xdash_done",m)}
function getPosted(id){var m=_lsGet("xdash_posted",{});return m[id]||""}
function setPosted(id,sid){var m=_lsGet("xdash_posted",{});if(sid)m[id]=sid;else delete m[id];_lsSet("xdash_posted",m)}
function applyDone(el,on){if(!el)return;el.classList.toggle("done",!!on);var cb=el.querySelector(".mdone");if(cb)cb.checked=!!on}
function markDone(cb,kind){var el=cb.closest(kind==="r"?".bi":".pc");var id=el&&el.dataset.id;if(!id)return;setDone(kind,id,cb.checked);applyDone(el,cb.checked);if(kind==="r"){var b=el.closest(".batch");if(b)updProg(b)}rememberFrom(el)}
function updProg(batch){var items=batch.querySelectorAll(".bi"),done=0;items.forEach(function(e){if(isDone("r",e.dataset.id))done++});var el=batch.querySelector(".prog");if(el)el.textContent=done+" of "+items.length+" done"}
function parseStatusId(v){if(!v)return "";v=(""+v).trim();var m=v.match(/(?:status\/|statuses\/|=)(\d{5,})/);if(m)return m[1];if(/^\d{5,}$/.test(v))return v;return ""}
function savePosted(inp){var c=inp.closest(".pc"),id=c.dataset.id,sid=parseStatusId(inp.value);inp.value=sid;setPosted(id,sid);showAns(c,sid);rememberFrom(c)}
function showAns(c,sid){var wrap=c.querySelector(".answrap");if(!wrap)return;if(sid){wrap.style.display="";var a=wrap.querySelector("a.ansbtn");if(a){var ans=(c.dataset.ans||"").trim();a.href="https://x.com/intent/post?in_reply_to="+encodeURIComponent(sid)+"&text="+encodeURIComponent(ans)}}else wrap.style.display="none"}
function copyText(b){var c=b.closest(".pc"),t=(c.dataset.t||"").trim(),ok=c.querySelector(".pok");rememberFrom(c);
 function done(){ok.textContent="Copied ✓"}
 function fb(){var ta=document.createElement("textarea");ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");done()}catch(e){ok.textContent="Copy failed, select the post text above"}document.body.removeChild(ta)}
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(done,fb);else fb()}
function approve(n,t){var items=[].slice.call(document.querySelectorAll("#batch"+n+" .bi")).filter(function(e){return !e.querySelector(".drop").checked});
 var dropped=document.querySelectorAll("#batch"+n+" .drop:checked").length;
 var msg="APPROVE batch "+n+" of "+t+" ("+items.length+" replies + likes"+(dropped?", "+dropped+" dropped":"")+")\n"+items.map(function(e,i){return (i+1)+". reply_to "+e.dataset.id+" (@"+e.dataset.h+"): "+e.dataset.d.trim()}).join("\n");
 var ok=document.getElementById("ok"+n);function done(){ok.textContent="Copied, paste it into approver1 bot's chat"}
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(msg).then(done,fb)}else fb();
 function fb(){var ta=document.createElement("textarea");ta.value=msg;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");done()}catch(e){ok.textContent="Copy failed, select and copy this:";var p=document.createElement("pre");p.style.whiteSpace="pre-wrap";p.textContent=msg;ok.appendChild(p)}document.body.removeChild(ta)}
 if(items[0])rememberFrom(items[0])}
function approvePost(b){var c=b.closest(".pc"),ok=c.querySelector(".pok");var msg="APPROVE post "+c.dataset.id+": "+c.dataset.t.trim()+" ["+c.dataset.img+"]";rememberFrom(c);
 function done(){ok.textContent="Copied, paste it into approver1 bot's chat"}
 function fb(){var ta=document.createElement("textarea");ta.value=msg;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");done()}catch(e){ok.textContent="Copy failed, select and copy this:";var p=document.createElement("pre");p.style.whiteSpace="pre-wrap";p.textContent=msg;ok.appendChild(p)}document.body.removeChild(ta)}
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(msg).then(done,fb);else fb()}
function getLast(){return _lsGet("xdash_last",null)}
function setLast(id,tab){if(!id)return;_lsSet("xdash_last",{id:String(id),tab:+tab||0});try{if(tab)localStorage.tabv2=String(tab)}catch(e){}showJump()}
function findById(sel,id){var nodes=document.querySelectorAll(sel);for(var i=0;i<nodes.length;i++){if(nodes[i].dataset&&nodes[i].dataset.id===id)return nodes[i]}return null}
function findItem(id){if(!id)return null;return findById(".bi",id)||findById(".pc",id)||findById(".oi",id)||findById(".ri",id)}
function clearHere(){document.querySelectorAll(".here").forEach(function(e){e.classList.remove("here");var t=e.querySelector(".here-tag");if(t)t.remove()})}
function applyHere(el){clearHere();if(!el)return;el.classList.add("here");if(!el.querySelector(".here-tag")){var tag=document.createElement("div");tag.className="here-tag";tag.textContent="📍 you were here";el.insertBefore(tag,el.firstChild)}}
function itemTab(el){var pane=el&&el.closest("#t1,#t2,#t3");return pane?+pane.id.slice(1):+(localStorage.tabv2||3)}
function rememberFrom(el){if(!el)return;var item=(el.classList&&(el.classList.contains("bi")||el.classList.contains("pc")||el.classList.contains("oi")||el.classList.contains("ri")))?el:el.closest(".bi,.pc,.oi,.ri");if(!item||!item.dataset.id)return;var tabn=itemTab(item);setLast(item.dataset.id,tabn);applyHere(item)}
function jumpToLast(){var L=getLast();if(!L||!L.id)return;var el=findItem(L.id);if(!el){showJump();return}var tabn=L.tab||itemTab(el);if(typeof tab==="function")tab(tabn);var d=el.closest("details");while(d){d.open=true;var p=d.parentElement;d=p?p.closest("details"):null}applyHere(el);setTimeout(function(){try{el.scrollIntoView({behavior:"smooth",block:"center"})}catch(e){try{el.scrollIntoView(true)}catch(x){}}},60);showJump()}
function showJump(){var btn=document.getElementById("jumpLast");if(!btn)return;var L=getLast();btn.style.display=(L&&L.id&&findItem(L.id))?"":"none"}
document.addEventListener("click",function(e){var t=e.target;if(!t||!t.closest)return;if(t.closest("#jumpLast")||t.closest(".tabs")||t.closest(".ctl"))return;var item=t.closest(".bi,.pc,.oi,.ri");if(item)rememberFrom(item)},true);
document.addEventListener("visibilitychange",function(){if(document.visibilityState==="visible")jumpToLast()});
window.addEventListener("pageshow",function(){jumpToLast()});
(function(){
 document.querySelectorAll(".bi").forEach(function(e){if(isDone("r",e.dataset.id))applyDone(e,true)});
 document.querySelectorAll(".batch").forEach(updProg);
 document.querySelectorAll(".pc").forEach(function(c){
  if(isDone("p",c.dataset.id))applyDone(c,true);
  var sid=getPosted(c.dataset.id)||(c.dataset.posted||"");
  var inp=c.querySelector(".posturl");if(inp&&sid)inp.value=sid;
  showAns(c,sid);
 });
 document.querySelectorAll("a.sv").forEach(function(a){var i=document.getElementById(a.dataset.img);if(i){a.href=i.src;a.download=a.dataset.name}});
 showJump();
})();
</script>'''
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
.d{{font-size:15px;margin:6px 0}}.btn{{display:block;text-align:center;background:#1d9bf0;color:#fff;border-radius:99px;padding:12px;font-weight:600;font-size:16px;border:0;box-sizing:border-box}}
.btn-sec{{background:#2f3336;color:#e7e9ea;font-size:14px;padding:8px;font-weight:500}}
.btn-row{{display:flex;gap:8px;margin:8px 0;flex-wrap:wrap}}.btn-row .btn{{flex:1;min-width:100px}}
.done{{opacity:.4}}.done .d{{text-decoration:line-through}}
.prog{{background:#2f3336;border-radius:99px;padding:2px 10px;font-size:13px;color:#e7e9ea;font-weight:500;margin-left:6px}}
.mdrow{{display:flex;gap:16px;align-items:center;font-size:15px;margin:8px 0;flex-wrap:wrap}}
.mdrow label{{display:flex;gap:8px;align-items:center}}
.mdrow input{{width:20px;height:20px}}
.posturl{{width:100%;box-sizing:border-box;padding:10px;font-size:15px;border-radius:10px;border:1px solid #2f3336;background:#0f1419;color:#e7e9ea;margin:6px 0}}
.here{{border-left:4px solid #ffd400!important;background:rgba(255,212,0,.14)!important;box-shadow:inset 4px 0 0 #ffd400}}.here-tag{{display:inline-block;background:#ffd400;color:#0f1419;font-size:12px;font-weight:700;border-radius:99px;padding:2px 8px;margin:0 0 8px}}#jumpLast{{position:fixed;bottom:16px;right:16px;z-index:98;background:#ffd400;color:#0f1419;border:0;border-radius:99px;padding:12px 16px;font-size:14px;font-weight:700;box-shadow:0 4px 16px rgba(0,0,0,.45);display:none}}.tabs{{display:flex;gap:8px;margin:12px 0;position:sticky;top:0;background:#0f1419;padding:6px 0;z-index:5}}.tabs button{{flex:1;background:#16202a;color:#e7e9ea;border:0;border-radius:12px;padding:10px;font-size:15px;font-weight:600}}.tabs button.on{{background:#1d9bf0}}.ctl{{margin:8px 0}}.ctl button{{background:#2f3336;color:#e7e9ea;border:0;border-radius:99px;padding:6px 12px;margin-right:6px}}</style></head><body>
<h1>Reply Dashboard <span class="b">{total} to reply</span></h1><div class="q">🔎 Last scanned X: <b>{E(d.get('last_scanned') or now)}</b> · page built {now}</div><button onclick="location.href=location.pathname+'?r='+Date.now()" style="width:100%;margin:10px 0 0;background:#00ba7c;color:#fff;border:0;border-radius:99px;padding:10px;font-size:16px;font-weight:600">🔄 Refresh</button>
<div class="ctl"><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">Expand all</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">Collapse all</button></div>''']
opps=d.get('opportunities',[])
nrep=total
posts=d.get('posts',[])  # list of {id,title,text,image?,answer?,note?,post_time?,created_ms,posted_id?}
out.append(f'<div class="tabs"><button id="b3" onclick="tab(3)">📝 Post to our page <span class="b{" z" if not posts else ""}">{len(posts)}</span></button><button id="b1" onclick="tab(1)">💬 Reply to viral posts <span class="b{" z" if not opps else ""}">{len(opps)}</span></button><button id="b2" onclick="tab(2)">💬 Replies &amp; likes <span class="b{" z" if not nrep else ""}">{nrep}</span></button></div><div id="t1"><div class="cd" id="cd1">⏱️ …</div><a target="_blank" rel="noopener" class="btn" style="display:block;text-align:center;background:#1d9bf0;margin:6px 0" href="https://github.com/6penny6wise6/x-reply-dashboard/actions/workflows/scan-now.yml">🔍 Scan now</a><div class="cd" id="scanst">Scan status: checking…</div>')
out.append(f'<h2 style="font-size:18px;margin:18px 0 4px">💬 Viral posts to reply to <span class="b{" z" if not opps else ""}">{len(opps)}</span></h2><div class="q">Save the image (press and hold, then Save to Photos), tap ↩️ Reply on their post, then attach it. These are replies on other people\'s posts, not posts on your page.</div>')
for o in opps:
    st=o['stats']; link='https://x.com/intent/post?in_reply_to='+o['id']+'&text='+u.quote(o['caption'].strip(),safe='')
    nt=f'<div class="q" style="color:#ffad1f">⚠️ {E(o["note"])}</div>' if o.get('note') else ''
    out.append(f'<details class="oi" data-id="{o["id"]}"><summary><div class="t"><span class="tt">{E(o["title"])}</span><span class="b">new</span></div><div class="st">@{E(o["author"])} · 👁 {fmt(st["views"])} · ❤️ {st["likes"]} · 💬 {st["replies"]}</div></summary><div class="in"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{o["author"]}/status/{o["id"]}">Open original post ↗</a></div><div class="d"><b>Q:</b> {E(o["question"])}<br><b>A:</b> {E(o["answer"])}</div>{nt}<img src="{o["image"]}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0"><div class="d">{E(o["caption"])}</div><a target="_blank" rel="noopener" class="btn" href="{link}">↩️ Reply on their post (@{E(o["author"])})</a></div></details>')
if not opps: out.append('<div class="q">Nothing new right now. The next scan runs within the hour, or tap Scan now.</div>')
out.append('</div><div id="t2" style="display:none"><div class="cd" id="cd2">⏱️ …</div>')
allr=[dict(r,thread=s['title']) for s in secs for r in s['replies']]
allr.sort(key=lambda r:-(r.get('views') or 0))
bs=[allr[i:i+8] for i in range(0,len(allr),8)]
if bs:
    out.append('<h2 style="font-size:17px;margin:14px 0 6px">↩️ Manual posting (phone)</h2><div class="q">Tap ↩️ Post reply (opens X with the draft), then ❤️ Like. Check Mark done when finished so it grays out. Batch 1 is the top-viewed comments. Nothing posts from this page.</div>')
for bi,b in enumerate(bs,1):
    out.append(f'<details class="batch"{" open" if bi==1 else ""}><summary><div class="t"><span class="tt">Batch {bi} of {len(bs)}</span><span class="prog" id="prog{bi}">0 of {len(b)} done</span><span class="b">{len(b)}</span></div></summary><div class="in" id="batch{bi}">')
    for r in b:
        rlink='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        llink='https://x.com/intent/like?tweet_id='+r['id']
        out.append(
            f'<div class="r bi" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"].strip())}">'
            f'<div class="q">{E(r["thread"])} · 👁 {fmt(r.get("views") or 0)}</div>'
            f'<div class="q"><a target="_blank" rel="noopener" href="https://x.com/{r["handle"]}/status/{r["id"]}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div>'
            f'<div class="d">{E(r["draft"])}</div>'
            f'<div class="btn-row">'
            f'<a target="_blank" rel="noopener" class="btn" href="{rlink}">↩️ Post reply</a>'
            f'<a target="_blank" rel="noopener" class="btn" style="flex:0 0 32%;background:#f91880" href="{llink}">❤️ Like</a>'
            f'</div>'
            f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'r\')"> Mark done</label>'
            f'<label><input type="checkbox" class="drop" onchange="this.closest(\'.bi\').style.opacity=this.checked?.35:\'\'"> Drop from Approve</label></div>'
            f'</div>'
        )
    out.append(
        f'<button class="btn btn-sec" style="width:100%;margin-top:8px" onclick="approve({bi},{len(bs)})">'
        f'📋 Copy APPROVE batch {bi} (for approver1)</button>'
        f'<div class="q" id="ok{bi}"></div></div></details>'
    )
# Keep per-thread manual section as a fallback view
if bs: out.append('<h2 style="font-size:17px;margin:18px 0 6px">📁 By thread</h2>')
for s in secs:
    n=len(s['replies']); st=s.get('stats')
    sl=f'<div class="st">👁 {fmt(st["views"])} views · ❤️ {st["likes"]} · 💬 {st["replies"]} replies</div>' if st else ''
    out.append(f'<details><summary><div class="t"><span class="tt">{E(s["title"])}</span><span class="b{" z" if n==0 else ""}">{n if n else "✓"}</span></div>{sl}</summary><div class="in"><div class="q"><a target="_blank" rel="noopener" href="{s["my_comment"]}">Open my comment ↗</a></div>')
    for r in s['replies']:
        link='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        out.append(f'<div class="r ri" data-id="{r["id"]}"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{r["handle"]}/status/{r["id"]}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div><div class="d">{E(r["draft"])}</div><div class="btn-row"><a target="_blank" rel="noopener" class="btn" style="flex:0 0 32%;background:#f91880" href="https://x.com/intent/like?tweet_id={r["id"]}">❤️ Like</a><a target="_blank" rel="noopener" class="btn" href="{link}">↩️ Post reply</a></div></div>')
    if n==0: out.append('<div class="q" style="padding-top:8px">All caught up ✅</div>')
    out.append('</div></details>')
out.append(SJS.replace('__SS__',json.dumps(d.get('scan_status'))))
out.append(JS.replace('__BUILT__',str(int(time.time()*1000))).replace('__RIDDLE__',str(d.get('last_riddle_scan_ms') or 0)))
def ptm(p):
    m=re.match(r'\s*(\d{1,2})(?::(\d\d))?\s*([AaPp])',p.get('post_time') or '')
    if not m: return 9999
    h=int(m.group(1))%12+(12 if m.group(3).lower()=='p' else 0); return h*60+int(m.group(2) or 0)
P=['</div><div id="t3" style="display:none"><h2 style="font-size:18px;margin:14px 0 4px">📝 Post to our page <span class="b'+(' z' if not posts else '')+f'">{len(posts)}</span></h2><div class="cd">original posts count toward monetization, replies don\'t. aim for 1 to 3 a day.</div><div class="q">🖼 Save image (or press and hold → Save to Photos), tap 📤 Post now, then attach the image in the composer. Intents can\'t attach images. Nothing posts from this page.</div>']
for p in sorted(posts,key=lambda p:(ptm(p),p.get('created_ms',0))):
    link='https://x.com/intent/post?text='+u.quote(p['text'].strip(),safe='')
    img=p.get('image'); absimg=('/workspace/x-dashboard/'+img) if img else 'none'
    pt=f'<span class="b">🕒 {E(p["post_time"])}</span>' if p.get('post_time') else ''
    im=f'<img id="pi_{E(p["id"])}" src="{E(img)}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0"><div class="q">intents can\'t attach images, so save the image and attach it in the composer. <a class="sv" data-img="pi_{E(p["id"])}" data-name="{E(img.split("/")[-1])}" href="#" target="_blank" rel="noopener">🖼 Save image</a></div>' if img else ''
    nt=f'<div class="q" style="color:#ffad1f">💡 {E(p["note"])}</div>' if p.get('note') else ''
    ans_text=(p.get('answer') or '').strip()
    ans_block=''
    if ans_text:
        ans_block=(
            f'<details style="background:#0f1419;margin:8px 0"><summary class="q" style="padding:8px">answer (post as a reply later)</summary>'
            f'<div class="d" style="padding:0 8px 8px">{E(ans_text)}</div></details>'
            f'<div class="q" style="margin-top:8px">After you post, paste the live post URL (or status ID) so you can tap Post answer:</div>'
            f'<input class="posturl" type="url" inputmode="url" placeholder="https://x.com/MrDonnieJackson/status/…" onchange="savePosted(this)" onblur="savePosted(this)">'
            f'<div class="answrap" style="display:none;margin-top:6px"><a target="_blank" rel="noopener" class="btn ansbtn" style="background:#7856ff" href="#">💡 Post answer</a></div>'
        )
    posted=E(str(p.get('posted_id') or ''))
    P.append(
        f'<div class="r pc" style="background:#16202a;border-radius:14px;padding:14px;margin:12px 0;border:0" '
        f'data-id="{E(p["id"])}" data-t="{E(p["text"].strip())}" data-img="{E(absimg)}" '
        f'data-ans="{E(ans_text)}" data-posted="{posted}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:17px"><span class="tt">{E(p["title"])}</span>{pt}</div>'
        f'{im}<div class="d">{E(p["text"])}</div>{nt}{ans_block}'
        f'<div class="btn-row">'
        f'<a target="_blank" rel="noopener" class="btn" href="{link}">📤 Post now</a>'
        f'<button type="button" class="btn" style="background:#00ba7c" onclick="copyText(this)">📋 Copy text</button>'
        f'</div>'
        f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'p\')"> Mark done</label></div>'
        f'<button type="button" class="btn btn-sec" style="width:100%;margin-top:4px" onclick="approvePost(this)">📋 Copy APPROVE (for approver1)</button>'
        f'<div class="q pok"></div></div>'
    )
if not posts: P.append('<div class="q">new post ideas get added every morning</div>')
out.append(''.join(P))
out.append(MAN)
out.append('</div><button type="button" id="jumpLast" onclick="jumpToLast()">📍 Jump to where I left off</button><script>function tab(n){for(const i of [1,2,3]){document.getElementById("t"+i).style.display=i==n?"":"none";document.getElementById("b"+i).className=i==n?"on":""}localStorage.tabv2=n}var _L=typeof getLast==="function"?getLast():null;if(_L&&_L.id&&typeof findItem==="function"&&findItem(_L.id)){jumpToLast()}else{tab(+(localStorage.tabv2||3));if(typeof showJump==="function")showJump()}</script></body></html>')
import seal; seal.publish('\n'.join(out))  # encrypted publish; never write plaintext index.html
print(total)
