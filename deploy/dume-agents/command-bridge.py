import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "deploy"))
from hostcfg import host as _host, relay_https as _relay_https  # noqa: E402
#!/usr/bin/env python3
"""Carry a command from a Buzz channel into DUM-E, or refuse and say why.

BZ-027 to BZ-030. Five gates, and a message has to pass all of them:

    signed event → author → channel → not already seen → closed grammar → intent

Only the last step decides what a command means, and it is DUM-E's own gateway
doing it. This file adds no vocabulary: a message that is not in the grammar is
refused rather than guessed at, because a chat window is not a shell and prose
is not a parameter.

Read-only to start (BZ-052). `status`, `show`, `findings` and their kin answer
from the store; `commission`, `pause` and the rest are refused with the reason,
and stay refused until the authority red-team in BZ-032 has run. Nothing here
can move a package or record a verdict — the gateway caps the principal at READ
and the store would refuse it anyway.

    ./command-bridge.py            one pass over recent mentions
    ./command-bridge.py --watch 10
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, "/home/otonom/Desktop/FH/DUM-E")
from dume.collaboration.buzz import (BuzzClient, BuzzError,         # noqa: E402
                                     Identity, SPACE_CHANNELS)
from dume.control.command_gateway import (CommandGateway, CONTROL,  # noqa: E402
                                          CommandRefused, Principal)
from dume.control.intent_handler import IntentHandler               # noqa: E402
from dume.runtimes.profiles import RuntimeRegistry                  # noqa: E402
from dume.state import Store                                        # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SECRETS = ROOT / "secrets"
SEEN = HERE / "work" / "command-bridge-seen.json"
AUDIT = ROOT / "evidence" / "buzz_command_audit.jsonl"

RELAY = _relay_https()

# Where a command may be given. Not every channel: a command surface is a
# decision, and a role's working channel is not one.
COMMAND_CHANNELS = {
    SPACE_CHANNELS["dume-control"]: "DUM-E · control",
}


# #DUM-E · general is deliberately absent. It is a conversation, and DUM-E
# answers there in prose through its agent. Commands belong on a surface where
# prose is refused rather than interpreted, and one identity should not have two
# processes answering it in the same room.


def load_seen() -> set:
    if SEEN.is_file():
        return set(json.loads(SEEN.read_text()))
    return set()


def save_seen(seen: set) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    # Bounded: the dedup window only has to outlive a reconnect, and an
    # unbounded file would grow until it was the slowest part of the loop.
    SEEN.write_text(json.dumps(sorted(seen)[-2000:]))


def strip_mention(text: str, names: list[str]) -> str:
    """Take the address off the front. What remains is the command, or is not."""
    out = (text or "").strip()
    for name in sorted(names, key=len, reverse=True):
        for form in (f"@{name}", name):
            if out.lower().startswith(form.lower()):
                out = out[len(form):].strip(" :,—-")
                return out
    return out


def build_gateway(operator_pubkey: str) -> CommandGateway:
    """One principal, capped at CONTROL.

    `verified=True` says the surface established this identity: the relay
    checked a Nostr signature before the event was stored. That is the
    difference between a sender and a claim, and it is the whole reason a chat
    message may be trusted this far and no further.

    This was READ until BZ-032 and BZ-047 ran. It is CONTROL now because those
    produced a result rather than a good feeling: a forged PASS, a reaction, a
    stolen display name, a replayed command, a command in the wrong channel, an
    injected directive and a producer accepting its own package all landed as
    real events and moved nothing — and the relay was stopped twice without the
    state noticing.

    CONTROL starts, stops and steers work. It is not acceptance. HUMAN_DECISION
    and DANGEROUS_ACTION stay above the cap, and the store still refuses a
    verdict from the identity that produced the candidate — so the class that
    actually matters is closed by two independent mechanisms, not by this
    number.
    """
    return CommandGateway(
        principals={operator_pubkey: Principal(
            actor_id=operator_pubkey, display_name="operator",
            max_class=CONTROL, verified=True)},
        audit_path=AUDIT)


def one_pass(client: BuzzClient, gateway: CommandGateway, handler: IntentHandler,
             dume_pubkey: str, names: list[str], seen: set, limit: int = 20) -> int:
    handled = 0
    for channel, label in COMMAND_CHANNELS.items():
        try:
            events = client.read(channel, limit=limit)
        except BuzzError as exc:
            # The relay is unreachable, which says nothing about any command and
            # nothing about the work. Nothing is marked seen, so whatever was
            # sent during the outage is answered when it comes back — an outage
            # is a delay, not a lost command. Crashing here would have made it a
            # lost command, which is what the first version of this did.
            print(f"  {label}: relay unavailable — {str(exc)[:80]}")
            continue
        for event in events:
            event_id = event.get("id") or ""
            if not event_id or event_id in seen:
                continue

            # Addressed to DUM-E, by a p tag rather than by the text saying so.
            mentions = [t[1] for t in event.get("tags", [])
                        if len(t) > 1 and t[0] == "p"]
            if dume_pubkey not in mentions:
                continue

            seen.add(event_id)
            author = event.get("pubkey", "")
            text = strip_mention(event.get("content", ""), names)
            if not text:
                continue

            try:
                intent = gateway.translate(actor_id=author, channel=label,
                                           text=text, verified=True)
                answer = handler(intent)
                # The receipt names the event the command came from, so a reader
                # can tell which message caused which answer — and so the same
                # message arriving twice is visibly the same command.
                reply = (f"{answer}\n\n`command {intent.action} · "
                         f"from {event_id[:12]} · class {intent.klass}`")
            except CommandRefused as exc:
                reply = (f"Refused: {exc}\n\n`from {event_id[:12]} — "
                         f"nothing was run and nothing changed`")
            except Exception as exc:                      # noqa: BLE001
                # A handler that fell over is a failure of the harness, not a
                # verdict about the work, and it is reported as such.
                reply = (f"The command was understood but the harness failed "
                         f"running it: {type(exc).__name__}: {exc}\n\n"
                         f"`from {event_id[:12]} — no state changed`")

            try:
                client.announce(channel, reply[:3500], mentions=[author],
                                message_type="STATUS")
            except BuzzError as exc:
                # The answer could not be delivered. Un-see the event so it is
                # answered on the next pass rather than silently dropped.
                seen.discard(event_id)
                print(f"  {label}: could not deliver — {str(exc)[:70]}")
                continue
            handled += 1

    save_seen(seen)
    return handled


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--watch", type=int, metavar="SECONDS")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    roles = json.loads((SECRETS / "roles.json").read_text())
    app = roles["dume_orchestrator"]
    identity = Identity(name="DUM-E", private_hex=app["private"],
                        pubkey=app["pubkey"])
    client = BuzzClient(RELAY, identity)

    owner = json.loads((SECRETS / "owner.json").read_text())["pubkey"]
    desktop = "9d07f4c96b5e9e890c950769d73eac26b3186581ab7862295dad92e90734e09c"

    gateway = build_gateway(desktop)
    gateway.principals[owner] = Principal(actor_id=owner, display_name="owner",
                                          max_class=CONTROL, verified=True)
    # The same store the CLI reads. A command from a channel and a command from
    # a terminal reach the same state through the same handler, so they cannot
    # disagree about what a package's state is.
    store = Store(pathlib.Path("/home/otonom/Desktop/FH/DUM-E/state/dume.db"))
    handler = IntentHandler(store, RuntimeRegistry.load(),
                            pathlib.Path("/home/otonom/Desktop/FH/DUM-E/state/PAUSED"))
    names = ["DUM-E", "dume"]
    seen = load_seen()

    print(f"command bridge · {len(COMMAND_CHANNELS)} channel(s) · READ + CONTROL")
    while True:
        n = one_pass(client, gateway, handler, app["pubkey"], names, seen,
                     limit=args.limit)
        if n:
            print(f"  handled {n}")
        if not args.watch:
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
