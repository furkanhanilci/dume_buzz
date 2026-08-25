"""Seat the human operator in DUM-E's standing channels.

The channels and their discovery events already exist; what the Desktop was
missing is membership. Added by the owner — a participant cannot put itself in
a room, which is the property the closed relay exists to have.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import Identity, BuzzClient, SPACE_CHANNELS, BuzzError

BASE = "http://127.0.0.1:3100"
SEC = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets')
o = json.loads((SEC/'owner.json').read_text())
owner = BuzzClient(BASE, Identity(name=o["name"], private_hex=o["private_hex"],
                                  pubkey=o["pubkey"]))
OPERATOR = sys.argv[1]

out = {}
for name, ch in SPACE_CHANNELS.items():
    try:
        owner.add_member(ch, OPERATOR, role="admin")
        out[name] = "seated (admin)"
    except BuzzError as e:
        try:
            owner.add_member(ch, OPERATOR, role="member")
            out[name] = "seated (member)"
        except BuzzError as e2:
            out[name] = f"refused: {str(e2)[:70]}"
print(json.dumps(out, indent=2))
