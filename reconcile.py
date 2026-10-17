#!/usr/bin/env python3
"""Mark dashboard.json items that @MrDonnieJackson has already replied to.

Uses free public X search results only (the `x` MCP namespace). Never calls user-X.

Usage:
  1) Fetch recent replies (free x namespace), save JSON:
       search_posts_all
         query: from:MrDonnieJackson is:reply
         max_results: 100  (API may cap at 25; paginate with next_token)
         sort_order: recency
         expansions: referenced_tweets.id
         post.fields: created_at,referenced_tweets,author_id,text
     Write the tool result (or {data:[...]} pages concatenated) to a file.

  2) python3 reconcile.py path/to/donnie_replies.json
     Or: python3 reconcile.py --dir reconcile_data/

Updates each matching reply/opportunity in dashboard.json with:
  replied: true
  my_reply_id: <his reply status id>
  replied_at: <ISO timestamp>

Mirrors replied+liked items into history (last 7 days); keeps them in sections so the UI can move them back.
Does NOT commit dashboard.json (gitignored). Run build.py after.

TIMELINE FLOW (preferred, every run, FREE `x` namespace only):
  1) python3 reconcile.py plan
       prints the exact get_users_posts arguments (user id 1691529217261948928,
       start_time = start of today CT, since_id = newest reply already saved).
  2) call x.get_users_posts with those args (write_to_file), then
       python3 reconcile.py ingest <result file>
     It prints NEXT <pagination_token> (call again with that token and ingest
     again) or STOP <reason> (reached already-seen replies / start of today /
     no more pages). The API returns at most 25 posts per page.
  3) python3 reconcile.py apply
       marks dashboard.json items replied from the saved set
       (reconcile_data/replied_set.json) plus posted replies in post_queue.json,
       and marks queue replies whose parent was already answered as
       status "skipped_already_replied".
build.py also applies the saved set + post_queue on every build (no X reads).
"""
from __future__ import annotations
import json, sys, os, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASH = Path(os.environ.get('XDASH_DASH') or (HERE / 'dashboard.json'))
DONNIE = '1691529217261948928'
HISTORY_DAYS = 7
DATA = Path(os.environ.get('XDASH_RECON_DIR') or (HERE / 'reconcile_data'))
STATE = DATA / 'replied_set.json'
QUEUE = Path(os.environ.get('XDASH_QUEUE') or (HERE / 'post_queue.json'))
CT = None
try:
    import zoneinfo; CT = zoneinfo.ZoneInfo('America/Chicago')
except Exception:
    pass

def load_posts(paths):
    posts = []
    for p in paths:
        raw = Path(p).read_text()
        start = raw.find('{')
        if start < 0:
            start = raw.find('[')
        dec = json.JSONDecoder()
        obj, _ = dec.raw_decode(raw, start)
        if isinstance(obj, list):
            posts.extend(obj)
        elif isinstance(obj, dict):
            if 'data' in obj:
                posts.extend(obj.get('data') or [])
            elif 'posts' in obj:
                posts.extend(obj.get('posts') or [])
            else:
                # maybe a parent->reply map
                pass
    return posts

def parent_map(posts):
    """Map parent tweet id -> {my_reply_id, replied_at} (newest wins)."""
    m = {}
    for p in posts:
        rid = str(p.get('id') or '')
        if not rid:
            continue
        # prefer referenced_tweets replied_to
        parents = []
        for rt in p.get('referenced_tweets') or []:
            if rt.get('type') == 'replied_to' and rt.get('id'):
                parents.append(str(rt['id']))
        if not parents:
            continue
        created = p.get('created_at') or ''
        for parent in parents:
            prev = m.get(parent)
            if not prev or created > (prev.get('replied_at') or ''):
                m[parent] = {'my_reply_id': rid, 'replied_at': created}
    return m

def prune_history(hist, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    cut = now - dt.timedelta(days=HISTORY_DAYS)
    out = []
    for h in hist or []:
        ts = h.get('done_at') or h.get('replied_at') or ''
        try:
            t = dt.datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            t = now  # keep undated
        if t >= cut:
            out.append(h)
    # newest first
    out.sort(key=lambda h: h.get('done_at') or h.get('replied_at') or '', reverse=True)
    return out

def to_history(item, *, thread='', my_comment='', kind='reply'):
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return {
        'id': item['id'],
        'handle': item.get('handle') or item.get('author') or '',
        'said': item.get('said') or item.get('question') or '',
        'draft': item.get('draft') or item.get('caption') or '',
        'thread': thread,
        'my_comment': my_comment,
        'my_reply_id': item.get('my_reply_id') or '',
        'replied': True,
        'liked': True,
        'replied_at': item.get('replied_at') or '',
        'done_at': item.get('done_at') or now,
        'kind': kind,
        'url': f"https://x.com/{item.get('handle') or item.get('author') or 'i'}/status/{item['id']}",
    }

def apply(dash, pmap):
    marked = 0
    moved = 0
    hist = list(dash.get('history') or [])
    hist_ids = {h['id'] for h in hist}

    for s in dash.get('sections') or []:
        for r in s.get('replies') or []:
            rid = str(r['id'])
            if rid in pmap:
                info = pmap[rid]
                if not r.get('replied'):
                    marked += 1
                r['replied'] = True
                r['my_reply_id'] = info['my_reply_id']
                if info.get('replied_at'):
                    r['replied_at'] = info['replied_at']
            if r.get('replied') and r.get('liked') and rid not in hist_ids:
                hist.append(to_history(r, thread=s.get('title',''), my_comment=s.get('my_comment',''), kind='reply'))
                hist_ids.add(rid)
                moved += 1

    for o in dash.get('opportunities') or []:
        oid = str(o['id'])
        if oid in pmap:
            info = pmap[oid]
            if not o.get('replied'):
                marked += 1
            o['replied'] = True
            o['my_reply_id'] = info['my_reply_id']
            if info.get('replied_at'):
                o['replied_at'] = info['replied_at']
        if o.get('replied') and o.get('liked') and oid not in hist_ids:
            hist.append(to_history(o, thread=o.get('title',''), kind='opp'))
            hist_ids.add(oid)
            moved += 1

    dash['history'] = prune_history(hist)
    return marked, moved


# ---------- saved replied-to set ----------
def load_state():
    try:
        st = json.loads(STATE.read_text())
    except Exception:
        st = {}
    st.setdefault('parents', {}); st.setdefault('seen', [])
    return st

def save_state(st):
    DATA.mkdir(parents=True, exist_ok=True)
    st['seen'] = sorted(set(st.get('seen') or []), key=int)[-2000:]
    st['updated'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    tmp = STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(st, indent=1) + '\n'); os.replace(tmp, STATE)

def start_of_today_utc():
    now = dt.datetime.now(CT) if CT else dt.datetime.now(dt.timezone.utc)
    sod = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return sod.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def _raw_obj(path):
    raw = Path(path).read_text(); i = raw.find('{')
    if i < 0: return {}
    try:
        o, _ = json.JSONDecoder().raw_decode(raw, i); return o if isinstance(o, dict) else {}
    except Exception:
        return {}

def ingest(paths, st=None, mark_seen=True):
    """Merge result pages into the saved set. Returns (st, decision, info)."""
    st = st or load_state()
    seen = set(st['seen'])
    sod = start_of_today_utc()
    hit_seen = False; oldest = None; new = 0; token = None
    for p in paths:
        posts = [x for x in load_posts([p]) if str(x.get('author_id') or DONNIE) == DONNIE]
        for x in posts:
            rid = str(x.get('id') or '')
            if not rid: continue
            c = x.get('created_at') or ''
            if c and (oldest is None or c < oldest): oldest = c
            if rid in seen: hit_seen = True
            else:
                new += 1
                if mark_seen: seen.add(rid)
        for parent, info in parent_map(posts).items():
            prev = st['parents'].get(parent)
            if not prev or (info.get('replied_at') or '') > (prev.get('replied_at') or ''):
                st['parents'][parent] = dict(info, source='x_timeline' if mark_seen else 'x_search')
        token = ((_raw_obj(p).get('meta') or {}).get('next_token')) or None
    st['seen'] = list(seen)
    if not mark_seen:
        return st, 'SEEDED', {'new_posts': new, 'oldest': oldest, 'parents_saved': len(st['parents'])}
    ids = [int(i) for i in seen] or [0]
    st['newest_id'] = str(max(ids)) if max(ids) else st.get('newest_id')
    if hit_seen: dec = 'STOP reached replies already saved'
    elif oldest and oldest < sod.replace('Z', '.000Z'): dec = 'STOP reached start of today'
    elif not token: dec = 'STOP no more pages'
    else: dec = 'NEXT ' + token
    if dec.startswith('STOP'): st['last_full_check'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return st, dec, {'new_posts': new, 'oldest': oldest, 'parents_saved': len(st['parents'])}

def plan(st=None):
    st = st or load_state()
    args = {'id': DONNIE, 'max_results': 100, 'start_time': start_of_today_utc(),
            'post.fields': 'created_at,referenced_tweets,in_reply_to_user_id,conversation_id',
            'expansions': 'referenced_tweets.id'}
    # since_id only when the saved newest reply is from today, so the API returns just newer posts
    nid = st.get('newest_id')
    if nid and st.get('last_full_check', '') >= start_of_today_utc():
        args['since_id'] = nid
    return args

def queue_parents():
    """Parents answered according to post_queue.json (status posted with a url)."""
    m = {}
    try:
        q = json.loads(QUEUE.read_text())
    except Exception:
        return m
    for it in q if isinstance(q, list) else []:
        if it.get('kind') != 'reply' or it.get('status') != 'posted': continue
        tu = it.get('target_url') or ''; url = it.get('url') or ''
        pid = tu.rstrip('/').split('/')[-1] if '/status/' in tu else ''
        mid = url.rstrip('/').split('/')[-1] if '/status/' in url else ''
        if pid.isdigit():
            m[pid] = {'my_reply_id': mid, 'replied_at': it.get('posted_at') or '', 'source': 'post_queue'}
    return m

def replied_parents(st=None):
    st = st or load_state()
    m = dict(queue_parents())
    m.update(st.get('parents') or {})
    return m

def apply_saved(dash):
    """Used by build.py on every build: no X reads, just saved set + queue."""
    return apply(dash, replied_parents())

def mark_queue(pm):
    try:
        q = json.loads(QUEUE.read_text())
    except Exception:
        return 0
    n = 0
    for it in q if isinstance(q, list) else []:
        if it.get('kind') != 'reply' or it.get('status') != 'pending': continue
        tu = it.get('target_url') or ''
        pid = tu.rstrip('/').split('/')[-1] if '/status/' in tu else ''
        if pid in pm:
            it['status'] = 'skipped_already_replied'
            it['note'] = ((it.get('note') or '') + f" | already replied ({pm[pid].get('my_reply_id') or 'see timeline'})").strip(' |')
            n += 1
    if n:
        tmp = QUEUE.with_suffix('.tmp'); tmp.write_text(json.dumps(q, ensure_ascii=False, indent=1) + '\n'); os.replace(tmp, QUEUE)
    return n

def _apply_cli():
    pm = replied_parents()
    dash = json.loads(DASH.read_text())
    marked, moved = apply(dash, pm)
    DASH.write_text(json.dumps(dash, ensure_ascii=False, indent=1) + '\n')
    qn = mark_queue(pm)
    print(f'parents_known={len(pm)} newly_marked_replied={marked} moved_to_history={moved} queue_marked_already_replied={qn}')
    return 0

def main(argv):
    paths = []
    cmd = argv[1] if len(argv) >= 2 else ''
    if cmd == 'plan':
        print(json.dumps(plan())); return 0
    if cmd == 'ingest':
        st, dec, info = ingest(argv[2:]); save_state(st)
        print(dec); print(json.dumps(info)); return 0
    if cmd == 'apply':
        return _apply_cli()
    if cmd == 'seed':  # one-off: seed saved set from older search result files
        st, dec, info = ingest(argv[2:], mark_seen=False); save_state(st); print(json.dumps(info)); return 0
    if len(argv) >= 2 and argv[1] == '--dir':
        d = Path(argv[2] if len(argv) > 2 else HERE / 'reconcile_data')
        paths = sorted(str(p) for p in d.glob('*.json'))
    elif len(argv) >= 2:
        paths = argv[1:]
    else:
        default = HERE / 'reconcile_data' / 'donnie_replies.json'
        if default.exists():
            paths = [str(default)]
        else:
            print('Usage: reconcile.py <search_results.json> [...]', file=sys.stderr)
            return 2
    posts = load_posts(paths)
    st, _, _ = ingest(paths, mark_seen=False); save_state(st)
    pmap = replied_parents(st)
    dash = json.loads(DASH.read_text())
    marked, moved = apply(dash, pmap)
    DASH.write_text(json.dumps(dash, ensure_ascii=False, indent=1) + '\n')
    print(f'posts_in={len(posts)} parents_mapped={len(pmap)} newly_marked_replied={marked} moved_to_history={moved} history_len={len(dash.get("history") or [])}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
