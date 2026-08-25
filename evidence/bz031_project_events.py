"""BZ-031 — DUM-E projects operational events into official Buzz.

Every message is operational. None of it is a verdict: nothing here can move a
work package or record a review, which is enforced by construction — this
module only publishes and reads messages.
"""
import json, sys, pathlib
sys.path.insert(0, '/home/otonom/Desktop/FH/DUM-E')
from dume.collaboration.buzz import (
    Identity, BuzzClient, SPACE_CHANNELS, load_identity, role_identity)

BASE = "http://127.0.0.1:3100"
STORE = pathlib.Path('/home/otonom/Desktop/FH/Buzz_Dume/secrets/roles.json')
OPERATOR = sys.argv[1]

app = BuzzClient(BASE, load_identity(STORE, "dume_orchestrator"))
ctl = SPACE_CHANNELS["dume-control"]

app.announce(ctl, (
    "DUM-E is live on official Buzz.\n\n"
    "Relay: official block/buzz at desktop-v0.5.18 content (sha-aea0ef8).\n"
    "Roles below are separate verified identities, seated by the independence rule:\n"
    "  @architect, @implementer  -> dume-implementation\n"
    "  @spec-reviewer, @code-reviewer -> dume-review\n"
    "  @verifier -> dume-verification (cannot see implementation)\n\n"
    "Buzz shows, routes and notifies. It does not decide that a package passed. "
    "Every verdict stays in the DUM-E store, recorded by an identity the store "
    "checks for independence."
), mentions=[OPERATOR], message_type="STATUS")

# Each role says hello in the channel it is actually seated in, so the operator
# can see the seating rule rather than be told about it.
hello = {
    "architect": ("dume-implementation", "Architect online. Plans packages; decides nothing about whether a stage passed."),
    "implementer": ("dume-implementation", "Implementer online. Writes code inside an assigned worktree."),
    "spec_reviewer": ("dume-review", "Spec reviewer online. Reviews against the frozen specification."),
    "code_reviewer": ("dume-review", "Code reviewer online. Reviews the diff."),
    "verifier": ("dume-verification", "Verifier online. Fresh session, no producer history."),
}
posted = {}
for role, (chan, text) in hello.items():
    c = BuzzClient(BASE, role_identity(role, STORE))
    ev = c.announce(SPACE_CHANNELS[chan], text, message_type="STATUS")
    posted[role] = f"{chan} <- {(ev.get('id') or '')[:12]}"

print(json.dumps({"control_channel": ctl, "role_posts": posted}, indent=2))
