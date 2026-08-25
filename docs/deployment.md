# What runs, and how to run it

Everything here is on one host. The address is in `deploy/host.env`, which is
not tracked — set it from `deploy/host.env.example` on a fresh checkout. One
value, because the relay keys a community by `host:port` and supports no
aliases: a second address is a second workspace, not a second door.

## The stack

| | where | started by |
|---|---|---|
| Relay | `https://$DUME_BUZZ_HOST` | `deploy/official-buzz/run.sh start` |
| Pair relay | `wss://$DUME_BUZZ_HOST:5443` | same — `compose.pairing.yml` |
| Desktop | its own window | `deploy/desktop/run-desktop.sh start` |
| DUM-E roles | six containers | `deploy/dume-agents/run-agents.sh start` |
| Buzz's own trio | three containers | `deploy/dume-agents/run-buzz-agents.sh start` |
| Command bridge | one process | `deploy/dume-agents/command-bridge.py --watch 10` |

An unrelated stack runs on `:3000` from a different project. It was never
touched, and the Compose project name is overridden precisely so it cannot be:
the upstream `compose.yml` hard-codes `name: buzz-prod`, which is the same
project, and `up` without the override would have adopted its containers and
volumes.

## The relay

The official `deploy/compose` bundle from `block/buzz`, unmodified, plus one
overlay for what it omits.

```bash
cd deploy/official-buzz
./run.sh start | stop | config | logs
./run.sh list-members
./run.sh add-member --pubkey <hex>
```

**Image.** `ghcr.io/block/buzz:sha-aea0ef8`. That is not the release tag by
accident: `desktop-v0.5.18` is a *Desktop* release whose commit touches only
`desktop/*` and never the relay, and CI publishes images per *main* commit, so
no image exists for the release commit at all. `sha-aea0ef8` is the main commit
the release was cut from — the relay of that release, without a source build.

**Overlay.** `compose.pairing.yml` starts `buzz-pair-relay`. The binary ships
inside the relay image and nothing starts it; the single-node bundle declares no
service for it. With nothing listening a phone reports it cannot reach the
pairing relay, which names the relay rather than the absent service.

**TLS.** `tailscale serve` fronts both ports with a real Let's Encrypt
certificate. iOS refuses a cleartext `ws://` relay outright — the error is
`failed to import credentials: relay url must use https` — so the certificate is
not a nicety. Nothing is exposed to the internet; the certificate is valid and
the reach is still tailnet-only.

## The Desktop

The official v0.5.18 AppImage, unmodified and unrebuilt. It cannot run natively
here: its bundled binaries need `GLIBC_2.39` and this host provides 2.35.
Upstream builds the Linux bundle inside `container: ubuntu:24.04`, so the
payload runs against that same base image.

```bash
deploy/desktop/run-desktop.sh start | stop | logs | status
```

It is also installed as a host menu entry that owns `x-scheme-handler/buzz`, so
an invite link opens it.

Two settings matter and both were found by measurement. Overriding the image's
`WEBKIT_DISABLE_COMPOSITING_MODE` renders a **blank white window** — leave the
image's WebKit environment alone. And *Create a community* goes to Builderlab,
Block's hosted service, and hangs forever on a self-hosted deployment; a
self-hosted relay is joined by invite:

```
buzz://join?relay=wss%3A%2F%2F<host>&code=<invite>
```

`relay` must be the **ws/wss** URL. `http://` is rejected — which is what the
relay's own invite page constructs, so it is not a guess.

## The agents

```bash
deploy/dume-agents/run-agents.sh start | stop | status | logs <role>
deploy/dume-agents/run-buzz-agents.sh start | stop | status | logs <name>
```

One container per role, and that is the point: buzz-acp's own README says every
worker under a single `--agents N` instance shares one Nostr identity, so a pool
cannot stand in for roles that must be independent.

Which model each role gets is not decided in these scripts. It is read from
`bindings.json`, which is generated from DUM-E's own `RuntimeRegistry.bind()` —
the same binder a live run uses, with the same independence constraints.

## When a runtime runs out

```bash
deploy/dume-agents/quota-watch.py --watch 60
```

It reports exhaustion to DUM-E's registry and asks DUM-E's binder what the role
gets instead. It never picks the replacement, and when nothing eligible is left
the role waits rather than taking whatever remains.

## Cold starts

llama.cpp caches a prompt by prefix. An agent that has been running answers in
about fifteen seconds; one that has just restarted pays the full prefill and
takes about a minute. That is not a fault, and it is why a restart during
debugging made everything look slower than it is.
