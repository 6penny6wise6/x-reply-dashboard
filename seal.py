"""Encrypts the dashboard before publishing. build.py must call seal.publish(html)
instead of writing index.html itself. Never writes plaintext to any tracked file."""
import os, re, sys, json, base64, mimetypes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = os.path.dirname(os.path.abspath(__file__))
PW_FILE = '/home/box/cli-config/dashboard_password'
ITER = 600000
INFO = b'x-reply-dashboard v1'
MARK = 'XDASH-ENCRYPTED-V1'
b64 = lambda b: base64.b64encode(b).decode()

def password():
    p = os.environ.get('DASHBOARD_PASSWORD')
    if not p and os.path.exists(PW_FILE):
        p = open(PW_FILE).read().strip()
    if not p:
        sys.exit('FATAL: no DASHBOARD_PASSWORD env var and no ' + PW_FILE + '. Refusing to publish plaintext.')
    return p

def kdf_salt():
    # Stable public salt for the PBKDF2 master key, so the device can remember the
    # derived key across builds. Each build still uses a fresh random salt (HKDF) + IV.
    f = os.path.join(HERE, 'kdf_salt.txt')
    if not os.path.exists(f):
        open(f, 'w').write(b64(os.urandom(16)))
    return base64.b64decode(open(f).read().strip())

def master_key(pw, salt):
    return PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw.encode())

def page_key(mk, bsalt):
    return HKDF(hashes.SHA256(), 32, bsalt, INFO).derive(mk)

_CACHE = {}
def embed_images(html):
    def rep(m):
        p = os.path.join(HERE, m.group(2))
        if not os.path.exists(p):
            return m.group(0)
        if p not in _CACHE:
            try:
                from PIL import Image
                import io
                im = Image.open(p).convert('RGB')
                im.thumbnail((1080, 1350))
                buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82, optimize=True, progressive=True)
                _CACHE[p] = 'data:image/jpeg;base64,' + b64(buf.getvalue())
            except Exception:
                mt = mimetypes.guess_type(p)[0] or 'image/png'
                _CACHE[p] = 'data:' + mt + ';base64,' + b64(open(p, 'rb').read())
        return m.group(1) + _CACHE[p] + '"'
    return re.sub(r'(src=")(img/[^"]+)"', rep, html)

def encrypt(html):
    salt = kdf_salt(); bsalt = os.urandom(16); iv = os.urandom(12)
    key = page_key(master_key(password(), salt), bsalt)
    ct = AESGCM(key).encrypt(iv, embed_images(html).encode(), None)
    return {'v': 1, 'iter': ITER, 'salt': b64(salt), 'bsalt': b64(bsalt), 'iv': b64(iv), 'ct': b64(ct)}

def decrypt(blob, pw):
    mk = master_key(pw, base64.b64decode(blob['salt']))
    key = page_key(mk, base64.b64decode(blob['bsalt']))
    return AESGCM(key).decrypt(base64.b64decode(blob['iv']), base64.b64decode(blob['ct']), None).decode()

SHELL = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<!-- __MARK__ -->
<title>Reply Dashboard</title>
<style>body{font-family:-apple-system,system-ui;background:#0f1419;color:#e7e9ea;padding:16px;max-width:420px;margin:15vh auto;text-align:center}
input{width:100%;box-sizing:border-box;padding:12px;font-size:17px;border-radius:12px;border:1px solid #2f3336;background:#16202a;color:#e7e9ea;margin:12px 0}
button{width:100%;background:#1d9bf0;color:#fff;border:0;border-radius:99px;padding:12px;font-size:17px;font-weight:600}#m{color:#f4212e;min-height:1.4em;margin-top:10px}</style></head>
<body><div id="f" style="display:none"><h1>🔒 Reply Dashboard</h1><form onsubmit="go(event)"><input id="p" type="password" autocomplete="current-password" placeholder="Password" autofocus><button>Unlock</button></form><div id="m"></div></div><div id="w">🔓 Unlocking…</div>
<script>
var B=__BLOB__,K="xdash_key_v1";
function ub(s){return Uint8Array.from(atob(s),function(c){return c.charCodeAt(0)})}
function bu(a){var s="";new Uint8Array(a).forEach(function(c){s+=String.fromCharCode(c)});return btoa(s)}
async function open_(mk){var s=crypto.subtle,h=await s.importKey("raw",mk,"HKDF",false,["deriveKey"]);
 var k=await s.deriveKey({name:"HKDF",hash:"SHA-256",salt:ub(B.bsalt),info:new TextEncoder().encode("x-reply-dashboard v1")},h,{name:"AES-GCM",length:256},false,["decrypt"]);
 var pt=await s.decrypt({name:"AES-GCM",iv:ub(B.iv)},k,ub(B.ct));return new TextDecoder().decode(pt)}
function show(html){document.open();document.write(html);document.close()}
function ask(msg){document.getElementById("w").style.display="none";document.getElementById("f").style.display="";document.getElementById("m").textContent=msg||""}
async function go(e){e.preventDefault();var pw=document.getElementById("p").value;document.getElementById("m").textContent="Unlocking…";
 try{var s=crypto.subtle,pk=await s.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveBits"]);
  var mk=await s.deriveBits({name:"PBKDF2",hash:"SHA-256",salt:ub(B.salt),iterations:B.iter},pk,256);
  var html=await open_(mk);try{localStorage.setItem(K,bu(mk))}catch(x){}show(html)}catch(x){ask("Wrong password")}}
(async function(){var u=new URL(location.href),r=+u.searchParams.get("r")||0;if(Date.now()-r>60000){u.searchParams.set("r",Date.now());location.replace(u.toString());return}
 if(!window.crypto||!crypto.subtle){ask("This browser can't decrypt the page");return}
 var sk=null;try{sk=localStorage.getItem(K)}catch(x){}
 if(sk){try{show(await open_(ub(sk)));return}catch(x){try{localStorage.removeItem(K)}catch(y){}}}ask()})();
</script></body></html>'''

LOCK = ('<button onclick="try{localStorage.removeItem(\'xdash_key_v1\')}catch(e){};location.href=location.pathname" '
        'style="position:fixed;top:10px;right:10px;z-index:99;background:#2f3336;color:#e7e9ea;border:0;border-radius:99px;padding:6px 12px;font-size:14px">🔒 Lock</button>')

def publish(html):
    html = html.replace('<body>', '<body>' + LOCK, 1)
    blob = encrypt(html)
    out = SHELL.replace('__MARK__', MARK).replace('__BLOB__', json.dumps(blob))
    tmp = os.path.join(HERE, 'index.html.tmp')
    open(tmp, 'w').write(out); os.replace(tmp, os.path.join(HERE, 'index.html'))
