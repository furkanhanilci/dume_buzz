"""Move the DUM-E workspace onto the tailnet address.

The relay keys a community by host:port and supports no aliases, so one
address has to serve the Desktop, mobile and DUM-E alike or they land in
different workspaces. Everything here goes through supported APIs: the
operator control plane provisions the host, then DUM-E's own bootstrap
re-asserts its channels and roles. Channel ids are derived, so they survive.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import (
    Identity, BuzzClient, ensure_spaces, ensure_roles, SPACE_CHANNELS, BuzzError)

BASE = "http://100.104.142.19:3100"
HOST = "100.104.142.19:3100"
SEC = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets')
DESKTOP = sys.argv[1] if len(sys.argv) > 1 else None

o = json.loads((SEC/'owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))
res = {"relay": BASE}

# 1. The community host. Idempotent: an existing host reports as such.
try:
    res["community"] = owner._post("/operator/communities",
        {"host": HOST, "initial_owner_pubkey": o["pubkey"]})
except BuzzError as e:
    res["community"] = ("already exists" if "already exists" in str(e)
                        else f"refused: {str(e)[:120]}")

# 2. Standing channels and the verified team, re-asserted on the new host.
res["spaces"] = {k: ("ok" if "asserted" in v else v)
                 for k, v in ensure_spaces(owner, operator=o["pubkey"]).items()}
res["roles"] = ensure_roles(owner, SEC/'roles.json')

# 3. Seat the human operator everywhere.
if DESKTOP:
    seated = {}
    for name, ch in SPACE_CHANNELS.items():
        try:
            owner.add_member(ch, DESKTOP, role="admin"); seated[name] = "admin"
        except BuzzError as e:
            seated[name] = f"refused: {str(e)[:50]}"
    res["operator_seated"] = seated

# 4. A fresh invite so the Desktop can join the new host.
res["invite"] = owner.mint_invite(ttl_secs=86400, max_uses=10)
print(json.dumps(res, indent=2))
