import json, html, urllib.parse as u, datetime, zoneinfo, re, time
d=json.load(open('dashboard.json'))
# Apply saved replied-to set (from free x timeline reads) + posted replies in post_queue.json
# on EVERY build, so already-answered comments never show a live Post reply button.
try:
    import reconcile as _rc
    _rcm,_rcmv=_rc.apply_saved(d)
    if _rcm: print('reconcile: newly marked replied', _rcm)
except Exception as _e:
    print('reconcile skipped:', _e)
now=datetime.datetime.now(zoneinfo.ZoneInfo('America/Chicago')).strftime('%a %b %-d, %-I:%M %p CT')
d['updated']=now

def _prune_hist(hist):
    import datetime as _dt
    nowu=_dt.datetime.now(_dt.timezone.utc); cut=nowu-_dt.timedelta(days=7); out=[]
    for h in hist or []:
        ts=h.get('done_at') or h.get('replied_at') or ''
        try: t=_dt.datetime.fromisoformat(ts.replace('Z','+00:00'))
        except Exception: t=nowu
        if t>=cut: out.append(h)
    out.sort(key=lambda h: h.get('done_at') or h.get('replied_at') or '', reverse=True)
    return out

def _to_hist(item, *, thread='', my_comment='', kind='reply'):
    import datetime as _dt
    nowu=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    handle=item.get('handle') or item.get('author') or ''
    return {'id':item['id'],'handle':handle,'said':item.get('said') or item.get('question') or '',
            'draft':item.get('draft') or item.get('caption') or '','thread':thread,'my_comment':my_comment,
            'my_reply_id':item.get('my_reply_id') or '','replied':True,'liked':True,
            'replied_at':item.get('replied_at') or '','done_at':item.get('done_at') or nowu,'kind':kind,
            'url':f"https://x.com/{handle or 'i'}/status/{item['id']}"}

hist=list(d.get('history') or []); hist_ids={h['id'] for h in hist}
# Mirror both-done items into History for the tab, but KEEP them in sections/opps
# so the client can still "move back" (JS hides actionable copies when both done).
for s in d.get('sections') or []:
    for r in s.get('replies') or []:
        if r.get('replied') and r.get('liked') and r['id'] not in hist_ids:
            hist.append(_to_hist(r, thread=s.get('title',''), my_comment=s.get('my_comment',''))); hist_ids.add(r['id'])
for o in d.get('opportunities') or []:
    if o.get('replied') and o.get('liked') and o['id'] not in hist_ids:
        hist.append(_to_hist(o, thread=o.get('title',''), kind='opp')); hist_ids.add(o['id'])
d['history']=_prune_hist(hist)
# Actionable badge counts exclude both-done (JS also hides them live)
json.dump(d,open('dashboard.json','w'),ensure_ascii=False,indent=1)

secs=sorted(d['sections'],key=lambda s:(-len([r for r in s['replies'] if not (r.get('replied') and r.get('liked'))]),-s.get('stats',{}).get('views',0)))
def _actionable(r): return not (r.get('replied') and r.get('liked'))
total=sum(len([r for r in s['replies'] if _actionable(r)]) for s in secs)
E=html.escape
def fmt(n):
    n=n or 0
    if n>=1_000_000: return f"{n/1_000_000:.1f}M"
    return f"{n/1000:.1f}K" if n>=1000 else str(n)
def _ctms(v):
    try:
        v=int(v)
        if v<=0: return ''
        return datetime.datetime.fromtimestamp(v/1000,zoneinfo.ZoneInfo('America/Chicago')).strftime('%-I:%M %p')+' CT'
    except Exception: return ''
def asof(v): t=_ctms(v); return f' <span class="asof">· stats as of {t}</span>' if t else ''
def statline(label,st,at=None,extra=''):
    if not st: return ''
    return f'<div class="st"><b class="slab">{label}:</b> 👁 {fmt(st.get("views"))} · ❤️ {fmt(st.get("likes"))} · 💬 {fmt(st.get("replies"))}{extra}{asof(at)}</div>'
def chips(replied=False, liked=False):
    rc='ok' if replied else 'no'; lc='ok' if liked else 'no'
    rt='↩️ replied ✓' if replied else '↩️ not replied'
    lt='❤️ liked ✓' if liked else '❤️ not liked'
    return f'<div class="chips"><span class="chip {rc}">{rt}</span><span class="chip {lc}">{lt}</span></div>'

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

# Manual mode + pacing + fully-done Mark done
MAN=r'''<script>
function _lsGet(k,fb){try{var v=localStorage.getItem(k);return v?JSON.parse(v):fb}catch(e){return fb}}
function _lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function likedMap(){return _lsGet("xdash_liked",{})}
function setLiked(id,on){var m=likedMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_liked",m)}
function repliedMap(){return _lsGet("xdash_replied",{})}
function setRepliedLocal(id,on){var m=repliedMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_replied",m)}
function pendingMap(){return _lsGet("xdash_pending",{})}
function setPending(id,kind){var m=pendingMap();if(kind)m[id]={kind:kind,at:Date.now()};else delete m[id];_lsSet("xdash_pending",m)}
function backMap(){return _lsGet("xdash_back",{})}
function setBack(id,on){var m=backMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_back",m)}
function doneMap(){return _lsGet("xdash_done",{})}
function setDone(kind,id,on){var m=doneMap();var k=kind+":"+id;if(on)m[k]=1;else delete m[k];_lsSet("xdash_done",m)}
function isDone(kind,id){return !!doneMap()[kind+":"+id]}
function migrateDoneMarks(){
  /* Old Mark done only set xdash_done / replied. Treat any existing done mark as FULLY done. */
  var m=doneMap(), changed=false;
  Object.keys(m).forEach(function(k){
    if(!m[k])return;
    var parts=k.split(":"); if(parts.length<2)return;
    var kind=parts[0], id=parts.slice(1).join(":");
    if(kind==="r"||kind==="o"){
      if(!repliedMap()[id]){setRepliedLocal(id,true);changed=true}
      if(!likedMap()[id]){setLiked(id,true);changed=true}
      setBack(id,false);
    }else if(kind==="p"){
      if(!answeredMap()[id]){setAnswered(id,true);changed=true}
    }
  });
  return changed;
}
function itemFullyDone(el){
  if(!el||!el.dataset.id)return false;
  if(itemForcedBack(el))return false;
  var id=el.dataset.id;
  if(el.classList.contains("pc"))return !!isDone("p",id)||(!!getPosted(id)&&!!answeredMap()[id]);
  if(el.classList.contains("oi"))return !!isDone("o",id)||(itemReplied(el)&&itemLiked(el));
  return !!isDone("r",id)||(itemReplied(el)&&itemLiked(el));
}
function getPosted(id){var m=_lsGet("xdash_posted",{});return m[id]||""}
function setPosted(id,sid){var m=_lsGet("xdash_posted",{});if(sid)m[id]=sid;else delete m[id];_lsSet("xdash_posted",m)}
function answeredMap(){return _lsGet("xdash_answered",{})}
function setAnswered(id,on){var m=answeredMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_answered",m)}

function itemReplied(el){if(!el)return false;var id=el.dataset.id;return el.dataset.replied==="1"||!!repliedMap()[id]||!!isDone("r",id)||!!isDone("o",id)}
function itemLiked(el){if(!el)return false;var id=el.dataset.id;return el.dataset.liked==="1"||!!likedMap()[id]||!!isDone("r",id)||!!isDone("o",id)}
function itemForcedBack(el){return !!(el&&backMap()[el.dataset.id])}
function itemPending(el){if(!el)return null;return pendingMap()[el.dataset.id]||null}
function postIsDone(el){if(!el)return false;var id=el.dataset.id;return !!isDone("p",id)||!!(el.dataset.posted)||!!getPosted(id)}
function answerIsDone(el){if(!el)return false;return !!answeredMap()[el.dataset.id]}

function muteBtn(a,label,cls){
  if(!a)return;
  if(!a.getAttribute("data-href")&&a.getAttribute("href"))a.setAttribute("data-href",a.getAttribute("href"));
  a.textContent=label;
  a.removeAttribute("href");
  a.className="btn "+(cls||"btn-done");
  a.setAttribute("aria-disabled","true");
  a.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}return false};
}
function pendBtn(a,label,cls){
  if(!a)return;
  var href=a.getAttribute("data-href");
  if(href)a.setAttribute("href",href);
  a.textContent=label;a.className="btn btn-pendlive "+(cls||"");a.style.background="";
  a.removeAttribute("aria-disabled");a.onclick=null;
}
function gateBlocked(el){return typeof hardStopped==="function"&&(hardStopped()||inCooldown(gateOf(el)))}
function unmuteBtn(a,label,cls,pink){
  if(!a)return;
  var href=a.getAttribute("data-href");
  if(href)a.setAttribute("href",href);
  a.textContent=label;
  a.className="btn "+(cls||"")+(pink?" likebtn":"");
  if(pink)a.style.background="#f91880"; else a.style.background="";
  a.removeAttribute("aria-disabled");
  a.onclick=null;
}
function ensureUndo(el,kind){
  var row=el.querySelector(".undo-row");
  if(!row){row=document.createElement("div");row.className="undo-row q";el.appendChild(row)}
  var parts=[];
  var id=el.dataset.id;
  if(kind==="reply"||kind==="opp"){
    if(isDone("r",id)||isDone("o",id)||((likedMap()[id]||repliedMap()[id])&&!(el.dataset.liked==="1"&&el.dataset.replied==="1")))
      parts.push('<a href="#" class="undolink" data-u="full">undo mark done</a>');
    else{
      if(likedMap()[id]&&el.dataset.liked!=="1")parts.push('<a href="#" class="undolink" data-u="like">undo like</a>');
      if(repliedMap()[id]&&el.dataset.replied!=="1")parts.push('<a href="#" class="undolink" data-u="reply">undo reply</a>');
    }
  }
  if(kind==="post"){
    if(isDone("p",id)||answeredMap()[id])parts.push('<a href="#" class="undolink" data-u="full">undo mark done</a>');
  }
  row.innerHTML=parts.join(" · ");
  row.style.display=parts.length?"":"none";
}
function ensureConfirm(el){
  var pend=itemPending(el);
  var bar=el.querySelector(".confirm-bar");
  if(!pend){if(bar)bar.parentNode.removeChild(bar);return}
  if(itemReplied(el)&&pend.kind==="reply"){confirmReply(el,pend.at);setPending(el.dataset.id,null);if(bar)bar.parentNode.removeChild(bar);return}
  if(postIsDone(el)&&pend.kind==="post"){setPending(el.dataset.id,null);if(bar)bar.parentNode.removeChild(bar);return}
  if(answerIsDone(el)&&pend.kind==="answer"){setPending(el.dataset.id,null);if(bar)bar.parentNode.removeChild(bar);return}
  if(!bar){
    bar=document.createElement("div");
    bar.className="confirm-bar";
    bar.innerHTML='did it post? <button type="button" class="cy" data-yn="1">✅ yes</button> <button type="button" class="cn" data-yn="0">❌ no</button>';
    el.appendChild(bar);
  }
}
function paintChips(el){
  var box=el.querySelector(".chips");if(!box)return;
  var full=itemFullyDone(el),r=itemReplied(el),l=itemLiked(el),pend=itemPending(el);
  if(full){box.innerHTML='<span class="chip ok">✅ fully done</span><span class="chip ok">↩️ replied ✓</span><span class="chip ok">❤️ liked ✓</span>';return}
  var rs=r?"↩️ replied ✓":(pend&&pend.kind==="reply"?"⏳ confirm reply":"↩️ not replied");
  var ls=l?"❤️ liked ✓":"❤️ not liked";
  box.innerHTML='<span class="chip '+(r?"ok":(pend&&pend.kind==="reply"?"pend":"no"))+'">'+rs+'</span>'+
    '<span class="chip '+(l?"ok":"no")+'">'+ls+'</span>';
}
function paintActionButtons(el){
  if(!el||!el.dataset.id)return;
  var kind=el.classList.contains("pc")?"post":(el.classList.contains("oi")?"opp":"reply");
  var like=el.querySelector("a.likebtn, a.btn-liked, span.btn-liked");
  var reply=el.querySelector("a.replybtn, a.btn-replied, span.btn-replied");
  var post=el.querySelector("a.postbtn, a.btn-posted, span.btn-posted");
  var ans=el.querySelector("a.ansbtn, a.btn-answered, span.btn-answered");
  // normalize: if muted to span, skip; we keep as <a>
  if(el.querySelector("a.likebtn,a.btn-liked")){
    like=el.querySelector("a.likebtn,a.btn-liked");
    if(itemLiked(el))muteBtn(like,"❤️ Liked ✓","btn-done btn-liked");
    else unmuteBtn(like,"❤️ Like","",true);
  }
  if(el.querySelector("a.replybtn,a.btn-replied")){
    reply=el.querySelector("a.replybtn,a.btn-replied");
    var pend=itemPending(el);
    if(itemReplied(el))muteBtn(reply,"↩️ Replied ✓","btn-done btn-replied");
    else if(gateBlocked(el)){if(!reply.classList.contains("btn-cool")){reply.classList.add("btn-cool");reply.removeAttribute("href");reply.setAttribute("aria-disabled","true")}}
    else if(pend&&pend.kind==="reply")pendBtn(reply,"↩️ reopen X (confirm below)","replybtn");
    else unmuteBtn(reply,"↩️ Post reply","replybtn",false);
  }
  if(el.querySelector("a.postbtn,a.btn-posted")){
    post=el.querySelector("a.postbtn,a.btn-posted");
    var pendp=itemPending(el);
    if(postIsDone(el))muteBtn(post,"📤 Posted ✓","btn-done btn-posted");
    else if(pendp&&pendp.kind==="post")pendBtn(post,"📤 reopen X (confirm below)","postbtn");
    else unmuteBtn(post,"📤 Post now","postbtn",false);
  }
  if(el.querySelector("a.ansbtn,a.btn-answered")){
    ans=el.querySelector("a.ansbtn,a.btn-answered");
    var penda=itemPending(el);
    if(answerIsDone(el))muteBtn(ans,"💡 Answered ✓","btn-done btn-answered");
    else if(penda&&penda.kind==="answer")pendBtn(ans,"💡 reopen X (confirm below)","ansbtn");
    else{
      var href=ans.getAttribute("data-href")||ans.getAttribute("href");
      if(href&&href!=="#"){ans.className="btn ansbtn";ans.style.background="#7856ff";ans.textContent="💡 Post answer";ans.setAttribute("href",href);ans.removeAttribute("aria-disabled");ans.onclick=null;}
    }
  }
  // mark-done checkbox = fully done
  var cb=el.querySelector(".mdone");
  if(cb)cb.checked=itemFullyDone(el);
  var alk=el.querySelector("a.alreadyliked");if(alk)alk.style.display=itemLiked(el)?"none":"";
  paintChips(el);
  ensureConfirm(el);
  ensureUndo(el,kind);
}
function applyDone(el,on){if(!el)return;el.classList.toggle("done",!!on)}

function histList(){return document.getElementById("histList")}
function ensureHistCard(el){
  var id=el.dataset.id,list=histList();if(!list)return null;
  var existing=list.querySelector('.hc[data-id="'+id+'"]');if(existing)return existing;
  var h=document.createElement("div");h.className="r hc";h.dataset.id=id;
  var handle=el.dataset.h||"";
  var draft=(el.dataset.d||"").trim();
  var url=el.dataset.url||"#";
  var thread=el.dataset.thread||"";
  h.innerHTML='<div class="q">'+esc(thread)+' · @'+esc(handle)+'</div><div class="d">'+esc(draft)+'</div>'+
    '<div class="btn-row"><a target="_blank" rel="noopener" class="btn btn-sec" href="'+esc(url)+'">Open comment ↗</a>'+
    '<button type="button" class="btn btn-sec" data-back="'+esc(id)+'">↩ move back</button></div>';
  list.insertBefore(h,list.firstChild);return h;
}
function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function updProg(batch){
  if(!batch)return;
  var items=[].slice.call(batch.querySelectorAll(".bi"));
  var act=items.filter(function(e){return !e.classList.contains("hist")});
  var done=act.filter(function(e){return itemFullyDone(e)}).length;
  var el=batch.querySelector(".prog");if(el)el.textContent=done+" of "+act.length+" fully done";
  var badge=batch.querySelector(".bcount");if(badge)badge.textContent=String(act.length);
  batch.style.display=act.length?"":"none";
}
function updThread(det){
  if(!det||det.classList.contains("batch")||det.classList.contains("oi"))return;
  var items=[].slice.call(det.querySelectorAll(".ri"));
  var act=items.filter(function(e){return !e.classList.contains("hist")});
  var badge=det.querySelector(".bcount");
  if(badge){badge.textContent=act.length?String(act.length):"✓";badge.classList.toggle("z",!act.length)}
  if(!act.length&&items.length)det.style.display="none"; else if(act.length)det.style.display="";
}
function updHistEmpty(){
  var list=histList(),empty=document.getElementById("histEmpty"),n=list?list.querySelectorAll(".hc").length:0;
  if(empty)empty.style.display=n?"none":"";
  var badge=document.getElementById("histBadge");if(badge){badge.textContent=String(n);badge.classList.toggle("z",!n)}
}
function reconcileItem(el){
  if(!el||!el.dataset.id)return;
  paintActionButtons(el);
  if(el.classList.contains("pc")){
    /* posts stay on Post tab when done; no History move required */
    return;
  }
  var both=itemFullyDone(el),back=itemForcedBack(el);
  if(both&&!back){el.classList.add("hist");el.style.display="none";ensureHistCard(el)}
  else{el.classList.remove("hist");if(el.style.display==="none")el.style.display=""}
}
function syncId(id){
  if(!id)return;
  var nodes=document.querySelectorAll('.bi[data-id="'+id+'"], .ri[data-id="'+id+'"], .oi[data-id="'+id+'"], .pc[data-id="'+id+'"]');
  for(var i=0;i<nodes.length;i++)reconcileItem(nodes[i]);
  document.querySelectorAll(".batch").forEach(updProg);
  document.querySelectorAll("#t2sec details").forEach(updThread);
  updHistEmpty();
  if(typeof paintLikeAll==="function")paintLikeAll();
}
function resyncAll(){
  paintPace();
  var nodes=document.querySelectorAll(".bi,.ri,.oi,.pc");
  for(var i=0;i<nodes.length;i++)reconcileItem(nodes[i]);
  document.querySelectorAll(".batch").forEach(updProg);
  document.querySelectorAll("#t2sec details").forEach(updThread);
  updHistEmpty();
  paintLikeAll();
  var L=getLast();
  if(L&&L.id){var el=findItem(L.id);if(!el||el.classList.contains("hist")){clearHere();showJump()}}
  else showJump();
}

function markDone(cb,kind){
  var sel=kind==="r"?".bi,.ri":kind==="o"?".oi":".pc";
  var el=cb.closest(sel);var id=el&&el.dataset.id;if(!id)return;
  var on=!!cb.checked;
  if(on&&(kind==="r"||kind==="o")&&!itemReplied(el))confirmReply(el);
  setDone(kind,id,on);
  if(kind==="r"||kind==="o"){
    /* Mark done = FULLY DONE: replied + liked */
    setRepliedLocal(id,on);
    setLiked(id,on);
    if(on){setBack(id,false);setPending(id,null)}
  }
  if(kind==="p"){
    /* Post cards: posted + answered */
    if(on){setAnswered(id,true);setPending(id,null)}
    else setAnswered(id,false);
  }
  rememberFrom(el);syncId(id);
}
function moveBack(id){
  setBack(id,true);setLiked(id,false);setRepliedLocal(id,false);setDone("r",id,false);setDone("o",id,false);setDone("p",id,false);setAnswered(id,false);setPending(id,null);
  var list=histList();if(list){var hc=list.querySelector('.hc[data-id="'+id+'"]');if(hc&&!hc.getAttribute("data-server"))hc.parentNode.removeChild(hc)}
  syncId(id);rememberFrom(document.querySelector('.bi[data-id="'+id+'"], .ri[data-id="'+id+'"], .oi[data-id="'+id+'"]'));
}
function parseStatusId(v){if(!v)return "";v=(""+v).trim();var m=v.match(/(?:status\/|statuses\/|=)(\d{5,})/);if(m)return m[1];if(/^\d{5,}$/.test(v))return v;return ""}
function savePosted(inp){var c=inp.closest(".pc"),id=c.dataset.id,sid=parseStatusId(inp.value);inp.value=sid;setPosted(id,sid);showAns(c,sid);setPending(id,null);rememberFrom(c);syncId(id)}
function showAns(c,sid){var wrap=c.querySelector(".answrap");if(!wrap)return;if(sid){wrap.style.display="";var a=wrap.querySelector("a.ansbtn,a.btn-answered");if(a){var ans=(c.dataset.ans||"").trim();var href="https://x.com/intent/post?in_reply_to="+encodeURIComponent(sid)+"&text="+encodeURIComponent(ans);a.setAttribute("data-href",href);if(!answerIsDone(c)){a.setAttribute("href",href);a.className="btn ansbtn";a.style.background="#7856ff";a.textContent="💡 Post answer"}}}else wrap.style.display="none"}
function copyText(b){var c=b.closest(".pc"),t=(c.dataset.t||"").trim(),ok=c.querySelector(".pok");rememberFrom(c);
 function done(){ok.textContent="Copied ✓"}
 function fb(){var ta=document.createElement("textarea");ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");done()}catch(e){ok.textContent="Copy failed, select the post text above"}document.body.removeChild(ta)}
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(done,fb);else fb()}
function approve(n,t){var items=[].slice.call(document.querySelectorAll("#batch"+n+" .bi")).filter(function(e){return !e.querySelector(".drop").checked&&!e.classList.contains("hist")});
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
function findById(sel,id){var nodes=document.querySelectorAll(sel);for(var i=0;i<nodes.length;i++){if(nodes[i].dataset&&nodes[i].dataset.id===id&&!nodes[i].classList.contains("hist")&&nodes[i].style.display!=="none")return nodes[i]}return null}
function findItem(id){if(!id)return null;return findById(".bi",id)||findById(".pc",id)||findById(".oi",id)||findById(".ri",id)||findById(".hc",id)}
function clearHere(){document.querySelectorAll(".here").forEach(function(e){e.classList.remove("here");var t=e.querySelector(".here-tag");if(t)t.parentNode.removeChild(t)})}
function applyHere(el){clearHere();if(!el)return;el.classList.add("here");if(!el.querySelector(".here-tag")){var tag=document.createElement("div");tag.className="here-tag";tag.textContent="📍 you were here";el.insertBefore(tag,el.firstChild)}}
function itemTab(el){var pane=el&&el.closest("#t1,#t3,#t4");return pane?+pane.id.slice(1):+(localStorage.tabv2||3)}
function rememberFrom(el){if(!el)return;var item=el.closest?el.closest(".bi,.pc,.oi,.ri,.hc"):null;if(!item&&el.classList)item=el;if(!item||!item.dataset||!item.dataset.id)return;var tabn=itemTab(item);setLast(item.dataset.id,tabn);applyHere(item)}
function jumpToLast(){var L=getLast();if(!L||!L.id)return;var el=findItem(L.id);if(!el){showJump();return}var tabn=L.tab||itemTab(el);if(typeof tab==="function")tab(tabn);var d=el.closest("details");while(d){d.open=true;var p=d.parentElement;d=p?p.closest("details"):null}applyHere(el);setTimeout(function(){var cbx=el.querySelector(".confirm-bar");if(cbx){try{cbx.scrollIntoView({block:"center"});return}catch(e){}}try{el.scrollIntoView({behavior:"smooth",block:"center"})}catch(e){try{el.scrollIntoView(true)}catch(x){}}},60);showJump()}
function showJump(){var btn=document.getElementById("jumpLast");if(!btn)return;var L=getLast();btn.style.display=(L&&L.id&&findItem(L.id))?"":"none"}


/* —— reply pacing: two gates, started only on CONFIRMED replies —— */
/* viral = top-level replies on other people's posts (.oi), 10-15 min.
   thread = replies to commenters in his own threads (.bi/.ri), 3-5 min.
   v2 key ignores the old xdash_pace coolUntil (it was set on tap, not post). */
function ctParts(){var p={};new Intl.DateTimeFormat("en-US",{timeZone:"America/Chicago",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).formatToParts(new Date()).forEach(function(x){p[x.type]=x.value});return p}
function ctDayKey(){var p=ctParts();return p.year+"-"+p.month+"-"+p.day}
var GATES={viral:{min:10,span:6,label:"viral reply"},thread:{min:3,span:3,label:"thread reply"}};
function paceGet(){var v=_lsGet("xdash_pace2",null);
  if(!v){var old=_lsGet("xdash_pace",null);v={day:ctDayKey(),count:(old&&old.day===ctDayKey()?(old.count||0):0),counted:{},viralUntil:0,threadUntil:0};_lsSet("xdash_pace2",v)}
  if(!v.counted)v.counted={};return v}
function paceSet(v){_lsSet("xdash_pace2",v)}
(function(){try{if(localStorage.getItem("xdash_pace_fix")==="v1")return;var v=_lsGet("xdash_pace2",null);if(v){v.count=Object.keys(v.counted||{}).length;_lsSet("xdash_pace2",v)}localStorage.setItem("xdash_pace_fix","v1")}catch(e){}})();
function paceEnsureDay(){var p=paceGet(),k=ctDayKey();if(p.day!==k){p={day:k,count:0,counted:{},viralUntil:p.viralUntil||0,threadUntil:p.threadUntil||0};paceSet(p)}return p}
function gateOf(el){return el&&el.classList&&el.classList.contains("oi")?"viral":"thread"}
function coolLeftMs(g){var p=paceEnsureDay();return Math.max(0,(p[g+"Until"]||0)-Date.now())}
function inCooldown(g){return coolLeftMs(g)>0}
function fmtCool(ms){var s=Math.ceil(ms/1000),m=Math.floor(s/60),r=s%60;return m+":"+(r<10?"0":"")+r}
function replyCount(){return paceEnsureDay().count||0}
function hardStopped(){return replyCount()>=30 && !_lsGet("xdash_pace_override",false)}
function softWarned(){return replyCount()>=25}
/* call when a reply is CONFIRMED (yes / Mark done / verified). from = when it was posted (ms). */
function confirmReply(el,from){
  if(!el||!el.dataset.id)return;var id=el.dataset.id,p=paceEnsureDay();
  if(p.counted[id])return;
  p.counted[id]=1;p.count=(p.count||0)+1;
  var g=gateOf(el),G=GATES[g],until=(from||Date.now())+(G.min+Math.random()*G.span)*60000;
  if(until>(p[g+"Until"]||0))p[g+"Until"]=until;
  paceSet(p);paintPace();
}
function paintPace(){
  var p=paceEnsureDay(), lv=coolLeftMs("viral"), lt=coolLeftMs("thread"), bar=document.getElementById("paceBar"), day=document.getElementById("paceDay");
  if(day){
    var n=p.count||0, cls=n>=30?"pace-hard":(n>=25?"pace-soft":"");
    day.className="pace-day "+cls;
    day.textContent="replies today: "+n+" of 25"+(n>=30?" · hard stop (30)":(n>=25?" · soft cap":""));
  }
  if(bar){
    if(lv>0||lt>0){bar.style.display="";
      bar.innerHTML="⏳ "+(lv>0?"next viral reply in <b>"+fmtCool(lv)+"</b>":"viral replies ready ✓")+" · "+(lt>0?"next thread reply in <b>"+fmtCool(lt)+"</b>":"thread replies ready ✓")+" · likes always ok"+(lv>0?" · good time to post an original 📝":"")}
    else{bar.style.display="none"}
  }
  var hs=hardStopped();
  document.querySelectorAll("a.replybtn").forEach(function(a){
    if(a.getAttribute("aria-disabled")==="true"&&a.classList.contains("btn-done"))return;
    var el=a.closest(".bi,.ri,.oi"),g=gateOf(el),blocked=hs||inCooldown(g);
    if(blocked){
      if(!a.getAttribute("data-href")&&a.getAttribute("href"))a.setAttribute("data-href",a.getAttribute("href"));
      a.removeAttribute("href");
      a.classList.add("btn-cool");
      a.setAttribute("aria-disabled","true");
      a.textContent=hs?"🛑 daily limit":"⏳ "+fmtCool(coolLeftMs(g));
    }else if(a.classList.contains("btn-cool")){
      a.classList.remove("btn-cool");
      var href=a.getAttribute("data-href");
      if(href&&!itemReplied(el)){a.setAttribute("href",href);var pp=itemPending(el);a.textContent=(pp&&pp.kind==="reply")?"↩️ reopen X (confirm below)":"↩️ Post reply";a.removeAttribute("aria-disabled")}
    }
  });
  var warn=document.getElementById("paceWarn");
  if(warn){
    if(hs){warn.style.display="";warn.innerHTML="hard stop at 30 replies today. <a href=\"#\" id=\"paceOverride\">post anyway</a>"}
    else if(softWarned()){warn.style.display="";warn.textContent="soft cap hit (25). slow down, hard stop at 30."}
    else warn.style.display="none";
  }
}
function tryReplyGate(el){
  if(hardStopped()||inCooldown(gateOf(el))){paintPace();return false}
  return true;
}
/* a tap only marks pending; nothing is counted or cooled until confirmed */
function onReplyTapPaced(a){
  var el=a.closest(".bi,.ri,.oi");if(!el)return;
  if(itemReplied(el))return;
  var pp=itemPending(el);if(pp&&pp.kind==="reply"){setPending(el.dataset.id,"reply");return}
  if(!tryReplyGate(el)){return}
  setPending(el.dataset.id,"reply");
  later(function(){rememberFrom(el);syncId(el.dataset.id)});
}


function later(fn){setTimeout(fn,350)}
function onLikeTap(a){var el=a.closest(".bi,.ri,.oi");if(!el)return;setLiked(el.dataset.id,true);setBack(el.dataset.id,false);later(function(){rememberFrom(el);syncId(el.dataset.id)})}
function onReplyTap(a){onReplyTapPaced(a)}
/* already-liked helpers: phone-side like state only (X hides likes from free reads) */
function laItems(scope){return [].slice.call(scope.querySelectorAll(".bi,.ri,.oi")).filter(function(e){return !e.classList.contains("hist")})}
function laUndoGet(){return _lsGet("xdash_likeall_undo",{})}
function laUndoSet(k,ids){var m=laUndoGet();if(ids&&ids.length)m[k]={ids:ids,at:Date.now()};else delete m[k];_lsSet("xdash_likeall_undo",m)}
function paintLikeAll(){
  document.querySelectorAll(".likeall-bar").forEach(function(bar){
    var scope=bar.closest(".likeall-scope");if(!scope)return;
    var k=bar.getAttribute("data-k"),btn=bar.querySelector("button.likeall"),msg=bar.querySelector(".likeall-msg");
    var left=laItems(scope).filter(function(e){return !itemLiked(e)}).length;
    if(btn){if(left){btn.disabled=false;btn.textContent=btn.getAttribute("data-label")+" ("+left+")";btn.className="btn likeall"}else{btn.disabled=true;btn.textContent="❤️ all marked liked ✓";btn.className="btn likeall btn-done"}}
    var u=laUndoGet()[k];
    if(u&&Date.now()-u.at>86400000){laUndoSet(k,null);u=null}
    if(msg)msg.innerHTML=u?'❤️ marked '+u.ids.length+' as liked · <a href="#" class="likeall-undo" data-k="'+esc(k)+'">undo</a>':"";
  });
  var g=document.getElementById("laGlobal");if(g){var m=laUndoGet(),best=null,bk="";for(var k in m){if(Date.now()-m[k].at>86400000)continue;if(!best||m[k].at>best.at){best=m[k];bk=k}}
    if(best){g.style.display="";g.innerHTML='❤️ last "already liked all": '+best.ids.length+' marked liked · <a href="#" class="likeall-undo" data-k="'+esc(bk)+'">undo</a> · <a href="#" class="likeall-x" data-k="'+esc(bk)+'">hide</a>'}else{g.style.display="none";g.innerHTML=""}}
}
function likeAllIn(bar){
  var scope=bar.closest(".likeall-scope");if(!scope)return;
  var ids=[];laItems(scope).forEach(function(e){var id=e.dataset.id;if(!itemLiked(e)&&ids.indexOf(id)<0)ids.push(id)});
  if(!ids.length){paintLikeAll();return}
  ids.forEach(function(id){setLiked(id,true);setBack(id,false)});
  laUndoSet(bar.getAttribute("data-k"),ids);
  ids.forEach(syncId);paintLikeAll();
}
function undoLikeAll(k){
  var u=laUndoGet()[k];if(!u)return;
  var list=histList();
  u.ids.forEach(function(id){setLiked(id,false);if(list){var hc=list.querySelector('.hc[data-id="'+id+'"]');if(hc&&!hc.getAttribute("data-server"))hc.parentNode.removeChild(hc)}});
  laUndoSet(k,null);
  u.ids.forEach(syncId);paintLikeAll();
}
function markAlreadyLiked(a){var el=a.closest(".bi,.ri,.oi");if(!el)return;setLiked(el.dataset.id,true);setBack(el.dataset.id,false);rememberFrom(el);syncId(el.dataset.id);paintLikeAll()}
function onPostTap(a){var el=a.closest(".pc");if(!el)return;if(postIsDone(el))return;setPending(el.dataset.id,"post");later(function(){rememberFrom(el);syncId(el.dataset.id)})}
function onAnsTap(a){var el=a.closest(".pc");if(!el)return;if(answerIsDone(el))return;setPending(el.dataset.id,"answer");later(function(){rememberFrom(el);syncId(el.dataset.id)})}

document.addEventListener("click",function(e){
  var t=e.target;if(!t||!t.closest)return;
  if(t.closest("#jumpLast")||t.closest(".tabs")||t.closest(".ctl")||t.closest("#newDataPill"))return;
  var back=t.closest("[data-back]");if(back){e.preventDefault();moveBack(back.getAttribute("data-back"));return}
  var yn=t.closest(".confirm-bar [data-yn]");
  if(yn){e.preventDefault();e.stopPropagation();var cbar=yn.closest(".confirm-bar");var el=yn.closest(".bi,.ri,.oi,.pc");if(!el&&cbar&&cbar.getAttribute("data-for")){var fid=cbar.getAttribute("data-for");el=document.querySelector('.pc[data-id="'+fid+'"]')||document.querySelector('.oi[data-id="'+fid+'"],.bi[data-id="'+fid+'"],.ri[data-id="'+fid+'"]')}if(!el){console.warn("confirm: no item for bar");return}var yes=yn.getAttribute("data-yn")==="1";var pend=itemPending(el);
    if(yes){if(pend&&pend.kind==="reply"){confirmReply(el);setRepliedLocal(el.dataset.id,true);setDone(el.classList.contains("oi")?"o":"r",el.dataset.id,true);setBack(el.dataset.id,false)}
      else if(pend&&pend.kind==="post"){setDone("p",el.dataset.id,true)}
      else if(pend&&pend.kind==="answer"){setAnswered(el.dataset.id,true)}
      setPending(el.dataset.id,null)}
    else{setPending(el.dataset.id,null)}
    rememberFrom(el);syncId(el.dataset.id);if(typeof paintNow==="function"){var nb=document.getElementById("nowBar");if(nb)nb.dataset.k="";paintNow()}return}
  var und=t.closest("a.undolink");
  if(und){e.preventDefault();var el=und.closest(".bi,.ri,.oi,.pc");if(!el)return;var u=und.getAttribute("data-u");var id=el.dataset.id;
    if(u==="like")setLiked(id,false);
    if(u==="reply"){setRepliedLocal(id,false);setDone("r",id,false);setDone("o",id,false)}
    if(u==="post")setDone("p",id,false);
    if(u==="ans")setAnswered(id,false);
    if(u==="full"){setLiked(id,false);setRepliedLocal(id,false);setDone("r",id,false);setDone("o",id,false);setDone("p",id,false);setAnswered(id,false);setPending(id,null);setBack(id,true)}
    rememberFrom(el);syncId(id);return}
  var lb=t.closest(".likeall-bar button.likeall");if(lb){e.preventDefault();if(!lb.disabled)likeAllIn(lb.closest(".likeall-bar"));return}
  var lu=t.closest("a.likeall-undo");if(lu){e.preventDefault();undoLikeAll(lu.getAttribute("data-k"));return}
  var lx=t.closest("a.likeall-x");if(lx){e.preventDefault();laUndoSet(lx.getAttribute("data-k"),null);paintLikeAll();return}
  var alk=t.closest("a.alreadyliked");if(alk){e.preventDefault();markAlreadyLiked(alk);return}
  var like=t.closest("a.likebtn");if(like&&!like.getAttribute("aria-disabled"))onLikeTap(like);
  var reply=t.closest("a.replybtn");
  if(reply&&!reply.getAttribute("aria-disabled")){
    if(!tryReplyGate(reply.closest(".bi,.ri,.oi"))){e.preventDefault();return}
    onReplyTap(reply);
  }
  var ov=t.closest("#paceOverride");if(ov){e.preventDefault();if(confirm("Post more replies today anyway?")){_lsSet("xdash_pace_override",true);paintPace()}return}
  var post=t.closest("a.postbtn");if(post&&!post.getAttribute("aria-disabled"))onPostTap(post);
  var ans=t.closest("a.ansbtn");if(ans&&!ans.getAttribute("aria-disabled"))onAnsTap(ans);
  var item=t.closest(".bi,.pc,.oi,.ri,.hc");if(item)later(function(){rememberFrom(item)});
},true);

document.addEventListener("visibilitychange",function(){if(document.visibilityState==="visible"){resyncAll();jumpToLast()}});
window.addEventListener("pageshow",function(){resyncAll();jumpToLast()});
window.addEventListener("storage",function(){resyncAll()});

var _syncTimer=null;
function startSyncLoop(){if(_syncTimer)return;_syncTimer=setInterval(function(){if(document.visibilityState==="visible")resyncAll()},2000)}
function stopSyncLoop(){if(_syncTimer){clearInterval(_syncTimer);_syncTimer=null}}
document.addEventListener("visibilitychange",function(){if(document.visibilityState==="visible")startSyncLoop();else stopSyncLoop()});
startSyncLoop();

/* background scan refresh — iOS-safe: show pill, user taps to reload */
var _ct0=null;
function showNewPill(){var p=document.getElementById("newDataPill");if(!p){p=document.createElement("button");p.id="newDataPill";p.type="button";p.textContent="🆕 new scan data — tap to update";p.onclick=function(){location.href=location.pathname+"?r="+Date.now()};document.body.appendChild(p)}p.style.display=""}
function pollScan(){if(document.visibilityState!=="visible")return;
  var url=location.pathname+(location.pathname.indexOf("?")>=0?"&":"?")+"r="+Date.now();
  fetch(url,{cache:"no-store",credentials:"same-origin"}).then(function(r){return r.text()}).then(function(html){
    var m=html.match(/var B=(\{[\s\S]*?\}),K=/);if(!m)return;
    var B=JSON.parse(m[1]);if(!_ct0){_ct0=B.ct;return}if(B.ct!==_ct0)showNewPill();
  }).catch(function(){})}
setInterval(pollScan,60000);
setTimeout(pollScan,8000);

(function(){
  migrateDoneMarks();
  document.querySelectorAll("a.likebtn,a.replybtn,a.postbtn,a.ansbtn").forEach(function(a){var h=a.getAttribute("href");if(h&&h!=="#"&&!a.getAttribute("data-href"))a.setAttribute("data-href",h)});
  document.querySelectorAll(".pc").forEach(function(c){
    var sid=getPosted(c.dataset.id)||(c.dataset.posted||"");
    var inp=c.querySelector(".posturl");if(inp&&sid)inp.value=sid;
    showAns(c,sid);
  });
  document.querySelectorAll("a.sv").forEach(function(a){var i=document.getElementById(a.dataset.img);if(i){a.href=i.src;a.download=a.dataset.name}});
  resyncAll();paintPace();showJump();
 setInterval(paintPace,1000);
})();
</script>'''

def _load_targets():
    base=['its_The_Dr','DavidLimbaugh','atensnut','TONYxTWO','CynicalPublius']
    try:
        txt=open('/workspace/x-growth/atensnut_lookalikes.md').read()
        sec=txt.split('## 3.')[1].split('## 4.')[0] if '## 3.' in txt else ''
        for h in re.findall(r'\[@([A-Za-z0-9_]+)\]',sec):
            if h not in base: base.append(h)
    except Exception: pass
    return base
TARGETS=_load_targets(); _TL={h.lower():i for i,h in enumerate(TARGETS)}
FARM={h.lower() for h in (d.get('farm_blocklist') or [])}
# code-level guarantee: finished target answers go to the TOP of post_queue.json every build
try:
    if _rc.promote_opportunities(d, TARGETS, FARM): print('queue: promoted open opportunity answers')
except Exception as _e:
    print('queue promote skipped:', _e)
RESET=r"""<script>(function(){try{var R=__RESET__;if(!R||!R.v||localStorage.getItem("xdash_reset_v")===R.v)return;
function g(k){try{return JSON.parse(localStorage.getItem(k)||"{}")||{}}catch(e){return {}}}function s(k,v){localStorage.setItem(k,JSON.stringify(v))}
var dn=g("xdash_done"),po=g("xdash_posted"),an=g("xdash_answered"),pe=g("xdash_pending"),bk=g("xdash_back");
(R.ids||[]).forEach(function(id){delete dn["p:"+id];delete po[id];delete an[id];delete pe[id];delete bk[id]});
s("xdash_done",dn);s("xdash_posted",po);s("xdash_answered",an);s("xdash_pending",pe);s("xdash_back",bk);localStorage.setItem("xdash_reset_v",R.v)}catch(e){}})();</script>"""
NOWJS=r"""<script>
function ctNowMin(){var p=ctParts();return {day:p.year+"-"+p.month+"-"+p.day,m:(+p.hour%24)*60+(+p.minute)}}
function paintNow(){var bar=document.getElementById("nowBar");if(!bar)return;var n=ctNowMin(),due=null,next=null;
 document.querySelectorAll(".pc").forEach(function(c){if(c.dataset.day!==n.day||postIsDone(c))return;var pend=itemPending(c);var sl=+c.dataset.slot;if(isNaN(sl)||sl>=9999)return;
  if(sl<=n.m){if(!due)due=c}else if(!next)next=c});
 var key=due?("d"+due.dataset.id+(itemPending(due)?"p":"")):next?("n"+next.dataset.id):"x";if(bar.dataset.k===key)return;bar.dataset.k=key;
 if(due){var img=due.querySelector("img"),pa=due.querySelector("a.postbtn");var href=pa?(pa.getAttribute("data-href")||pa.getAttribute("href")):"#";var pend=itemPending(due);
  bar.className="nowbar";bar.style.display="";bar.innerHTML="";
  var h=document.createElement("div");h.className="nowh";h.textContent="📣 post this now: "+due.dataset.title+" (slot "+due.dataset.ptime+")";bar.appendChild(h);
  if(img){var im=document.createElement("img");im.src=img.src;im.className="nowimg";bar.appendChild(im);var sv=document.createElement("a");sv.href=img.src;sv.download=(due.dataset.img||"image.jpg").split("/").pop();sv.target="_blank";sv.rel="noopener";sv.className="q";sv.textContent="🖼 Save image";bar.appendChild(sv)}
  var d=document.createElement("div");d.className="d";d.textContent=due.dataset.t||"";bar.appendChild(d);
  var row=document.createElement("div");row.className="btn-row";
  if(pend&&pend.kind==="post"){var cb=document.createElement("div");cb.className="confirm-bar nowconfirm";cb.setAttribute("data-for",due.dataset.id);cb.innerHTML='did it post? <button type="button" class="cy" data-yn="1">✅ yes</button> <button type="button" class="cn" data-yn="0">❌ no</button>';bar.appendChild(cb)}
  else{var a=document.createElement("a");a.className="btn nowpost";a.target="_blank";a.rel="noopener";a.href=href;a.textContent="📤 Post now";a.setAttribute("data-for",due.dataset.id);row.appendChild(a)}
  var j=document.createElement("button");j.type="button";j.className="btn btn-sec";j.textContent="↓ show card";j.onclick=function(){applyHere(due);due.scrollIntoView({block:"center"})};row.appendChild(j);bar.appendChild(row);
 }else if(next){bar.className="nowbar nownext";bar.style.display="";bar.textContent="⏭ next post: "+next.dataset.title+" at "+next.dataset.ptime}
 else{var tm=null;document.querySelectorAll(".pc").forEach(function(c){if(tm||postIsDone(c)||c.dataset.day<=n.day)return;tm=c});
  if(tm){bar.className="nowbar nownext";bar.style.display="";bar.textContent="⏭ next post: "+tm.dataset.title+" on "+(tm.dataset.sday||tm.dataset.day)+" at "+tm.dataset.ptime}else bar.style.display="none"}}
document.addEventListener("click",function(e){var a=e.target&&e.target.closest&&e.target.closest("a.nowpost");if(!a)return;var c=document.querySelector('.pc[data-id="'+a.getAttribute("data-for")+'"]');if(c&&!postIsDone(c)){setPending(c.dataset.id,"post");later(function(){rememberFrom(c);syncId(c.dataset.id);bar_reset();paintNow()})}},true);
function bar_reset(){var nb=document.getElementById("nowBar");if(nb)nb.dataset.k=""}
paintNow();setInterval(paintNow,2000);
</script>"""
opps=[o for o in d.get('opportunities',[]) if not o.get('skip') and (o.get('author') or '').lower() not in FARM]
for o in opps: o['_trank']=_TL.get((o.get('author') or '').lower())
opps.sort(key=lambda o:(0 if o['_trank'] is not None else 1, o['_trank'] if o['_trank'] is not None else 0, o.get('priority',9), -(o.get('stats',{}).get('views') or 0)))
_tnow=[o for o in opps if o['_trank'] is not None and not o.get('replied') and o.get('image') and (o.get('caption') or '').strip()]
for s in secs:
    s['replies']=[r for r in s['replies'] if not r.get('skip')]
secs=sorted(secs,key=lambda s:(-len(s['replies']),-s.get('stats',{}).get('views',0)))
total=sum(len(s['replies']) for s in secs)
posts_all=d.get('posts',[])
posted_live=[p for p in posts_all if p.get('posted_id')]
posts=[p for p in posts_all if not p.get('posted_id')]
history=d.get('history',[])
nrep=total
nhist=len(history)
from collections import Counter as _Counter
_alls=[]
for _s in secs:
    for _r in _s['replies']:
        _alls.append((_r['id'],' '.join((_r.get('draft') or '').lower().split()[:3])))
for _o in opps:
    _alls.append((_o['id'],' '.join((_o.get('caption') or '').lower().split()[:3])))
_open_counts=_Counter(o for _,o in _alls if o)
dup_ids={i for i,o in _alls if _open_counts.get(o,0)>1}

CSS_EXTRA = (
".chips{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}"
".chip{font-size:12px;font-weight:600;border-radius:99px;padding:3px 8px}"
".chip.ok{background:rgba(0,186,124,.2);color:#00ba7c}.chip.no{background:#2f3336;color:#8b98a5}"
".chip.pend{background:rgba(255,173,31,.2);color:#ffad1f}"
".btn-done{background:#2f3336!important;color:#8b98a5!important;opacity:.55;pointer-events:none;cursor:default}"
".btn-pendlive{background:#ffad1f!important;color:#0f1419!important}.btn-pend{background:#ffad1f!important;color:#0f1419!important;pointer-events:none;cursor:default}"
".confirm-bar{background:rgba(255,173,31,.15);border:1px solid #ffad1f;border-radius:10px;padding:8px 10px;margin:8px 0;font-size:14px;color:#e7e9ea}"
".confirm-bar{scroll-margin-top:180px;scroll-margin-bottom:40px}.confirm-bar button{touch-action:manipulation;min-height:40px;background:#16202a;color:#e7e9ea;border:1px solid #2f3336;border-radius:99px;padding:6px 12px;margin-left:6px;font-size:14px;font-weight:600}"
".confirm-bar .cy{background:#00ba7c;border-color:#00ba7c;color:#fff}"
".likeall-bar{margin:8px 0 4px}.likeall{width:100%;background:#2f3336;color:#f91880;border:1px solid #f91880;font-size:15px;padding:10px;touch-action:manipulation}.likeall-msg{margin-top:4px;font-size:13px}.likeall-msg a{color:#8b98a5;text-decoration:underline}"
".alreadyliked{color:#f91880;font-size:13px;text-decoration:underline;touch-action:manipulation}"
".undo-row{margin-top:4px}.undolink{color:#8b98a5;font-size:12px;text-decoration:underline}"
".here{border-left:4px solid #ffd400!important;background:rgba(255,212,0,.14)!important;box-shadow:inset 4px 0 0 #ffd400}"
".here-tag{display:inline-block;background:#ffd400;color:#0f1419;font-size:12px;font-weight:700;border-radius:99px;padding:2px 8px;margin:0 0 8px}"
"#jumpLast{position:fixed;bottom:16px;right:16px;z-index:98;background:#ffd400;color:#0f1419;border:0;border-radius:99px;padding:12px 16px;font-size:14px;font-weight:700;box-shadow:0 4px 16px rgba(0,0,0,.45);display:none}"
"#newDataPill{position:fixed;bottom:16px;left:16px;right:90px;z-index:98;background:#1d9bf0;color:#fff;border:0;border-radius:99px;padding:12px 14px;font-size:14px;font-weight:700;box-shadow:0 4px 16px rgba(0,0,0,.45);display:none}"
"#paceBar{position:sticky;top:52px;z-index:4;background:#16202a;border:1px solid #ffad1f;color:#ffad1f;border-radius:10px;padding:10px 12px;margin:8px 0;font-size:14px;display:none}"
".pace-day{background:#16181c;border:1px solid #2f3336;border-radius:10px;padding:8px 12px;margin:8px 0;font-size:14px;color:#e7e9ea}"
".pace-day.pace-soft{border-color:#ffad1f;color:#ffad1f}.pace-day.pace-hard{border-color:#f4212e;color:#f4212e}"
"#paceWarn{background:rgba(244,33,46,.12);border:1px solid #f4212e;color:#f4212e;border-radius:10px;padding:8px 12px;margin:8px 0;font-size:14px;display:none}"
".btn-cool{background:#2f3336!important;color:#8b98a5!important;opacity:.6;pointer-events:none}"
".d{white-space:pre-line}.slab{color:#e7e9ea;font-weight:600}.asof{color:#5c6670;font-size:12px}"
".dupflag{color:#ffad1f;font-size:12px;font-weight:600}"
".tipline{color:#8b98a5;font-size:13px;margin:6px 0 10px}"
".hc{background:#16202a;border-radius:14px;padding:12px;margin:10px 0;border:0}"
"#nowBar{position:static;background:#1a1f12;border:2px solid #ffd400;border-radius:14px;padding:10px 12px;margin:10px 0;box-shadow:0 6px 18px rgba(0,0,0,.5)}"
"#nowBar.nownext{border:1px solid #2f3336;background:#16181c;color:#8b98a5;font-size:14px;padding:8px 12px}"
".nowh{font-weight:700;font-size:16px;color:#ffd400;margin-bottom:6px}.nowimg{width:100%;max-height:22vh;object-fit:contain;border-radius:10px;background:#fff;margin:6px 0}"
"#targetNow{background:#0f2a1f;border:2px solid #00ba7c;border-radius:14px;padding:10px 12px;margin:10px 0;box-shadow:0 6px 18px rgba(0,0,0,.5)}#targetNow .nowh{color:#00ba7c}"
".dayh{font-size:15px;color:#8b98a5;margin:16px 0 0;font-weight:600}"
".ntag{font-size:12px;color:#8b98a5}.revnote{color:#ffad1f;margin:4px 0 8px}"
)

def _tnow_html():
    if not _tnow: return ''
    o=_tnow[0]; more=len(_tnow)-1
    return (f'<div id="targetNow" data-id="{o["id"]}"><div class="nowh">🎯 post this now: @{E(o["author"])} · {E(o["title"])}</div>'
            f'<div class="q">top-level answer on a target account. this beats old-thread replies{(" · "+str(more)+" more target pick"+("s" if more>1 else "")+" waiting") if more else ""}</div>'
            f'<img src="{o["image"]}" class="nowimg"><div class="d">{E(o["caption"])}</div>'
            f'<div class="btn-row"><button type="button" class="btn" id="tnGo" style="background:#00ba7c">🎯 open it &amp; reply</button></div></div>'
            '<script>function tnPaint(){var b=document.getElementById("targetNow");if(!b)return;var c=document.querySelector(\'.oi[data-id="\'+b.dataset.id+\'"]\');b.style.display=(!c||itemReplied(c))?"none":""}'
            'document.addEventListener("click",function(e){if(!e.target.closest||!e.target.closest("#tnGo"))return;var b=document.getElementById("targetNow");var c=document.querySelector(\'.oi[data-id="\'+b.dataset.id+\'"]\');if(!c)return;if(typeof tab==="function")tab(1);c.open=true;applyHere(c);setTimeout(function(){try{c.scrollIntoView({block:"start"})}catch(x){}},60)});'
            'setInterval(function(){if(typeof itemReplied==="function")tnPaint()},2000);</script>')
out=[f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="120"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><script>(function(){{var u=new URL(location.href);var r=+u.searchParams.get("r")||0;if(Date.now()-r>60000){{u.searchParams.set("r",Date.now());location.replace(u.toString());}}}})();</script><style>.cd{{background:#16181c;border:1px solid #2f3336;border-radius:10px;padding:8px 12px;margin:8px 0;font-size:14px;color:#71767b}}</style><title>Reply Dashboard ({total})</title>
<style>body{{font-family:-apple-system,system-ui;background:#0f1419;color:#e7e9ea;padding:16px;max-width:640px;margin:auto}}
h1{{font-size:22px;margin-bottom:4px}}details{{background:#16202a;border-radius:14px;margin:12px 0;overflow:hidden}}
summary{{list-style:none;padding:14px;cursor:pointer}}summary::-webkit-details-marker{{display:none}}
.t{{display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:17px;flex-wrap:wrap;gap:6px}}
.t:before{{content:"▸";margin-right:8px;color:#8b98a5}}details[open] .t:before{{content:"▾"}}.tt{{flex:1}}
.b{{background:#1d9bf0;border-radius:99px;padding:2px 10px;font-size:14px;color:#fff}}.z{{background:#2f3336}}
.st{{color:#8b98a5;font-size:13px;margin:4px 0 0 18px}}a{{color:#1d9bf0;text-decoration:none}}
.in{{padding:0 14px 12px}}.r{{border-top:1px solid #2f3336;padding:10px 0}}.q{{color:#8b98a5;font-size:14px}}
.d{{font-size:15px;margin:6px 0}}.btn{{display:block;text-align:center;background:#1d9bf0;color:#fff;border-radius:99px;padding:12px;font-weight:600;font-size:16px;border:0;box-sizing:border-box}}
.btn-sec{{background:#2f3336;color:#e7e9ea;font-size:14px;padding:8px;font-weight:500}}
.btn-row{{display:flex;gap:8px;margin:8px 0;flex-wrap:wrap}}.btn-row .btn{{flex:1;min-width:100px}}
.done{{opacity:.55}}
.prog{{background:#2f3336;border-radius:99px;padding:2px 10px;font-size:13px;color:#e7e9ea;font-weight:500;margin-left:6px}}
.mdrow{{display:flex;gap:16px;align-items:center;font-size:15px;margin:8px 0;flex-wrap:wrap}}
.mdrow label{{display:flex;gap:8px;align-items:center}}
.mdrow input{{width:20px;height:20px}}
.posturl{{width:100%;box-sizing:border-box;padding:10px;font-size:15px;border-radius:10px;border:1px solid #2f3336;background:#0f1419;color:#e7e9ea;margin:6px 0}}
.tabs{{display:flex;gap:6px;margin:12px 0;position:sticky;top:0;background:#0f1419;padding:6px 0;z-index:5;flex-wrap:wrap}}.tabs button{{flex:1;min-width:40%;background:#16202a;color:#e7e9ea;border:0;border-radius:12px;padding:10px 8px;font-size:13px;font-weight:600}}.tabs button.on{{background:#1d9bf0}}.ctl{{margin:8px 0}}.ctl button{{background:#2f3336;color:#e7e9ea;border:0;border-radius:99px;padding:6px 12px;margin-right:6px}}
''' + CSS_EXTRA + f'''</style></head><body>
<h1>Reply Dashboard <span class="b">{total} to reply</span></h1><div class="q">🔎 Last scanned X: <b>{E(d.get('last_scanned') or now)}</b> · page built {now}</div><button onclick="location.href=location.pathname+'?r='+Date.now()" style="width:100%;margin:10px 0 0;background:#00ba7c;color:#fff;border:0;border-radius:99px;padding:10px;font-size:16px;font-weight:600">🔄 Refresh</button>
<div class="ctl"><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">Expand all</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">Collapse all</button></div><div class="pace-day" id="paceDay">replies today: …</div><div id="paceWarn"></div><div id="paceBar"></div><div class="tipline">💡 one top-level reply per post, no copy-paste answers. viral replies 10–15 min apart, thread replies 3–5 min. timers start once a reply is confirmed.</div>'''+_tnow_html()+'''<div id="laGlobal" class="likeall-msg q" style="display:none"></div>''']

out.append(
 f'<div class="tabs">'
 f'<button id="b3" onclick="tab(3)">📝 Post to our page <span class="b{" z" if not posts else ""}">{len(posts)}</span></button>'
 f'<button id="b1" onclick="tab(1)">💬 Reply to viral posts <span class="b{" z" if not opps else ""}">{len(opps)}</span></button>'
 f'<button id="b2" onclick="tab(2)">💬 Replies &amp; likes <span class="b{" z" if not nrep else ""}">{nrep}</span></button>'
 f'<button id="b4" onclick="tab(4)">🗂 History <span class="b{" z" if not nhist else ""}" id="histBadge">{nhist}</span></button>'
 f'</div><div id="t1"><div class="cd" id="cd1">⏱️ …</div>'
 f'<a target="_blank" rel="noopener" class="btn" style="display:block;text-align:center;background:#1d9bf0;margin:6px 0" href="https://github.com/6penny6wise6/x-reply-dashboard/actions/workflows/scan-now.yml">🔍 Scan now</a>'
 f'<div class="cd" id="scanst">Scan status: checking…</div>'
)
out.append(f'<h2 style="font-size:18px;margin:18px 0 4px">💬 Viral posts to reply to <span class="b{" z" if not opps else ""}">{len(opps)}</span></h2><div class="q">Save the image, tap ↩️ Reply, then attach it. Mark done after you reply, and tap ❤️ Like. When both are done it moves to History.</div>')
if opps: out.append('<div class="likeall-scope" id="oppList">'+'<div class="likeall-bar" data-k="opps"><button type="button" class="btn likeall" data-label="❤️ already liked all these viral posts">❤️ already liked all these viral posts</button><div class="likeall-msg q"></div></div>')
for o in opps:
    st=o['stats']; link='https://x.com/intent/post?in_reply_to='+o['id']+'&text='+u.quote(o['caption'].strip(),safe='')
    llink='https://x.com/intent/like?tweet_id='+o['id']
    nt=f'<div class="q" style="color:#ffad1f">⚠️ {E(o["note"])}</div>' if o.get('note') else ''
    rp='1' if o.get('replied') else '0'; lk='1' if o.get('liked') else '0'
    out.append(
        f'<details class="oi" data-id="{o["id"]}" data-replied="{rp}" data-liked="{lk}" data-h="{E(o["author"])}" data-d="{E(o["caption"].strip())}" data-thread="{E(o["title"])}" data-url="https://x.com/{o["author"]}/status/{o["id"]}">'
        f'<summary><div class="t"><span class="tt">{E(o["title"])}</span>{('<span class="b" style="background:#00ba7c">🎯 target</span>') if o['_trank'] is not None else '<span class="b z ntag">not a target</span>'}</div>'
        f'<div class="st">@{E(o["author"])}</div>{statline("original post",st,o.get("stats_at"))}</summary>'
        f'<div class="in"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{o["author"]}/status/{o["id"]}">Open original post ↗</a></div>'
        f'<div class="d"><b>Q:</b> {E(o["question"])}<br><b>A:</b> {E(o["answer"])}</div>{nt}'
        + (f'<img src="{o["image"]}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0">' if o.get('image') else '<div class="q">no image for this one, the caption carries it</div>') +
        f'<div class="d">{E(o["caption"])}</div>{"<div class=\"dupflag\">⚠️ similar opening to another draft — rewrite before posting</div>" if o["id"] in dup_ids else ""}{chips(o.get("replied"), o.get("liked"))}'
        f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn replybtn" href="{link}" data-href="{link}">↩️ Post reply</a>'
        f'<a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}" data-href="{llink}">❤️ Like</a></div>'
        f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'o\')"> Mark done</label><a href="#" class="alreadyliked">❤️ already liked (skip X)</a></div>'
        f'</div></details>'
    )
if opps: out.append('</div>')
if not opps: out.append('<div class="q">Nothing new right now. The next scan runs within the hour, or tap Scan now.</div>')

out.append('<div id="t2sec" style="margin-top:26px;border-top:2px solid #2f3336;padding-top:8px"><h2 style="font-size:18px;margin:14px 0 4px">💬 People replying to your comments <span class="b">'+str(nrep)+'</span></h2><div class="cd" id="cd2">⏱️ …</div>')
allr=[dict(r,thread=s['title'],my_comment=s.get('my_comment','')) for s in secs for r in s['replies']]
allr.sort(key=lambda r:-(r.get('views') or 0))
bs=[allr[i:i+8] for i in range(0,len(allr),8)]
if bs:
    out.append('<h2 style="font-size:17px;margin:14px 0 6px">↩️ Manual posting (phone)</h2><div class="q">Tap ↩️ Post reply or ❤️ Like, or check Mark done to finish an item in one tap (locks both + moves to History). After Post reply without Mark done, confirm when you come back. Batch 1 is top-viewed.</div>')
for bi,b in enumerate(bs,1):
    out.append(f'<details class="batch"{" open" if bi==1 else ""}><summary><div class="t"><span class="tt">Batch {bi} of {len(bs)}</span><span class="prog" id="prog{bi}">0 of {len(b)} fully done</span><span class="b bcount">{len(b)}</span></div></summary><div class="in likeall-scope" id="batch{bi}">'+f'<div class="likeall-bar" data-k="b{bi}"><button type="button" class="btn likeall" data-label="❤️ already liked all in this batch">❤️ already liked all in this batch</button><div class="likeall-msg q"></div></div>')
    for r in b:
        rlink='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        llink='https://x.com/intent/like?tweet_id='+r['id']
        url=f'https://x.com/{r["handle"]}/status/{r["id"]}'
        rp='1' if r.get('replied') else '0'; lk='1' if r.get('liked') else '0'
        ver=f'<div class="q" style="color:#00ba7c">verified reply on X ✓</div>' if r.get('replied') and r.get('my_reply_id') else ''
        out.append(
            f'<div class="r bi" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"].strip())}" data-replied="{rp}" data-liked="{lk}" data-thread="{E(r["thread"])}" data-url="{url}">'
            f'<div class="q">{E(r["thread"])} · <b class="slab">their reply:</b> 👁 {fmt(r.get("views") or 0)}</div>'
            f'<div class="q"><a target="_blank" rel="noopener" href="{url}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div>'
            f'<div class="d">{E(r["draft"])}</div>{"<div class=\"dupflag\">⚠️ similar opening to another draft — rewrite before posting</div>" if r["id"] in dup_ids else ""}{chips(r.get("replied"), r.get("liked"))}{ver}'
            f'<div class="btn-row">'
            f'<a target="_blank" rel="noopener" class="btn replybtn" href="{rlink}" data-href="{rlink}">↩️ Post reply</a>'
            f'<a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}" data-href="{llink}">❤️ Like</a>'
            f'</div>'
            f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'r\')"> Mark done</label><a href="#" class="alreadyliked">❤️ already liked (skip X)</a>'
            f'<label><input type="checkbox" class="drop" onchange="this.closest(\'.bi\').style.opacity=this.checked?.35:\'\'"> Drop from Approve</label></div>'
            f'</div>'
        )
    out.append(
        f'<button class="btn btn-sec" style="width:100%;margin-top:8px" onclick="approve({bi},{len(bs)})">'
        f'📋 Copy APPROVE batch {bi} (for approver1)</button>'
        f'<div class="q" id="ok{bi}"></div></div></details>'
    )
if not bs:
    out.append('<div class="q">All caught up here. New comments show up after the next reply check.</div>')

if bs: out.append('<h2 style="font-size:17px;margin:18px 0 6px">📁 By thread</h2>')
for s in secs:
    n=len([r for r in s['replies'] if _actionable(r)]); st=s.get('stats')
    if n==0 and not s['replies']: continue
    if n==0: continue  # hide threads with nothing actionable
    sl=statline("your comment",st,s.get('stats_at'))
    oid=s.get('original_id'); oh=s.get('original_handle') or 'i'
    olab=(f"parent comment (@{E(oh)})" if s.get('original_is_reply') else "original post")
    sl+=statline(olab,s.get('original_stats'),s.get('original_stats_at'))
    olink=f' · <a target="_blank" rel="noopener" href="https://x.com/{E(oh)}/status/{E(oid)}">Open {"parent comment" if s.get("original_is_reply") else "original post"} ↗</a>' if oid else ''
    out.append(f'<details><summary><div class="t"><span class="tt">{E(s["title"])}</span><span class="b bcount">{n}</span></div>{sl}</summary><div class="in likeall-scope"><div class="q"><a target="_blank" rel="noopener" href="{s["my_comment"]}">Open my comment ↗</a>{olink}</div>'+f'<div class="likeall-bar" data-k="t{E(str(s.get("my_comment") or s["title"]).rstrip("/").split("/")[-1])}"><button type="button" class="btn likeall" data-label="❤️ already liked all in this thread">❤️ already liked all in this thread</button><div class="likeall-msg q"></div></div>')
    for r in s['replies']:
        link='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        llink='https://x.com/intent/like?tweet_id='+r['id']
        url=f'https://x.com/{r["handle"]}/status/{r["id"]}'
        rp='1' if r.get('replied') else '0'; lk='1' if r.get('liked') else '0'
        out.append(
            f'<div class="r ri" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"].strip())}" data-replied="{rp}" data-liked="{lk}" data-thread="{E(s["title"])}" data-url="{url}">'
            f'<div class="q"><a target="_blank" rel="noopener" href="{url}">@{E(r["handle"])}</a>: “{E(r["said"])}” · <b class="slab">their reply:</b> 👁 {fmt(r.get("views") or 0)}</div>'
            f'<div class="d">{E(r["draft"])}</div>{"<div class=\"dupflag\">⚠️ similar opening to another draft — rewrite before posting</div>" if r["id"] in dup_ids else ""}{chips(r.get("replied"), r.get("liked"))}'
            f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}" data-href="{llink}">❤️ Like</a>'
            f'<a target="_blank" rel="noopener" class="btn replybtn" href="{link}" data-href="{link}">↩️ Post reply</a></div>'
            f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'r\')"> Mark done</label><a href="#" class="alreadyliked">❤️ already liked (skip X)</a></div></div>'
        )
    out.append('</div></details>')

out.append(SJS.replace('__SS__',json.dumps(d.get('scan_status'))))
out.append(JS.replace('__BUILT__',str(int(time.time()*1000))).replace('__RIDDLE__',str(d.get('last_riddle_scan_ms') or 0)))

def ptm(p):
    m=re.match(r'\s*(\d{1,2})(?::(\d\d))?\s*([AaPp])',p.get('post_time') or '')
    if not m: return 9999
    h=int(m.group(1))%12+(12 if m.group(3).lower()=='p' else 0); return h*60+int(m.group(2) or 0)

P=['</div></div><div id="t3" style="display:none"><h2 style="font-size:18px;margin:14px 0 4px">📝 Post to our page <span class="b'+(' z' if not posts else '')+f'">{len(posts)}</span></h2><div class="cd">original posts count toward monetization, replies don\'t. today\'s slots are spaced 1 to 2 hours apart.</div><div class="q">🖼 Save image, tap 📤 Post now, then attach the image in the composer. Intents can\'t attach images. Nothing posts from this page.</div>']
_today=datetime.datetime.now(zoneinfo.ZoneInfo('America/Chicago')).strftime('%Y-%m-%d')
def _pday(p): return p.get('slot_date') or _today
_tmrw=(datetime.date.fromisoformat(_today)+datetime.timedelta(days=1)).isoformat()
_curgrp=None; _later_open=False
P.append('<div id="nowBar" style="display:none"></div><div class="q revnote">⚠️ if X shows Under review, your checkmark is probably being re-verified after the avatar change. wait it out, don\'t repost</div>')
for p in sorted(posts,key=lambda p:(_pday(p),ptm(p),p.get('created_ms',0))):
    link='https://x.com/intent/post?text='+u.quote(p['text'].strip(),safe='')
    img=p.get('image'); absimg=('/workspace/x-dashboard/'+img) if img else 'none'
    _dlab=datetime.date.fromisoformat(_pday(p)).strftime('%a %b %-d')+' · '
    pt=f'<span class="b{" z" if _pday(p)>_tmrw else ""}">🕒 {"today" if _pday(p)==_today else ("tomorrow" if _pday(p)==_tmrw else "")}{" · " if _pday(p) in (_today,_tmrw) else ""}{_dlab}{E(p["post_time"])}</span>' if p.get('post_time') else ''
    if _pday(p)!=_curgrp:
        _g=_pday(p)
        if _g>_tmrw and not _later_open:
            _nl=len([x for x in posts if _pday(x)>_tmrw])
            P.append(f'<details class="laterdays"><summary><div class="t"><span class="tt">📅 Later days</span><span class="b z">{_nl}</span></div><div class="st">4 a day at 8 AM, 12 PM, 4 PM, 8 PM CT</div></summary><div class="in">'); _later_open=True
        _gl=datetime.date.fromisoformat(_g).strftime('%A %b %-d')
        P.append(f'<h3 class="dayh">{"Today · " if _g==_today else ("Tomorrow · " if _g==_tmrw else ("Overdue · " if _g<_today else ""))}{_gl}</h3>')
        _curgrp=_g
    im=f'<img id="pi_{E(p["id"])}" src="{E(img)}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0"><div class="q">intents can\'t attach images, so save the image and attach it in the composer. <a class="sv" data-img="pi_{E(p["id"])}" data-name="{E(img.split("/")[-1])}" href="#" target="_blank" rel="noopener">🖼 Save image</a></div>' if img else ''
    nt=f'<div class="q" style="color:#ffad1f">💡 {E(p["note"])}</div>' if p.get('note') else ''
    if p.get('not_posted_note'): nt=f'<div class="q" style="color:#f4212e">↻ not posted: {E(p["not_posted_note"])}</div>'+nt
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
        f'data-ans="{E(ans_text)}" data-posted="{posted}" data-day="{E(_pday(p))}" data-sday="{E(datetime.date.fromisoformat(_pday(p)).strftime('%a %b %-d'))}" data-slot="{ptm(p)}" data-title="{E(p["title"])}" data-ptime="{E(p.get("post_time") or "")}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:17px"><span class="tt">{E(p["title"])}</span>{pt}</div>'
        f'{im}<div class="d">{E(p["text"])}</div>{nt}{ans_block}'
        f'<div class="btn-row">'
        f'<a target="_blank" rel="noopener" class="btn postbtn" href="{link}" data-href="{link}">📤 Post now</a>'
        f'<button type="button" class="btn" style="background:#00ba7c" onclick="copyText(this)">📋 Copy text</button>'
        f'</div>'
        f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'p\')"> Mark done</label></div>'
        f'<button type="button" class="btn btn-sec" style="width:100%;margin-top:4px" onclick="approvePost(this)">📋 Copy APPROVE (for approver1)</button>'
        f'<div class="q pok"></div></div>'
    )
if _later_open: P.append('</div></details>')
if not posts: P.append('<div class="q">new post ideas get added every morning</div>')
if posted_live:
    _pl=sorted(posted_live,key=lambda p:p.get('posted_at') or '',reverse=True)
    P.append(f'<details class="postedlist"><summary><div class="t"><span class="tt">✅ Posted today</span><span class="b z">{len(_pl)}</span></div><div class="st">already live on X, matched from your timeline</div></summary><div class="in">')
    for p in _pl:
        _url=p.get('url') or f"https://x.com/MrDonnieJackson/status/{p['posted_id']}"
        _at=''
        try:
            _at=datetime.datetime.fromisoformat((p.get('posted_at') or '').replace('Z','+00:00')).astimezone(zoneinfo.ZoneInfo('America/Chicago')).strftime('%-I:%M %p CT')
        except Exception: pass
        _ans=(p.get('answer') or '').strip()
        _al=('<a target="_blank" rel="noopener" class="btn btn-sec" href="https://x.com/intent/post?in_reply_to='+E(str(p['posted_id']))+'&text='+u.quote(_ans,safe='')+'">💡 Post answer</a>') if _ans else ''
        P.append(f'<div class="r"><div class="q"><b class="slab">{E(p["title"])}</b>{(" · posted "+_at) if _at else ""}{(" · slot "+E(p["post_time"])) if p.get("post_time") else ""}</div>'
                 f'<div class="d">{E(p["text"])}</div>{statline("original post",p.get("posted_stats"),p.get("posted_stats_at"))}'
                 f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn btn-sec" href="{E(_url)}">Open post ↗</a>{_al}</div></div>')
    P.append('</div></details>')
out.append(''.join(P))

H=['</div><div id="t4" style="display:none"><h2 style="font-size:18px;margin:14px 0 4px">🗂 History <span class="b'+(' z' if not history else '')+f'">{len(history)}</span></h2>'
   '<div class="cd">items you both replied to and liked. last 7 days. tap ↩ move back if one landed here by mistake.</div>'
   '<div id="histEmpty" class="q"'+('' if not history else ' style="display:none"')+'>Nothing here yet. Finish a reply and a like on the same comment and it shows up.</div>'
   '<div id="histList">']
for h in history:
    url=h.get('url') or f"https://x.com/{h.get('handle') or 'i'}/status/{h['id']}"
    H.append(
        f'<div class="r hc" data-id="{E(h["id"])}" data-server="1" data-h="{E(h.get("handle") or "")}" data-d="{E((h.get("draft") or "").strip())}" data-thread="{E(h.get("thread") or "")}" data-url="{E(url)}">'
        f'<div class="q">{E(h.get("thread") or "")} · @{E(h.get("handle") or "")}'
        + (f' · {E(h["replied_at"][:10])}' if h.get('replied_at') else '')
        + f'</div><div class="d">{E(h.get("draft") or h.get("said") or "")}</div>'
        f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn btn-sec" href="{E(url)}">Open comment ↗</a>'
        f'<button type="button" class="btn btn-sec" onclick="moveBack(\'{E(h["id"])}\')">↩ move back</button></div></div>'
    )
H.append('</div></div>')
out.append(''.join(H))

out.append(RESET.replace('__RESET__',json.dumps(d.get('post_reset') or {})))
out.append(MAN)
out.append(NOWJS)
out.append(
 '</div><button type="button" id="jumpLast" onclick="jumpToLast()">📍 Jump to where I left off</button>'
 '<script>function tab(n){var sec=(n==2);if(sec)n=1;for(const i of [1,2,3,4]){var t=document.getElementById("t"+i),b=document.getElementById("b"+i);if(t)t.style.display=i==n?"":"none";if(b)b.className=i==n?"on":""}var b2=document.getElementById("b2");if(b2)b2.className=sec?"on":"";if(sec){var b1=document.getElementById("b1");if(b1)b1.className="";var ts=document.getElementById("t2sec");if(ts)setTimeout(function(){ts.scrollIntoView({block:"start"})},30)}localStorage.tabv2=n}'
 'var _L=typeof getLast==="function"?getLast():null;'
 'if(_L&&_L.id&&typeof findItem==="function"&&findItem(_L.id)){jumpToLast()}'
 'else{tab(+(localStorage.tabv2||3));if(typeof showJump==="function")showJump()}'
 '</script></body></html>'
)
import seal; seal.publish('\n'.join(out))
print(total, 'history', len(history))
