"""Upload the DUM-E logo to the relay's media store and report its URL.

Blossom BUD-02: the request carries a kind-24242 authorisation event naming the
blob's sha256 in an `x` tag, base64-encoded in an `Authorization: Nostr` header.
The blob is then addressed by that hash, so the URL is the content.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1] / "deploy"))
from hostcfg import host as _host, relay_https as _relay_https  # noqa: E402
import base64, hashlib, json, sys, time, pathlib, urllib.request, urllib.error
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration import nostr

BASE = "http://127.0.0.1:3100"
HOST = _host()
blob = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'assets/dume-avatar.png').read_bytes()
digest = hashlib.sha256(blob).hexdigest()

o = json.loads(pathlib.Path('secrets/owner.json').read_text())
ev = nostr.sign_event(
    o["private_hex"], 24242, "Upload DUM-E avatar",
    tags=[["t", "upload"], ["x", digest],
          ["expiration", str(int(time.time()) + 600)]])
auth = base64.b64encode(json.dumps(ev.as_dict() if hasattr(ev, "as_dict") else {
    "id": ev.id, "pubkey": ev.pubkey, "created_at": ev.created_at,
    "kind": ev.kind, "tags": ev.tags, "content": ev.content, "sig": ev.sig,
}).encode()).decode()

req = urllib.request.Request(f"{BASE}/upload", data=blob, method="PUT")
req.add_header("Authorization", f"Nostr {auth}")
req.add_header("Content-Type", "image/png")
req.add_header("Content-Length", str(len(blob)))
req.add_header("Host", HOST)
# BUD-11 hash binding: the header states the blob the auth event authorises,
# so a token minted for one upload cannot be replayed against another body.
req.add_header("X-SHA-256", digest)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read().decode())
    print(json.dumps({"sha256": digest, "url": out.get("url"),
                      "size": out.get("size"), "type": out.get("type")}, indent=2))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])
