#!/usr/bin/env python3
"""Refresh "your comment" + "original post" stats for every tracked section.

Free `x` namespace only (never user-X). One call covers up to 100 sections:
  1) python3 original_stats.py --ids        -> prints comma-separated my_comment + opportunity ids
  2) x.get_posts_by_ids  ids=<that list>
       post.fields=public_metrics,referenced_tweets,author_id,created_at
       expansions=referenced_tweets.id,referenced_tweets.id.author_id
       user.fields=username
     (save the tool result to a file, e.g. with write_to_file)
  3) python3 original_stats.py <result file>   -> updates dashboard.json, then run build.py

Per section it sets: stats + stats_at (his comment), original_id, original_handle,
original_is_reply, original_stats + original_stats_at (the post his comment replied to).
Opportunities in the id list also get fresh stats + stats_at (they ARE the original post).
"""
import json, sys, re, datetime as dt
from pathlib import Path
DASH = Path(__file__).resolve().parent / 'dashboard.json'

def cid(s):
    m = re.search(r'status/(\d+)', s.get('my_comment') or '')
    return m.group(1) if m else ''

def ms(m):
    m = m or {}
    return {'views': m.get('impression_count', 0), 'likes': m.get('like_count', 0), 'replies': m.get('reply_count', 0)}

def main():
    d = json.loads(DASH.read_text())
    if sys.argv[1:] == ['--ids']:
        ids = [i for i in (cid(s) for s in d['sections']) if i]
        ids += [o['id'] for o in d.get('opportunities') or [] if not o.get('skip')]
        print(','.join(dict.fromkeys(ids))); return
    raw = Path(sys.argv[1]).read_text(); i = raw.find('{')
    o, _ = json.JSONDecoder().raw_decode(raw, i)
    inc = o.get('includes') or {}
    parents = {p['id']: p for p in (inc.get('posts') or inc.get('tweets') or [])}
    users = {u['id']: u.get('username', '') for u in inc.get('users') or []}
    mine = {p['id']: p for p in o.get('data') or []}
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000); n = 0
    for s in d['sections']:
        p = mine.get(cid(s))
        if not p: continue
        s['stats'] = ms(p.get('public_metrics')); s['stats_at'] = now_ms
        par = next((r['id'] for r in p.get('referenced_tweets') or [] if r.get('type') == 'replied_to'), None)
        if not par: continue
        s['original_id'] = par
        pp = parents.get(par)
        if pp:
            s['original_handle'] = users.get(pp.get('author_id'), s.get('original_handle', ''))
            s['original_is_reply'] = any(r.get('type') == 'replied_to' for r in pp.get('referenced_tweets') or [])
            s['original_stats'] = ms(pp.get('public_metrics')); s['original_stats_at'] = now_ms
            n += 1
    for op in d.get('opportunities') or []:
        p = mine.get(op.get('id'))
        if p:
            op['stats'] = ms(p.get('public_metrics')); op['stats_at'] = now_ms
    DASH.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    print('updated original_stats for', n, 'sections')

if __name__ == '__main__':
    main()
