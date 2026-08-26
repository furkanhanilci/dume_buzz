#!/usr/bin/env python3
"""BZ-047 / BZ-048 — take the substrate away and see what survives.

The question is not whether things break. It is whether a broken relay looks
like broken work. DUM-E's own invariant separates them: a failure to run is not
a failure to implement, and a package that cannot be narrated has not thereby
failed.

Every outage here is real — the relay is actually stopped, the agent is actually
killed — and the state is compared by fingerprint across the whole catalogue
before and after.

    ./bz047_reliability_redteam.py
    ./bz047_reliability_redteam.py --json
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "deploy"))
sys.path.insert(0, "/home/otonom/Desktop/FH/DUM-E")
from hostcfg import relay_https as _relay_https                     # noqa: E402
from dume.collaboration.buzz import (BuzzClient, BuzzError,         # noqa: E402
                                     Identity, SPACE_CHANNELS)
from dume.state import Store                                        # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECRETS = ROOT / "secrets"
STATE_DB = "/home/otonom/Desktop/FH/DUM-E/state/dume.db"
OUT = ROOT / "evidence" / "bz047_reliability_redteam.json"
COMPOSE = ROOT / "deploy" / "official-buzz"
AGENTS = ROOT / "deploy" / "dume-agents"
CONTROL = SPACE_CHANNELS["dume-control"]


def fingerprint() -> str:
    store = Store(pathlib.Path(STATE_DB))
    rows = sorted((w["wp_id"], w["state"], (w["candidate_revision"] or ""))
                  for w in store.all_wps())
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def owner() -> Identity:
    o = json.loads((SECRETS / "owner.json").read_text())
    return Identity(name=o["name"], private_hex=o["private_hex"], pubkey=o["pubkey"])


def relay(action: str) -> None:
    subprocess.run(["docker", action, "buzz-official-relay-1"],
                   capture_output=True, check=False)


def wait_healthy(timeout: int = 90) -> bool:
    import urllib.request
    for _ in range(timeout // 3):
        try:
            urllib.request.urlopen(f"{_relay_https()}/_liveness", timeout=4)
            return True
        except Exception:                                           # noqa: BLE001
            time.sleep(3)
    return False


# --- the outages --------------------------------------------------------

def acc_016_outage_during_work(results: list) -> None:
    """The relay dies while the harness is mid-package."""
    before = fingerprint()
    relay("stop")
    reached, note = False, ""
    try:
        BuzzClient(_relay_https(), owner()).announce(
            CONTROL, "narrating a stage while the relay is down",
            message_type="STATUS")
        note = "the write succeeded, which it should not have"
    except BuzzError as exc:
        reached, note = True, str(exc)[:90]

    # The store is local and has no opinion about the relay.
    store_readable = True
    try:
        during = fingerprint()
    except Exception as exc:                                        # noqa: BLE001
        store_readable, during = False, f"{type(exc).__name__}"

    relay("start")
    back = wait_healthy()
    results.append({
        "scenario": "ACC-BZ-016", "name": "relay outage during implementation",
        "occurred": True,
        "publish_refused": reached, "reason": note,
        "store_readable_during_outage": store_readable,
        "state_unchanged_during_outage": during == before,
        "relay_recovered": back,
    })


def acc_017_outage_during_command(results: list) -> None:
    """A command is given, and the relay dies before it is answered."""
    c = BuzzClient(_relay_https(), owner())
    dume = json.loads((SECRETS / "roles.json").read_text())["dume_orchestrator"]["pubkey"]
    c.announce(CONTROL, "@DUM-E status", mentions=[dume], message_type="REQUEST")
    relay("stop")
    bridge = subprocess.run(
        [sys.executable, str(AGENTS / "command-bridge.py")],
        capture_output=True, text=True, timeout=180)
    crashed = bridge.returncode != 0
    relay("start")
    back = wait_healthy()
    # The command is still in the channel; the bridge has not marked it seen,
    # so it is answered when the relay returns rather than lost.
    after = subprocess.run(
        [sys.executable, str(AGENTS / "command-bridge.py")],
        capture_output=True, text=True, timeout=180)
    results.append({
        "scenario": "ACC-BZ-017", "name": "relay outage during command",
        "occurred": True,
        "bridge_survived_outage": not crashed,
        "bridge_output_during": (bridge.stdout + bridge.stderr).strip()[:120],
        "answered_after_recovery": "handled" in after.stdout,
        "relay_recovered": back,
    })


def acc_019_agent_crash(results: list) -> None:
    """An agent is killed mid-flight and has to come back on its own key."""
    name = "dume-agent-architect"
    before = subprocess.run(["docker", "inspect", "-f", "{{.State.StartedAt}}", name],
                            capture_output=True, text=True).stdout.strip()
    subprocess.run(["docker", "kill", name], capture_output=True, check=False)
    time.sleep(2)
    running = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name],
                             capture_output=True, text=True).stdout.strip()
    subprocess.run([str(AGENTS / "run-agents.sh"), "start"],
                   capture_output=True, check=False, timeout=300)
    time.sleep(18)
    log = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
    text = log.stdout + log.stderr
    after = subprocess.run(["docker", "inspect", "-f", "{{.State.StartedAt}}", name],
                           capture_output=True, text=True).stdout.strip()
    results.append({
        "scenario": "ACC-BZ-019", "name": "agent crash and respawn",
        "occurred": running == "false",
        "restarted": before != after,
        "same_identity": "pubkey=f8a417b95fed" in text.replace("\x1b", ""),
        "reconnected": "connected to relay" in text,
    })


def acc_028_stale_mention(results: list) -> None:
    """An old command event, offered to the bridge again after a restart."""
    seen = AGENTS / "work" / "command-bridge-seen.json"
    ids = json.loads(seen.read_text()) if seen.is_file() else []
    first = subprocess.run([sys.executable, str(AGENTS / "command-bridge.py")],
                           capture_output=True, text=True, timeout=180)
    second = subprocess.run([sys.executable, str(AGENTS / "command-bridge.py")],
                            capture_output=True, text=True, timeout=180)
    results.append({
        "scenario": "ACC-BZ-028", "name": "stale mention replay after restart",
        "occurred": True,
        "seen_ids_persisted": len(ids),
        "second_pass_handled_nothing": "handled" not in second.stdout,
        "first_pass": first.stdout.strip()[:80],
    })


def acc_032_buzz_unavailable_at_gate(results: list) -> None:
    """The gate is reached while Buzz cannot be told about it."""
    relay("stop")
    store = Store(pathlib.Path(STATE_DB))
    readable = len(store.all_wps())
    # The projector must degrade, not lose. Its watermark may not advance over
    # a transition it could not deliver.
    mark_file = AGENTS / "work" / "event-projector.json"
    before_mark = json.loads(mark_file.read_text())["last_id"] if mark_file.is_file() else 0
    proj = subprocess.run(
        [sys.executable, str(AGENTS / "event-projector.py"), "--since", "115"],
        capture_output=True, text=True, timeout=180)
    after_mark = json.loads(mark_file.read_text())["last_id"] if mark_file.is_file() else 0
    relay("start")
    back = wait_healthy()
    results.append({
        "scenario": "ACC-BZ-032", "name": "Buzz unavailable at the gate",
        "occurred": True,
        "store_readable": readable > 0,
        "projector_degraded": "DEGRADED" in proj.stdout,
        "watermark_did_not_advance_past_undelivered": after_mark <= 115,
        "watermark_before": before_mark, "watermark_after": after_mark,
        "relay_recovered": back,
    })


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    before = fingerprint()
    results: list = []
    acc_016_outage_during_work(results)
    acc_017_outage_during_command(results)
    acc_019_agent_crash(results)
    acc_028_stale_mention(results)
    acc_032_buzz_unavailable_at_gate(results)
    after = fingerprint()

    unmoved = before == after
    report = {"schema": "dume.bz047_reliability_redteam/1",
              "state_before": before[:16], "state_after": after[:16],
              "state_unmoved": unmoved, "scenarios": results,
              "verdict": "PASS" if unmoved else "FAIL"}
    OUT.write_text(json.dumps(report, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if unmoved else 1

    print("BZ-047 / BZ-048 — outage and crash\n")
    for r in results:
        print(f"  {r['scenario']}  {r['name']}")
        for k, v in r.items():
            if k in ("scenario", "name", "occurred"):
                continue
            print(f"      {k:44} {v}")
    print(f"\n  state before {before[:16]}\n  state after  {after[:16]}")
    print(f"\n  {'nothing moved — PASS' if unmoved else 'STATE MOVED — FAIL'}")
    print(f"  evidence: {OUT}")
    return 0 if unmoved else 1


if __name__ == "__main__":
    sys.exit(main())
