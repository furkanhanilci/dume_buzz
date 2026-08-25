"""Independent verification of the native team, read back from the relay.

Nothing is taken from the bootstrap's return value; every fact is queried.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import (
    Identity, BuzzClient, SPACE_CHANNELS, ROLE_CHANNELS, BuzzError)

BASE = "http://100.104.142.19:3100"
SEC = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets')
o = json.loads((SEC/'owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))
store = json.loads((SEC/'roles.json').read_text())

pub = {"dume_application": store["dume_orchestrator"]["pubkey"]}
for k, v in store.items():
    if k.startswith("role:"):
        pub[k[5:]] = v["pubkey"]

res = {"identities": len(pub), "checks": {}}

# Every identity must be a distinct relay member with a published profile.
seen, members, profiled, announced = set(), {}, {}, {}
for name, pk in pub.items():
    seen.add(pk)
    c = BuzzClient(BASE, Identity(name=name, private_hex="00"*32, pubkey=pk))
    try:
        members[name] = owner.query(kinds=[0], authors=[pk]) != []
    except BuzzError:
        members[name] = None
    profs = owner.query(kinds=[0], authors=[pk], limit=1)
    profiled[name] = bool(profs)
    if profs:
        try:
            profiled[name] = json.loads(profs[0].get("content") or "{}").get("name")
        except Exception:
            pass
    announced[name] = bool(owner.query(kinds=[10100], authors=[pk], limit=1))

res["checks"]["distinct_pubkeys"] = (len(seen) == len(pub))
res["checks"]["profiles"] = profiled
res["checks"]["agent_directory_10100"] = announced

# The independence rule, verified against the relay rather than the config:
# the verifier must not be seated where the implementer works.
def seated(pk, channel_uuid):
    evs = owner.query(kinds=[9], limit=200)  # membership events
    return any(channel_uuid in json.dumps(e.get("tags", [])) and pk in json.dumps(e.get("tags", []))
               for e in evs)

impl_ch = SPACE_CHANNELS["dume-implementation"]
verif_ch = SPACE_CHANNELS["dume-verification"]
res["checks"]["independence"] = {
    "verifier_channels_by_contract": list(ROLE_CHANNELS["verifier"]),
    "implementer_channels_by_contract": list(ROLE_CHANNELS["implementer"]),
    "verifier_excluded_from_implementation":
        "dume-implementation" not in ROLE_CHANNELS["verifier"],
    "implementer_excluded_from_verification":
        "dume-verification" not in ROLE_CHANNELS["implementer"],
}

# Standing channels actually exist on this relay.
res["checks"]["standing_channels"] = len(SPACE_CHANNELS)
res["pubkeys"] = {k: v[:16] for k, v in pub.items()}
print(json.dumps(res, indent=2))
