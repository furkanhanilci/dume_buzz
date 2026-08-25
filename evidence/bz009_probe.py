"""BZ-009 — DUM-E's existing Buzz adapter against the official stable relay.

Characterization only. Nothing here moves a work package or records a review.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import (
    Identity, BuzzClient, admit, channel_id_for, BuzzError, TYPE_TAG, REF_TAG)

BASE = "http://127.0.0.1:3100"
SEC = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets/owner.json')
o = json.loads(SEC.read_text())
owner_id = Identity(name=o["name"], private_hex=o["private_hex"], pubkey=o["pubkey"])
owner = BuzzClient(BASE, owner_id)
res = {}

# T01 — relay reachable and describes itself
info = owner.relay_info()
res["T01_relay_info"] = {"software": info.get("software"), "version": info.get("version"),
                         "auth_required": info.get("limitation", {}).get("auth_required"),
                         "restricted_writes": info.get("limitation", {}).get("restricted_writes")}

# T01 — owner is a member by configuration, not by asking
res["T02_owner_is_member"] = owner.is_member()

# T04 — an unadmitted identity must be refused
stranger = Identity.create("unadmitted_stranger")
sc = BuzzClient(BASE, stranger)
try:
    refused = not sc.is_member()
except BuzzError as e:
    refused = True
res["T04_stranger_refused"] = refused

# T01 — the two-party admission path still works
role = Identity.create("dume_architect_probe")
member = admit(owner, role, BASE)
res["T05_admitted_is_member"] = member.is_member()

# T01 — derived channel id is accepted by the official relay's h-grammar
ch = channel_id_for("BZ-009")
owner.create_channel(ch, name="bz-009-probe", about="DUM-E adapter characterization")
ev = member.announce(ch, "STATUS: adapter probe against official stable relay",
                     message_type="STATUS")
res["T06_channel_id"] = ch
res["T06_event_id"] = ev.get("id") or ev.get("event_id")

# T10 — typed tags survive a round trip through the official relay
msgs = owner.read(ch, limit=10)
found = None
for m in msgs:
    tags = m.get("tags", [])
    if any(t[0] == TYPE_TAG for t in tags if len(t) > 1):
        found = {"declared_type": [t[1] for t in tags if t[0] == TYPE_TAG][0],
                 "author": m.get("pubkey", "")[:16]}
        break
res["T10_typed_tag_round_trip"] = found
res["T10_messages_read"] = len(msgs)

print(json.dumps(res, indent=2))
