"""BZ-010 — provision the community host the official Desktop registers against.

The relay is multi-tenant: without a community row for the host the Desktop
connects to, every real request answers 404 and reads as "the relay is down"
(the trap DUM-E's own health.py already documents).
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import Identity, BuzzClient, BuzzError

BASE = "http://127.0.0.1:3100"
o = json.loads(pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets/owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))

for host in ("127.0.0.1", "localhost"):
    try:
        r = owner._post("/operator/communities",
                        {"host": host, "initial_owner_pubkey": o["pubkey"]})
        print(f"{host:12} PROVISIONED  {json.dumps(r)[:200]}")
    except BuzzError as e:
        msg = str(e)
        print(f"{host:12} {'ALREADY EXISTS' if 'already exists' in msg else 'REFUSED'}  {msg[:200]}")
