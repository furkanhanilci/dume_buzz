#!/usr/bin/env python3
"""Move a role off a runtime that has run out, and say so.

Quota is not a property of the work. A package does not become wrong because
someone's billing period turned over, so a runtime that refuses must hand its
role to another one rather than let the role keep failing against it.

What this does *not* do is choose the replacement. It reports the exhaustion to
DUM-E's registry and asks DUM-E's own binder what the role gets instead — the
same binder a live run uses, with the same independence constraints. Buzz
executes; DUM-E decides (BZ-042). If nothing eligible is left, the binder
refuses and the agent stays down: assurance does not shrink because the cheap
option is unavailable.

    ./quota-watch.py              one pass
    ./quota-watch.py --watch 60   every 60 seconds
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/otonom/Desktop/FH/DUM-E")
from dume.cohort.role_registry import ROLES                      # noqa: E402
from dume.runtimes.profiles import (NoEligibleRuntime,           # noqa: E402
                                    RuntimeRegistry)

HERE = pathlib.Path(__file__).resolve().parent
BINDINGS = HERE / "bindings.json"
STATE = HERE / "work" / "quota-watch.json"

# Provider error payloads, not prose. The first version of this matched the bare
# word "billing" and marked four working runtimes exhausted on its first pass —
# the word appears in the agents' own instructions, which the log echoes. What a
# provider actually returns is a machine-readable code, so match those.
EXHAUSTED = re.compile(
    r"insufficient_quota|quota_exceeded|rate_limit_exceeded"
    r"|\b429\b[^\n]{0,40}(too many|rate)"
    r"|usage limit reached|credit balance is too low"
    r"|exceeded your current quota",
    re.IGNORECASE,
)

ORDER = ["architect", "implementer", "spec_reviewer", "code_reviewer", "verifier"]


def container(role: str) -> str:
    return f"dume-agent-{role}"


def recent_log(role: str, since: str = "10m") -> str:
    p = subprocess.run(["docker", "logs", "--since", since, container(role)],
                       capture_output=True, text=True)
    return p.stdout + p.stderr


def load_state() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text())
    return {"reported": {}}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def rebind(registry: RuntimeRegistry) -> dict:
    """Ask DUM-E what every role gets now, under the same independence rules."""
    bound = {}
    for role_id in ORDER:
        role = ROLES[role_id]
        bound[role_id] = registry.bind(
            role_id, already_bound=bound,
            family_independent_of=tuple(
                getattr(role, "family_independent_of", ()) or ()))
    return bound


def one_pass(restart: bool) -> int:
    plan = json.loads(BINDINGS.read_text())
    state = load_state()
    registry = RuntimeRegistry.load()
    moved = 0

    for role, entry in plan["roles"].items():
        runtime = entry["runtime_id"]
        rt = registry.get(runtime)
        if rt is None or not rt.usable():
            continue

        log = recent_log(role)
        if not EXHAUSTED.search(log):
            continue

        hit = EXHAUSTED.search(log).group(0)
        # A provider usually refuses until a period turns over. Without a stated
        # time, a day is the honest guess and it is recorded as a guess.
        retry_after = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(
            timespec="seconds")
        registry.set_status(runtime, "QUOTA_EXHAUSTED",
                            reason=f"agent {role} saw: {hit}",
                            retry_after=retry_after)
        registry.save()
        print(f"  {role}: {runtime} refused ({hit}) — marked QUOTA_EXHAUSTED")

        if role not in ORDER:
            # The front desk is not a cohort slot, so DUM-E's binder has no rule
            # for it. Report the exhaustion and leave the choice to a human:
            # inventing one here would be this file deciding runtime policy.
            print(f"  {role}: no cohort rule for this slot — reassign it by hand")
            state["reported"][role] = {"runtime": runtime, "at": retry_after,
                                       "replacement": None}
            save_state(state)
            continue

        try:
            replacement = rebind(registry)[role]
        except NoEligibleRuntime as exc:
            print(f"  {role}: nothing eligible is left — the role waits.\n    {exc}")
            state["reported"][role] = {"runtime": runtime, "at": retry_after,
                                       "replacement": None}
            save_state(state)
            continue

        print(f"  {role}: DUM-E rebinds to {replacement.runtime_id} "
              f"({replacement.family})")
        entry["runtime_id"] = replacement.runtime_id
        entry["family"] = replacement.family
        entry["model"] = replacement.model
        state["reported"][role] = {"runtime": runtime, "at": retry_after,
                                   "replacement": replacement.runtime_id}
        moved += 1

    if moved:
        BINDINGS.write_text(json.dumps(plan, indent=2))
        save_state(state)
        if restart:
            print("  restarting agents on the new bindings")
            subprocess.run([str(HERE / "run-agents.sh"), "start"], check=False)
    return moved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--watch", type=int, metavar="SECONDS",
                    help="keep checking on this interval")
    ap.add_argument("--no-restart", action="store_true",
                    help="record and rebind, but leave the agents alone")
    args = ap.parse_args()

    while True:
        moved = one_pass(restart=not args.no_restart)
        if not args.watch:
            print("no runtime reported exhaustion" if not moved
                  else f"{moved} role(s) moved")
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
