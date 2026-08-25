# DUM-E × Official Buzz

Making the DUM-E commissioning harness a native application inside official
[Block Buzz](https://github.com/block/buzz) — its roles visible as verified
identities, its state readable from a channel, and its authority unmoved.

> **The invariant.** Buzz can show, route, launch, notify and collaborate. It
> cannot decide that a DUM-E package passed. Every verdict is recorded through
> the DUM-E store by an identity the store checks for independence, and the gate
> reads the store — never a message, a reaction, or a model saying so.

DUM-E itself lives in [`furkanhanilci/DUM-E`](https://github.com/furkanhanilci/DUM-E);
this repository is the integration around it.

## What runs

| | |
|---|---|
| Relay | official `ghcr.io/block/buzz`, self-hosted, TLS over the tailnet |
| Desktop | official v0.5.18, unmodified, against the runtime it was built for |
| Roles | six agents — architect, implementer, three reviewers, and DUM-E itself |
| Runtimes | local Qwen and Mistral, Claude and Codex on their own subscriptions |

```
deploy/official-buzz/   the upstream compose bundle, plus what it omits
deploy/desktop/         the Desktop, and the runtime it needs
deploy/dume-agents/     one process per role, and what decides which model
docs/                   how the harness is operated
baseline/               what was measured, and what turned out to be false
evidence/               probes, and what they answered
```

## The record

`baseline/BASELINE_LOCK.md` is the honest one. It carries what was measured
rather than assumed, including the assumptions that did not survive contact:

- `desktop-v0.5.18` is a **Desktop** release whose commit never touches the
  relay, so the relay of that release is the main commit it was cut from.
- The pinned Buzz revision DUM-E already had was *ahead* of the "newer" stable
  tag, not behind it — and every difference between them fell inside the
  integration pack's own DEFER set.
- Both ACP adapters were recorded as needing an API key. Neither does; they run
  on the CLIs' own sessions.
- `buzz-pair-relay` ships in the relay image and nothing starts it, so a phone
  reports it cannot reach a relay that is running fine.

## Reading it

Start with `docs/dume-operations.html` for how the harness is run, then
`baseline/BASELINE_LOCK.md` for why each piece is the way it is.

## Not in here

`secrets/` and `deploy/official-buzz/.env` hold the relay and agent keys and are
never tracked. `deploy/dume-agents/buzz-builtin.json` is a runtime input for the
same reason. The tailnet hostnames that do appear resolve only inside the
tailnet.
