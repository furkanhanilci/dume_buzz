"""Mint a relay invite so the official Desktop can join the self-hosted community.

The Desktop's "create a community" path goes to Builderlab, Block's hosted
service. A self-hosted deployment is joined through an invite instead — which
is why the relay's bundled web UI serves the invite landing page and nothing
else.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import Identity, BuzzClient

BASE = "http://127.0.0.1:3100"
o = json.loads(pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets/owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))
code = owner.mint_invite(ttl_secs=86400, max_uses=10)
print("invite code :", code)
print("invite url  :", f"{BASE}/invite/{code}")
