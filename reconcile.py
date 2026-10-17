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
"""
from __future__ import annotations
import json, sys, os, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASH = HERE / 'dashboard.json'
DONNIE = '1691529217261948928'
HISTORY_DAYS = 7

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

def main(argv):
    paths = []
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
    pmap = parent_map(posts)
    dash = json.loads(DASH.read_text())
    marked, moved = apply(dash, pmap)
    DASH.write_text(json.dumps(dash, ensure_ascii=False, indent=1) + '\n')
    print(f'posts_in={len(posts)} parents_mapped={len(pmap)} newly_marked_replied={marked} moved_to_history={moved} history_len={len(dash.get("history") or [])}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
