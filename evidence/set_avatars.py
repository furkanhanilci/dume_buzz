"""Publish each role's profile with the DUM-E mark.

kind 0 carries `picture`; DUM-E's set_profile only writes name and about, so the
event is published directly. The identities are DUM-E's own, so this is the
harness naming itself rather than Buzz configuration.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import Identity, BuzzClient, KIND_METADATA

BASE = "https://otonom-cluster-0.taile59b41.ts.net"
AVATAR = ("https://otonom-cluster-0.taile59b41.ts.net/media/"
          "b36e4c2445b47750956844938816e4e8951693b7fcbd7df50c8438cb5edccc9d.png")

DISPLAY = {"architect": ("DUM-E Architect", "Turns a frozen packet into a plan. Decides no stage."),
           "implementer": ("DUM-E Implementer", "Writes code inside an assigned worktree."),
           "spec_reviewer": ("DUM-E Spec Reviewer", "Reviews against the frozen specification."),
           "code_reviewer": ("DUM-E Code Reviewer", "Reviews the diff, independently."),
           "verifier": ("DUM-E Verifier", "Fresh verification, no producer history.")}

st = json.loads(pathlib.Path('secrets/roles.json').read_text())
out = {}
for role, (name, about) in DISPLAY.items():
    e = st[f'role:{role}']
    c = BuzzClient(BASE, Identity(name=role, private_hex=e['private'], pubkey=e['pubkey']))
    c.publish(KIND_METADATA, json.dumps(
        {"name": name, "display_name": name, "about": about, "picture": AVATAR},
        separators=(",", ":")))
    out[role] = name

app = st['dume_orchestrator']
c = BuzzClient(BASE, Identity(name="dume_orchestrator",
                             private_hex=app['private'], pubkey=app['pubkey']))
c.publish(KIND_METADATA, json.dumps(
    {"name": "DUM-E", "display_name": "DUM-E",
     "about": "The commissioning harness. Records what happened; the gate decides, "
              "and nothing said in a channel moves a package.",
     "picture": AVATAR}, separators=(",", ":")))
out["dume"] = "DUM-E"
print(json.dumps(out, indent=2))
