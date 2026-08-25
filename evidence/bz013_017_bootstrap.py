"""BZ-013/014/016/017/021/024 — DUM-E as a native team on official Buzz.

Application identity, persistent role identities, owner-admitted membership,
profiles, agent-directory announcement, standing channels and role seating.
Nothing here can move a work package or record a review.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import (
    Identity, BuzzClient, ensure_spaces, ensure_roles, role_identity,
    SPACE_CHANNELS, ROLE_CHANNELS, BuzzError)

BASE = "http://127.0.0.1:3100"
SEC = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets')
o = json.loads((SEC/'owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))
store = SEC/'roles.json'

res = {"relay": BASE, "owner": o["pubkey"][:12]}

# BZ-021 — the standing workspace
res["spaces"] = ensure_spaces(owner, operator=o["pubkey"])

# BZ-013/014/016/017/024 — application + role identities, profiles, seating
res["roles"] = ensure_roles(owner, store)

print(json.dumps(res, indent=2))
