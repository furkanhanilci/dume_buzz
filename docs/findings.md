# What was measured, and what turned out to be false

The integration pack was written from a reading of upstream. Most of it held.
This is the part that did not, plus the faults found in code that was already
running — including the ones in code written during this work.

Each entry says how it was found, because "we checked" is not a finding.

## The plan's own assumptions

### `desktop-v0.5.18` is a Desktop release, not a relay release

`git show --stat 39f8b469` touches `.release/desktop-candidate.json`,
`CHANGELOG.md`, `desktop/package.json` and `desktop/src-tauri/*`. It does not
touch the relay. There is therefore no relay to deploy "at the stable tag" — the
relay of that release is the main commit it was cut from, `aea0ef8d`, which is
where the published image comes from.

### The pin the plan called old was ahead of the tag

The pack frames `0720f53` as the old pin and the stable tag as the upgrade.
Measured: `0720f538` **is** an ancestor of `origin/main` and `39f8b469` is not;
the pin carries 31 commits the tag lacks, and the tag carries one — its own
release chore commit. Moving to the tag is a step sideways onto a release
branch, not forward.

It is still the right move, and the reason is the diff rather than the framing:
`kind.rs`, `NIP-OA.md`, `NIP-PMA.md` and `buzz-agent` are **identical** between
them, and the only relay-handler change is 149 lines of Huddle lifecycle
validation — which the pack DEFERs anyway.

### Nothing starts `buzz-pair-relay`

The binary ships in the relay image beside `buzz-relay` and `buzz-admin`. The
relay does not spawn it and the single-node compose bundle declares no service
for it. It also defaults to `127.0.0.1:5000`, which inside a container is
reachable from nothing, and `BUZZ_PAIRING_RELAY_URL` was unset so the relay
advertised no pairing address at all.

A phone therefore reports *"could not reach the pairing relay"* — correctly, and
about a relay that is running fine.

### The ACP adapters need no API key

Recorded twice in this repo that they do, and wrong both times.

`claude-agent-acp` reports `apiType=native` and reuses the Claude CLI's own
session. `codex-acp` 1.6.2 offers a `chat-gpt` auth method, opens a session on
the ChatGPT subscription, and lists `gpt-5.6-sol` among its models. Buzz's README
says codex-acp demands `OPENAI_API_KEY`; that was true of an older build.

Both need a newer Node than ubuntu:24.04 ships, plus `libatomic1`.

## Faults in DUM-E, found while binding roles

Three, each silent, and together they collapsed the cohort onto one runtime —
which is a cohort with no independence that looks exactly like one that has it.

### A local family had no probe

`mistral-local` serves the second family, the one that makes review independent
of implementation. It answered on `:8001` throughout, but it was absent from
`ENDPOINT_PROBES`, so `runtime --probe` overwrote a working `AVAILABLE` with
*"no probe is defined for this runtime"* and the router stopped offering it.

### Recording a qualification did not make a runtime usable

`qualify --record` wrote `qualified_roles` and left `status` alone. For a
CLI-backed runtime that is the difference between working and not: its probe can
only ever answer `UNKNOWN`, because quota and auth cannot be established without
spending a request. A runtime that had just answered four live trials still
counted as unusable.

### A probe overwrote the measurement with the guess

Worse: running `runtime --probe` after a qualification threw the measurement
away and put `UNKNOWN` back. Recording a pass appeared to work and silently
stopped mattering the next time anything probed.

All three are fixed under test in `tests/test_runtime_availability.py`. The
binder now spreads five roles across four families.

### `reserve` never spent what it reserved

`reserve` answers *"it will now only be spent on architecture-critical work,
spec conflicts and high-risk review"* — and then never spent it. The binder takes
the cheapest candidate and a reserved runtime is the dearest by definition, so
reserving only removed it from the routine pool. A control that never changes
the outcome it names is not a control.

Now, on the work a reserve admits, the role that work turns on takes it first —
and only that role, because upgrading the implementer during a critical package
spends the budget on the highest-volume slot and changes nothing about the
decision that made the work critical. Held by `tests/test_reserve_is_spent.py`.

## Faults in Buzz's own surface

### An agent's voice is the shell

buzz-acp does not publish the reply itself. The agent posts by running the Buzz
CLI, through the `shell` tool that `buzz-dev-mcp` provides. Removing the shell —
which looked like tightening an unrestricted-shell boundary the pack flags —
produced an agent that thought for fifty seconds and said nothing.

`deploy/dume-agents/mcp/desk-mcp.py` keeps the narrower attempt for the day a
send-message tool can replace it.

### Mistral answers without sending

Qwen calls the tool that posts; Mistral emits its answer as text and stops —
`output_tokens=7`, then `19` after the prompt was told to send. It is silent in
a channel and unaffected in the pipeline, where the harness reads its output
rather than waiting for it to speak.

### The Desktop races its own agents

An agent the Desktop considers its own but unconfigured gets a *setup-listener*
that answers mentions with a "needs configuration" nudge — on the same key as
the real runtime, whichever replies first. The DUM-E entries stay listed and
inactive so only one process holds each key.

### There is no headless way to create an agent

The relay exposes no API, and `buzz agents draft-create` needs a `BUZZ_AUTH_TAG`
only the Desktop issues. Its own state files do accept entries, which is how the
team, the personas and the agents got there. The app told us the schema itself,
one error at a time: personas live in `agents/personas.json`, the field is
`system_prompt`, and an agent whose persona is missing is left orphaned and
refused.

### The idle detector refused the cycle it exists to enforce

The live rehearsal died at `implement` on two model families, seven runs in a
row, with *the implementer took 3 turns in a row without changing a file*. The
transcript said the opposite: it had written the test, run it red, and written
the code.

Two defects compounded. `turn_idle` was computed at the bottom of the turn loop
and read at the top of the **next** one, so every turn was judged by what the
previous turn did — a write that followed a test run was idle however much it
changed. And a lone `run_tests` was idle unconditionally, when the red run is
one the protocol requires.

Together they spent the whole three-turn budget on the canonical cycle: write
the test, run it red, write the code, run it green. Four correct turns, refused
for being correct.

The reason it ever worked is the uncomfortable part. The passing run of 08-24
did the same four things in **three** turns, because that model bundled a write
and a run into one. The harness was passing on a property of the model, not on
the discipline, and nothing recorded that it was.

Idle is now decided where the turn's own results are: a run of the tests is
progress exactly once per change, and a second one on an unchanged tree is the
loop worth refusing. Both original stalls still die, under test.

### The refusal destroyed the evidence for the refusal

`tool_log.json` was written after the loop returned, so a raise took it with
it. The only runs with no record of what the implementer did were the runs that
failed — the ones worth reading. Six rehearsals were diagnosed without it, and
the first hypothesis to survive was reached by re-running with the transcript
saved before the raise. It now is, on every raise, and the refusal message names
the calls it refuses.

### The transcript stopped before the deliverables it is evidence for

`tool_log.json` was written where the red-then-green cycle ends. The
deliverable turns run after that, through the same tools — so every call that
produced a mandatory deliverable was missing from the record of what the agent
actually did, which is the phase the `deliverables` gate then returns a verdict
on. Two live runs reported 19 and 17 tool calls against files holding 8 and 11.

Found by chasing that discrepancy rather than assuming the count was cosmetic.
It is written again after the deliverable turns, and a test asserts the file
and the reported number agree.

### A missing pytest was reported as a failing test

`python -m pytest` on an interpreter without pytest exits **1** — the same code
as a test that ran and failed. `run_tests` returned it as the red phase, so a
run launched with the wrong interpreter reported a correct red, could never
reach green, and the implementer was blamed for the host.

This is the invariant DUM-E states about itself: a failure to run is not a
failure to implement. It now checks the runner is there and says so when it is
not.

## Faults in code written here

Kept because the fix is only half the record.

**The quota watcher matched the word "billing".** On its first pass it marked
four working runtimes exhausted. The word appears in the agents' own
instructions and the log echoes them. Its own comment warned against exactly
this. It now matches provider error codes.

**The watcher raised `KeyError` on the front desk.** Which is not a cohort slot
and has no binder rule. It now says so instead of inventing one.

**Agent private keys were committed.** `buzz-builtin.json` carries the secp256k1
private keys for Buzz's three agents, decoded so the runner could start them. It
was written as a working file and never added to `.gitignore`. The credential
scan before the first push caught it; the repository had never been pushed, so
nothing left the machine. Removed from history, and the file stays on disk.

**`node_modules` was committed.** 6116 files, a 270 MB repository, and a
credential scan drowning in minified vendor code. Removed from history: 5.5 MB.

**A blank window was self-inflicted.** Overriding the image's
`WEBKIT_DISABLE_COMPOSITING_MODE` at runtime rendered nothing. The app warns
about the neighbouring variable in its own startup log.
