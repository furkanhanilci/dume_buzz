#!/usr/bin/env python3
"""BZ-031 — project DUM-E's state changes into Buzz, and say where they came from.

Every message carries the reference that makes it checkable: the package, the
transition id, and the actor the store recorded. The text is a projection. The
truth is the store, and a reader who wants to be sure runs
`python3 -m dume.cli history <wp>` rather than believing the channel.

This is the direction the pack cares about least and depends on most. Buzz
learning what DUM-E did is safe; the reverse is the whole authority question.
So this is one-way by construction — it opens the database read-only, and there
is no code path here that could write a transition even if something asked it to.

**When Buzz is down the projection degrades and DUM-E does not.** The watermark
only advances over transitions that were actually delivered, so an outage
becomes a backlog rather than a hole, and the packages keep moving regardless.

    ./event-projector.py                catch up and exit
    ./event-projector.py --watch 15
    ./event-projector.py --since 0      re-project everything
"""
import argparse
import json
import pathlib
import sqlite3
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "deploy"))
sys.path.insert(0, "/home/otonom/Desktop/FH/DUM-E")
from hostcfg import relay_https as _relay_https                     # noqa: E402
from dume.collaboration.buzz import (BuzzClient, BuzzError,         # noqa: E402
                                     Identity, SPACE_CHANNELS)

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SECRETS = ROOT / "secrets"
STATE_DB = "/home/otonom/Desktop/FH/DUM-E/state/dume.db"
MARK = HERE / "work" / "event-projector.json"

# Which room a transition belongs in. A state change is news for the people who
# would act on it, and the control channel is where the run as a whole is
# followed.
ROOM = {
    "IMPLEMENTING": "dume-implementation",
    "IN_REVIEW": "dume-review",
    "SPEC_REVIEW": "dume-review",
    "CODE_REVIEW": "dume-review",
    "VERIFYING": "dume-verification",
    "ACCEPTANCE_READY": "dume-verification",
    "BLOCKED": "decisions-escalations",
    "FAILED": "operations-incidents",
}
DEFAULT_ROOM = "dume-control"

# A transition is not a verdict, and the wording should not let anyone read one
# into it. "reached" describes the store; it does not bless what is in it.
SHAPE = {
    "MERGE_ELIGIBLE": "reached the machine gate",
    "ACCEPTED": "was accepted",
    "BLOCKED": "is blocked",
    "FAILED": "failed",
}


def load_mark() -> int:
    if MARK.is_file():
        return json.loads(MARK.read_text()).get("last_id", 0)
    return 0


def save_mark(last_id: int, pending: int = 0) -> None:
    MARK.parent.mkdir(parents=True, exist_ok=True)
    MARK.write_text(json.dumps({"last_id": last_id, "pending": pending}, indent=2))


def unseen(since: int) -> list[sqlite3.Row]:
    # Read-only, and not merely by convention: the URI flag makes a write fail
    # rather than rely on this file never growing one.
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return list(conn.execute(
            "select id, wp_id, from_state, to_state, actor, reason, at "
            "from transition where id > ? order by id", (since,)))
    finally:
        conn.close()


def render(row: sqlite3.Row) -> str:
    verb = SHAPE.get(row["to_state"], f"is now {row['to_state']}")
    line = f"**{row['wp_id']}** {verb}."
    if row["from_state"] and row["from_state"] != row["to_state"]:
        line += f"  ({row['from_state']} → {row['to_state']})"
    if row["reason"]:
        line += f"\n\n{row['reason']}"
    # The reference is the point of the message. Without it this is a rumour.
    line += (f"\n\n`transition {row['id']} · {row['wp_id']} · "
             f"actor {row['actor']} · {row['at']}`"
             f"\n`check: python3 -m dume.cli history {row['wp_id']}`")
    return line


def project(client: BuzzClient, since: int, dry_run: bool = False) -> tuple[int, int]:
    rows = unseen(since)
    if not rows:
        return since, 0

    delivered = since
    for row in rows:
        channel = SPACE_CHANNELS[ROOM.get(row["to_state"], DEFAULT_ROOM)]
        if dry_run:
            print(f"  {row['id']:>4}  {row['wp_id']:<8} → {row['to_state']}")
            delivered = row["id"]
            continue
        try:
            client.announce(channel, render(row), message_type="STATUS",
                            refs=[row["wp_id"]])
        except BuzzError as exc:
            # The relay is unavailable, which says nothing about the work. Stop
            # at the last transition that actually landed: the rest stay unsent
            # and are sent when it comes back, so an outage is a backlog rather
            # than a hole.
            remaining = len(rows) - (rows.index(row))
            print(f"  projection DEGRADED at transition {row['id']}: "
                  f"{str(exc)[:90]}\n  {remaining} transition(s) pending; "
                  f"DUM-E state is unaffected")
            save_mark(delivered, pending=remaining)
            return delivered, remaining
        delivered = row["id"]

    if not dry_run:
        save_mark(delivered, pending=0)
    return delivered, 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--watch", type=int, metavar="SECONDS")
    ap.add_argument("--since", type=int, help="re-project from this transition id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    app = json.loads((SECRETS / "roles.json").read_text())["dume_orchestrator"]
    client = BuzzClient(_relay_https(), Identity(
        name="DUM-E", private_hex=app["private"], pubkey=app["pubkey"]))

    mark = args.since if args.since is not None else load_mark()
    print(f"event projector · from transition {mark}"
          f"{' · dry run' if args.dry_run else ''}")

    while True:
        mark, pending = project(client, mark, dry_run=args.dry_run)
        if pending:
            print(f"  {pending} pending — will retry")
        if not args.watch:
            print(f"  at transition {mark}")
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
