import json, html, urllib.parse as u, datetime, zoneinfo, re, time
d=json.load(open('dashboard.json'))
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
def fmt(n): return f"{n/1000:.1f}K" if n>=1000 else str(n)
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

# Manual mode + reconcile/history
MAN=r'''<script>
function _lsGet(k,fb){try{var v=localStorage.getItem(k);return v?JSON.parse(v):fb}catch(e){return fb}}
function _lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function isDone(kind,id){var m=_lsGet("xdash_done",{});return !!m[kind+":"+id]}
function setDone(kind,id,on){var m=_lsGet("xdash_done",{});if(on)m[kind+":"+id]=1;else delete m[kind+":"+id];_lsSet("xdash_done",m)}
function getPosted(id){var m=_lsGet("xdash_posted",{});return m[id]||""}
function setPosted(id,sid){var m=_lsGet("xdash_posted",{});if(sid)m[id]=sid;else delete m[id];_lsSet("xdash_posted",m)}
function likedMap(){return _lsGet("xdash_liked",{})}
function setLiked(id,on){var m=likedMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_liked",m)}
function repliedMap(){return _lsGet("xdash_replied",{})}
function setRepliedLocal(id,on){var m=repliedMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_replied",m)}
function backMap(){return _lsGet("xdash_back",{})}
function setBack(id,on){var m=backMap();if(on)m[id]=1;else delete m[id];_lsSet("xdash_back",m)}
function itemReplied(el){if(!el)return false;return el.dataset.replied==="1"||!!repliedMap()[el.dataset.id]||!!isDone("r",el.dataset.id)||!!isDone("o",el.dataset.id)}
function itemLiked(el){if(!el)return false;return el.dataset.liked==="1"||!!likedMap()[el.dataset.id]}
function itemForcedBack(el){return !!(el&&backMap()[el.dataset.id])}
function applyDone(el,on){if(!el)return;el.classList.toggle("done",!!on);var cb=el.querySelector(".mdone");if(cb)cb.checked=!!on}
function paintChips(el){var box=el.querySelector(".chips");if(!box)return;var r=itemReplied(el),l=itemLiked(el);
 box.innerHTML='<span class="chip '+(r?"ok":"no")+'">'+(r?"↩️ replied ✓":"↩️ not replied")+'</span>'+
  '<span class="chip '+(l?"ok":"no")+'">'+(l?'❤️ liked ✓ <button type="button" class="undo-like" onclick="undoLike(event)">undo</button>':"❤️ not liked")+'</span>'}
function markDone(cb,kind){var sel=kind==="r"?".bi,.ri":kind==="o"?".oi":".pc";var el=cb.closest(sel);var id=el&&el.dataset.id;if(!id)return;
 setDone(kind,id,cb.checked);if(kind==="r"||kind==="o"){setRepliedLocal(id,cb.checked);if(cb.checked)setBack(id,false)}
 applyDone(el,cb.checked);paintChips(el);rememberFrom(el);reconcileItem(el);if(el.classList.contains("bi")){var b=el.closest(".batch");if(b)updProg(b)}}
function undoLike(ev){ev.preventDefault();ev.stopPropagation();var el=ev.target.closest(".bi,.ri,.oi,.pc");if(!el)return;setLiked(el.dataset.id,false);paintChips(el);reconcileItem(el);rememberFrom(el)}
function onLikeClick(a){var el=a.closest(".bi,.ri,.oi");if(!el)return;setLiked(el.dataset.id,true);setBack(el.dataset.id,false);paintChips(el);rememberFrom(el);reconcileItem(el)}
function updProg(batch){if(!batch)return;var items=[].slice.call(batch.querySelectorAll(".bi")),act=items.filter(function(e){return !e.classList.contains("hist")});
 var done=act.filter(function(e){return itemReplied(e)&&itemLiked(e)}).length;
 var el=batch.querySelector(".prog");if(el)el.textContent=done+" of "+act.length+" fully done";
 var badge=batch.querySelector(".bcount");if(badge)badge.textContent=act.length;batch.style.display=act.length?"":"none"}
function updThread(det){if(!det||det.classList.contains("batch")||det.classList.contains("oi"))return;var items=[].slice.call(det.querySelectorAll(".ri"));
 var act=items.filter(function(e){return !e.classList.contains("hist")});var badge=det.querySelector(".bcount");if(badge){badge.textContent=act.length?act.length:"✓";badge.classList.toggle("z",!act.length)}
 if(!act.length&&items.length)det.style.display="none"}
function histList(){return document.getElementById("histList")}
function ensureHistCard(el){var id=el.dataset.id,list=histList();if(!list)return null;var existing=list.querySelector('.hc[data-id="'+id+'"]');if(existing)return existing;
 var h=document.createElement("div");h.className="r hc";h.dataset.id=id;
 var handle=el.dataset.h||"";var draft=(el.dataset.d||el.querySelector(".d")&&el.querySelector(".d").textContent||"").trim();
 var url=el.dataset.url||("#");
 h.innerHTML='<div class="q">'+(el.dataset.thread||"")+' · @'+handle+'</div><div class="d">'+draft.replace(/[<>&]/g,function(c){return({"<":"&lt;",">":"&gt;","&":"&amp;"}[c])})+'</div>'+
  '<div class="btn-row"><a target="_blank" rel="noopener" class="btn btn-sec" href="'+url+'">Open comment ↗</a>'+
  '<button type="button" class="btn btn-sec" onclick="moveBack(\''+id+'\')">↩ move back</button></div>';
 list.insertBefore(h,list.firstChild);return h}
function reconcileItem(el){if(!el||!el.dataset.id)return;paintChips(el);var both=itemReplied(el)&&itemLiked(el),back=itemForcedBack(el);
 if(both&&!back){el.classList.add("hist");el.style.display="none";ensureHistCard(el)}
 else{el.classList.remove("hist");el.style.display="";var list=histList();if(list){var hc=list.querySelector('.hc[data-id="'+el.dataset.id+'"]');if(hc&&!(el.dataset.replied==="1"&&el.dataset.liked==="1"&&!back)){/* keep server hist */}}}}
function moveBack(id){setBack(id,true);setLiked(id,false);setRepliedLocal(id,false);setDone("r",id,false);setDone("o",id,false);
 document.querySelectorAll('.bi[data-id="'+id+'"], .ri[data-id="'+id+'"], .oi[data-id="'+id+'"]').forEach(function(el){el.classList.remove("hist");el.style.display="";applyDone(el,false);paintChips(el);rememberFrom(el)});
 var list=histList();if(list){var hc=list.querySelector('.hc[data-id="'+id+'"]');if(hc&&!hc.dataset.server)hc.remove()}
 document.querySelectorAll(".batch").forEach(updProg);document.querySelectorAll("#t2 details").forEach(updThread);updHistEmpty();showJump()}
function updHistEmpty(){var list=histList(),empty=document.getElementById("histEmpty"),n=list?list.querySelectorAll(".hc").length:0;
 if(empty)empty.style.display=n? "none":"";var badge=document.getElementById("histBadge");if(badge){badge.textContent=n;badge.classList.toggle("z",!n)}}
function reconcileAll(){document.querySelectorAll(".bi,.ri,.oi").forEach(function(el){paintChips(el);var both=itemReplied(el)&&itemLiked(el),back=itemForcedBack(el);
  if(both&&!back){el.classList.add("hist");el.style.display="none";ensureHistCard(el)}else{el.classList.remove("hist");if(el.style.display==="none"&&!el.classList.contains("hist"))el.style.display=""}});
 document.querySelectorAll(".batch").forEach(updProg);document.querySelectorAll("#t2 details").forEach(updThread);updHistEmpty();
 // if last-selected moved to history, clear highlight silently
 var L=getLast();if(L&&L.id){var el=findItem(L.id);if(!el||el.classList.contains("hist")||el.style.display==="none"){clearHere();showJump()}}}
function parseStatusId(v){if(!v)return "";v=(""+v).trim();var m=v.match(/(?:status\/|statuses\/|=)(\d{5,})/);if(m)return m[1];if(/^\d{5,}$/.test(v))return v;return ""}
function savePosted(inp){var c=inp.closest(".pc"),id=c.dataset.id,sid=parseStatusId(inp.value);inp.value=sid;setPosted(id,sid);showAns(c,sid);rememberFrom(c)}
function showAns(c,sid){var wrap=c.querySelector(".answrap");if(!wrap)return;if(sid){wrap.style.display="";var a=wrap.querySelector("a.ansbtn");if(a){var ans=(c.dataset.ans||"").trim();a.href="https://x.com/intent/post?in_reply_to="+encodeURIComponent(sid)+"&text="+encodeURIComponent(ans)}}else wrap.style.display="none"}
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
function clearHere(){document.querySelectorAll(".here").forEach(function(e){e.classList.remove("here");var t=e.querySelector(".here-tag");if(t)t.remove()})}
function applyHere(el){clearHere();if(!el)return;el.classList.add("here");if(!el.querySelector(".here-tag")){var tag=document.createElement("div");tag.className="here-tag";tag.textContent="📍 you were here";el.insertBefore(tag,el.firstChild)}}
function itemTab(el){var pane=el&&el.closest("#t1,#t2,#t3,#t4");return pane?+pane.id.slice(1):+(localStorage.tabv2||3)}
function rememberFrom(el){if(!el)return;var item=(el.classList&&(el.classList.contains("bi")||el.classList.contains("pc")||el.classList.contains("oi")||el.classList.contains("ri")||el.classList.contains("hc")))?el:el.closest(".bi,.pc,.oi,.ri,.hc");if(!item||!item.dataset.id)return;var tabn=itemTab(item);setLast(item.dataset.id,tabn);applyHere(item)}
function jumpToLast(){var L=getLast();if(!L||!L.id)return;var el=findItem(L.id);if(!el){showJump();return}var tabn=L.tab||itemTab(el);if(typeof tab==="function")tab(tabn);var d=el.closest("details");while(d){d.open=true;var p=d.parentElement;d=p?p.closest("details"):null}applyHere(el);setTimeout(function(){try{el.scrollIntoView({behavior:"smooth",block:"center"})}catch(e){try{el.scrollIntoView(true)}catch(x){}}},60);showJump()}
function showJump(){var btn=document.getElementById("jumpLast");if(!btn)return;var L=getLast();btn.style.display=(L&&L.id&&findItem(L.id))?"":"none"}
document.addEventListener("click",function(e){var t=e.target;if(!t||!t.closest)return;if(t.closest("#jumpLast")||t.closest(".tabs")||t.closest(".ctl"))return;
 var like=t.closest("a.likebtn");if(like)onLikeClick(like);
 var item=t.closest(".bi,.pc,.oi,.ri,.hc");if(item)rememberFrom(item)},true);
document.addEventListener("visibilitychange",function(){if(document.visibilityState==="visible")jumpToLast()});
window.addEventListener("pageshow",function(){jumpToLast()});
(function(){
 document.querySelectorAll(".bi,.ri").forEach(function(e){if(isDone("r",e.dataset.id)||repliedMap()[e.dataset.id])applyDone(e,true)});
 document.querySelectorAll(".oi").forEach(function(e){if(isDone("o",e.dataset.id)||repliedMap()[e.dataset.id])applyDone(e,true)});
 document.querySelectorAll(".pc").forEach(function(c){
  if(isDone("p",c.dataset.id))applyDone(c,true);
  var sid=getPosted(c.dataset.id)||(c.dataset.posted||"");
  var inp=c.querySelector(".posturl");if(inp&&sid)inp.value=sid;
  showAns(c,sid);
 });
 document.querySelectorAll("a.sv").forEach(function(a){var i=document.getElementById(a.dataset.img);if(i){a.href=i.src;a.download=a.dataset.name}});
 reconcileAll();showJump();
})();
</script>'''

opps=d.get('opportunities',[])
posts=d.get('posts',[])
history=d.get('history',[])
nrep=total
nhist=len(history)

CSS_EXTRA = (
".chips{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}"
".chip{font-size:12px;font-weight:600;border-radius:99px;padding:3px 8px}"
".chip.ok{background:rgba(0,186,124,.2);color:#00ba7c}.chip.no{background:#2f3336;color:#8b98a5}"
".undo-like{background:none;border:0;color:#8b98a5;font-size:11px;text-decoration:underline;padding:0 0 0 4px;cursor:pointer}"
".here{border-left:4px solid #ffd400!important;background:rgba(255,212,0,.14)!important;box-shadow:inset 4px 0 0 #ffd400}"
".here-tag{display:inline-block;background:#ffd400;color:#0f1419;font-size:12px;font-weight:700;border-radius:99px;padding:2px 8px;margin:0 0 8px}"
"#jumpLast{position:fixed;bottom:16px;right:16px;z-index:98;background:#ffd400;color:#0f1419;border:0;border-radius:99px;padding:12px 16px;font-size:14px;font-weight:700;box-shadow:0 4px 16px rgba(0,0,0,.45);display:none}"
".hc{background:#16202a;border-radius:14px;padding:12px;margin:10px 0;border:0}"
)

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
<div class="ctl"><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">Expand all</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">Collapse all</button></div>''']

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
for o in opps:
    st=o['stats']; link='https://x.com/intent/post?in_reply_to='+o['id']+'&text='+u.quote(o['caption'].strip(),safe='')
    llink='https://x.com/intent/like?tweet_id='+o['id']
    nt=f'<div class="q" style="color:#ffad1f">⚠️ {E(o["note"])}</div>' if o.get('note') else ''
    rp='1' if o.get('replied') else '0'; lk='1' if o.get('liked') else '0'
    out.append(
        f'<details class="oi" data-id="{o["id"]}" data-replied="{rp}" data-liked="{lk}" data-h="{E(o["author"])}" data-d="{E(o["caption"].strip())}" data-thread="{E(o["title"])}" data-url="https://x.com/{o["author"]}/status/{o["id"]}">'
        f'<summary><div class="t"><span class="tt">{E(o["title"])}</span><span class="b">new</span></div>'
        f'<div class="st">@{E(o["author"])} · 👁 {fmt(st["views"])} · ❤️ {st["likes"]} · 💬 {st["replies"]}</div></summary>'
        f'<div class="in"><div class="q"><a target="_blank" rel="noopener" href="https://x.com/{o["author"]}/status/{o["id"]}">Open original post ↗</a></div>'
        f'<div class="d"><b>Q:</b> {E(o["question"])}<br><b>A:</b> {E(o["answer"])}</div>{nt}'
        f'<img src="{o["image"]}" style="width:100%;border-radius:10px;background:#fff;margin:8px 0">'
        f'<div class="d">{E(o["caption"])}</div>{chips(o.get("replied"), o.get("liked"))}'
        f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn" href="{link}">↩️ Post reply</a>'
        f'<a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}">❤️ Like</a></div>'
        f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'o\')"> Mark done (replied)</label></div>'
        f'</div></details>'
    )
if not opps: out.append('<div class="q">Nothing new right now. The next scan runs within the hour, or tap Scan now.</div>')

out.append('</div><div id="t2" style="display:none"><div class="cd" id="cd2">⏱️ …</div>')
allr=[dict(r,thread=s['title'],my_comment=s.get('my_comment','')) for s in secs for r in s['replies']]
allr.sort(key=lambda r:-(r.get('views') or 0))
bs=[allr[i:i+8] for i in range(0,len(allr),8)]
if bs:
    out.append('<h2 style="font-size:17px;margin:14px 0 6px">↩️ Manual posting (phone)</h2><div class="q">Tap ↩️ Post reply, then check Mark done. Tap ❤️ Like (it remembers). When both chips are green it moves to 🗂 History. Batch 1 is top-viewed.</div>')
for bi,b in enumerate(bs,1):
    out.append(f'<details class="batch"{" open" if bi==1 else ""}><summary><div class="t"><span class="tt">Batch {bi} of {len(bs)}</span><span class="prog" id="prog{bi}">0 of {len(b)} fully done</span><span class="b bcount">{len(b)}</span></div></summary><div class="in" id="batch{bi}">')
    for r in b:
        rlink='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        llink='https://x.com/intent/like?tweet_id='+r['id']
        url=f'https://x.com/{r["handle"]}/status/{r["id"]}'
        rp='1' if r.get('replied') else '0'; lk='1' if r.get('liked') else '0'
        ver=f'<div class="q" style="color:#00ba7c">verified reply on X ✓</div>' if r.get('replied') and r.get('my_reply_id') else ''
        out.append(
            f'<div class="r bi" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"].strip())}" data-replied="{rp}" data-liked="{lk}" data-thread="{E(r["thread"])}" data-url="{url}">'
            f'<div class="q">{E(r["thread"])} · 👁 {fmt(r.get("views") or 0)}</div>'
            f'<div class="q"><a target="_blank" rel="noopener" href="{url}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div>'
            f'<div class="d">{E(r["draft"])}</div>{chips(r.get("replied"), r.get("liked"))}{ver}'
            f'<div class="btn-row">'
            f'<a target="_blank" rel="noopener" class="btn" href="{rlink}">↩️ Post reply</a>'
            f'<a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}">❤️ Like</a>'
            f'</div>'
            f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'r\')"> Mark done (replied)</label>'
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
    sl=f'<div class="st">👁 {fmt(st["views"])} views · ❤️ {st["likes"]} · 💬 {st["replies"]} replies</div>' if st else ''
    out.append(f'<details><summary><div class="t"><span class="tt">{E(s["title"])}</span><span class="b bcount">{n}</span></div>{sl}</summary><div class="in"><div class="q"><a target="_blank" rel="noopener" href="{s["my_comment"]}">Open my comment ↗</a></div>')
    for r in s['replies']:
        link='https://x.com/intent/post?in_reply_to='+r['id']+'&text='+u.quote(r['draft'].strip(),safe='')
        llink='https://x.com/intent/like?tweet_id='+r['id']
        url=f'https://x.com/{r["handle"]}/status/{r["id"]}'
        rp='1' if r.get('replied') else '0'; lk='1' if r.get('liked') else '0'
        out.append(
            f'<div class="r ri" data-id="{r["id"]}" data-h="{E(r["handle"])}" data-d="{E(r["draft"].strip())}" data-replied="{rp}" data-liked="{lk}" data-thread="{E(s["title"])}" data-url="{url}">'
            f'<div class="q"><a target="_blank" rel="noopener" href="{url}">@{E(r["handle"])}</a>: “{E(r["said"])}”</div>'
            f'<div class="d">{E(r["draft"])}</div>{chips(r.get("replied"), r.get("liked"))}'
            f'<div class="btn-row"><a target="_blank" rel="noopener" class="btn likebtn" style="flex:0 0 32%;background:#f91880" href="{llink}">❤️ Like</a>'
            f'<a target="_blank" rel="noopener" class="btn" href="{link}">↩️ Post reply</a></div>'
            f'<div class="mdrow"><label><input type="checkbox" class="mdone" onchange="markDone(this,\'r\')"> Mark done (replied)</label></div></div>'
        )
    out.append('</div></details>')

out.append(SJS.replace('__SS__',json.dumps(d.get('scan_status'))))
out.append(JS.replace('__BUILT__',str(int(time.time()*1000))).replace('__RIDDLE__',str(d.get('last_riddle_scan_ms') or 0)))

def ptm(p):
    m=re.match(r'\s*(\d{1,2})(?::(\d\d))?\s*([AaPp])',p.get('post_time') or '')
    if not m: return 9999
    h=int(m.group(1))%12+(12 if m.group(3).lower()=='p' else 0); return h*60+int(m.group(2) or 0)

P=['</div><div id="t3" style="display:none"><h2 style="font-size:18px;margin:14px 0 4px">📝 Post to our page <span class="b'+(' z' if not posts else '')+f'">{len(posts)}</span></h2><div class="cd">original posts count toward monetization, replies don\'t. aim for 1 to 3 a day.</div><div class="q">🖼 Save image, tap 📤 Post now, then attach the image in the composer. Intents can\'t attach images. Nothing posts from this page.</div>']
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

out.append(MAN)
out.append(
 '</div><button type="button" id="jumpLast" onclick="jumpToLast()">📍 Jump to where I left off</button>'
 '<script>function tab(n){for(const i of [1,2,3,4]){var t=document.getElementById("t"+i),b=document.getElementById("b"+i);if(t)t.style.display=i==n?"":"none";if(b)b.className=i==n?"on":""}localStorage.tabv2=n}'
 'var _L=typeof getLast==="function"?getLast():null;'
 'if(_L&&_L.id&&typeof findItem==="function"&&findItem(_L.id)){jumpToLast()}'
 'else{tab(+(localStorage.tabv2||3));if(typeof showJump==="function")showJump()}'
 '</script></body></html>'
)
import seal; seal.publish('\n'.join(out))
print(total, 'history', len(history))
