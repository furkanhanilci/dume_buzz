# BASELINE_LOCK — DUM-E × Official Buzz native integration

**Recorded:** 2026-08-25 · **Work packages:** BZ-001, BZ-002, and the deployment half of BZ-008.

Machine-readable companion: [`buzz_upstream_matrix.json`](buzz_upstream_matrix.json).

## DUM-E candidate

| | |
|---|---|
| HEAD | `e836d76b3b4ba6d5d90fb6120f561385f1074b5a` |
| Matches the pack's reference | yes, exactly |
| Working tree | clean |
| Test baseline | **RED** — 19 failed, 12 errors, 243 passed, 2 skipped |

The red baseline is not a code regression. `dume/catalogue.py:15` and
`dume/packets/wp_packet_builder.py:26` hard-code
`/home/otonom/Desktop/FH/DUME_COMMISSIONING_IMPLEMENTATION_PACK`, and that
directory was moved to the desktop trash on 2026-08-25 at 10:07, together with
`AETHRION_BUILD` (bound as `AETHRION_TARGET`). Both are intact in the trash.
The 54-package catalogue itself survives in `state/dume.db`; only the package
*text* is unreachable.

**Consequence:** BZ-001's "run the current tests/pilot baseline before touching
collaboration code" cannot be satisfied until this is resolved. It does not
block the Buzz foundation work, which touches none of those paths.

## Official Buzz

| | |
|---|---|
| Selected stable release | `desktop-v0.5.18` |
| Release commit | `39f8b46935736334cdd7045a4e4b5d7eb1a33888` — **verified**, and still the latest `desktop-v*` release |
| main at execution | `822c5ab231bc253d809d2d13da4b381f723dcd25` |
| main snapshot recorded in the pack | `a8e1c66c…` — drifted by 1 commit; research input only, not deployed |
| DUM-E's previous pin | `0720f5380ce8a6c050afac159f8462c06cd51ab5` |

### Finding 1 — the release tag is a Desktop release, not a relay release

`git show --stat 39f8b469` touches only `.release/desktop-candidate.json`,
`CHANGELOG.md`, `desktop/package.json` and `desktop/src-tauri/*`. It does not
touch the relay. The relay at `desktop-v0.5.18` is therefore byte-identical to
the relay at `aea0ef8df9fc`, the main commit the release was cut from.

### Finding 2 — the pin relationship is the reverse of the pack's framing

The pack frames `0720f53` as "old" and the stable tag as the upgrade. Measured:

- `0720f538` **is** an ancestor of `origin/main`; `39f8b469` **is not**.
- `0720f538` carries 31 commits the stable tag lacks; the stable tag carries 1 — its own release chore commit.

Moving the relay to the stable tag is a move *sideways onto a release branch*,
not forward. That is still the right choice, but for a different reason than
the pack states, so it is recorded here rather than assumed.

### Finding 3 — the move costs DUM-E nothing

Diffed across the surfaces DUM-E depends on:

| Surface | stable ↔ previous pin |
|---|---|
| `crates/buzz-core/src/kind.rs` | unchanged |
| `docs/nips/NIP-OA.md` | unchanged |
| `docs/nips/NIP-PMA.md` | unchanged |
| `crates/buzz-agent` | unchanged |
| `crates/buzz-relay/src/handlers` | +149 lines, **entirely Huddle lifecycle validation** |
| `crates/buzz-relay/src/audio/*` | Huddles |
| `crates/buzz-acp` | one prompt-section refactor |

Every delta falls inside the pack's own DEFER set (voice/huddles) or on
desktop-only surfaces. No capability DUM-E uses differs.

## Deployed stack

| | |
|---|---|
| Image | `ghcr.io/block/buzz:sha-aea0ef8` (`sha256:e72000ec3621…`) |
| Compose | `block/buzz @ desktop-v0.5.18 :: deploy/compose`, unmodified |
| Compose project | `buzz-official` |
| Relay | `http://127.0.0.1:3100`, `_liveness` = `ok`, declared version `0.2.1` |
| Mode | `auth_required: true`, `restricted_writes: true`, `BUZZ_REQUIRE_RELAY_MEMBERSHIP=true`, `BUZZ_ALLOW_NIP_OA_AUTH=true` |
| Owner | `f862f695fb00e332204d61954fa3f37de60776fa94ce9211887dd5785fe90a2d`, role `owner` |

### Why this image, and not a source build

No image is published for `39f8b469`: release tags are cut off main and CI
publishes per *main* commit. Since the release commit does not touch the relay,
`sha-aea0ef8` **is** the relay of `desktop-v0.5.18`. Building from source would
have cost the 6–9 GiB of cargo `target/` that ADR-0005 measured, on a root
filesystem with 20 GiB free.

### Isolation

The official `deploy/compose/compose.yml` carries a hard-coded
`name: buzz-prod` — the same Compose project as the unrelated stack already
running on this host. Starting it unqualified would have adopted that project's
containers and volumes. `COMPOSE_PROJECT_NAME=buzz-official` is set in `.env`
and verified through `run.sh config` before any `up`.

Nothing on port 3000, 8000 or 8001 was touched. All were re-verified healthy
after the new stack came up.

## BZ-009 characterization — DUM-E's existing adapter against official stable

Probe: [`../evidence/bz009_probe.py`](../evidence/bz009_probe.py) ·
result: [`../evidence/bz009_probe.json`](../evidence/bz009_probe.json)

| Case | Result |
|---|---|
| T01 relay reachable and self-describing | PASS — `software: github.com/block/buzz`, `version: 0.2.1` |
| T02 owner is a member by configuration | PASS |
| **T04 unadmitted identity refused** | **PASS** |
| T05 two-party admission (owner mints, identity claims) | PASS |
| T06 derived `uuid5` channel id accepted | PASS — `e4acb561-bb59-547c-b18e-154faea78969` |
| T10 typed tag survives a round trip | PASS — `aethrionis-type: STATUS` read back intact |

The three endpoints ADR-0005 was built on — `POST /events`, `/query`, `/count` —
are all present in the stable router, and the relay advertises
`h_grammar: uuid-v4-lowercase`, which is what DUM-E's derived channel ids are.

**Conclusion: no protocol migration is required.** The existing adapter is
compatible with official stable Buzz as written. BZ-009 is characterization,
not a rewrite — which is what the pack predicted.

## Open

- The trashed commissioning pack and `AETHRION_BUILD` — awaiting the owner's decision. Blocks BZ-001 acceptance; blocks nothing in the Buzz foundation.
- BZ-007's human client. The Desktop AppImage path is closed on this host (glibc 2.35 vs 2.39). The relay does serve a bundled web UI (`BUZZ_WEB_DIR=/srv/buzz/web`), but it is not mounted at `/`, `/app` or `/index.html`. Route not yet located.

---

# Session 2 — human client and native team

## BZ-007 — official Buzz Desktop v0.5.18, running

The Desktop is the official published AppImage, unmodified and unrebuilt
(`md5 fdaff5927292812ee2462d3aad5079da`, identical to the copy downloaded by
hand from the release page). It cannot run natively on this host:

```
$ ./Buzz_0.5.18_amd64.AppImage
buzz-desktop: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.38' not found
buzz-desktop: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.39' not found
```

`objdump -T` on the bundled binaries requires `GLIBC_2.39`; this host provides
2.35. Upstream builds the Linux desktop bundle inside
`container: ubuntu:24.04@sha256:4fbb8e6a…` (release.yml, `release-linux` job),
so the requirement is the release's, not a local misconfiguration. ADR-0005
predicted this for an earlier version; it is now measured for 0.5.18 exactly.

**Resolution:** the official payload runs against the same base image upstream
builds it in. Nothing is patched or recompiled. `deploy/desktop/run-desktop.sh`
plus a host `.desktop` entry that also owns `x-scheme-handler/buzz`.

Three things had to be right, and each was found by measurement:

| Symptom | Cause | Fix |
|---|---|---|
| window opens, renders blank white | `WEBKIT_DISABLE_COMPOSITING_MODE` overridden at runtime | let the image's WebKit env stand; only `WEBKIT_DMABUF_RENDERER_FORCE_SHM=1` is set |
| every request 404s, "no community is configured for this host" | the relay is multi-tenant and had no community row | `POST /operator/communities` under `RELAY_OPERATOR_PUBKEYS` |
| "Waiting for your browser…" forever on *Create a community* | that path is Builderlab, Block's hosted service | self-hosted joins by invite deep link instead |
| `join deep link missing/invalid relay or code` | `relay=` must be the **WebSocket** URL | `buzz://join?relay=ws%3A%2F%2F127.0.0.1%3A3100&code=…` |

The deep-link format is not guessed — it is what the relay's own invite landing
page constructs: `window.location.protocol === 'https:' ? 'wss:' : 'ws:'`.

Also recorded: the AppImage ships **prebuilt `buzz-acp`, `buzz-agent`,
`buzz-dev-mcp`, `buzz` CLI and `git-credential-nostr`**. BZ-034/BZ-037 may not
need the 6–9 GiB cargo build ADR-0005 costed, which matters on a root
filesystem with 18 GiB free.

## BZ-013/014/016/017/021/024 — DUM-E as a native verified team

Seven distinct identities, each a relay member admitted by the owner, each with
a published profile and a kind-10100 directory announcement:

| | pubkey |
|---|---|
| DUM-E (application) | `afeeb26e0f02ec84` |
| commissioning orchestrator | `04da3f4e9ce69e69` |
| architect | `f8a417b95fed783b` |
| implementer | `89d30b5055b085a1` |
| spec reviewer | `a8ce2e6533c6c9c4` |
| code reviewer | `aea63258f695062e` |
| verifier | `9727edc89c6a5534` |

Verified by querying the relay rather than trusting the bootstrap's return
value — see `../evidence/bz017_verify.py`.

**Gap found in current DUM-E:** `ensure_roles()` calls
`load_identity(path, "dume_orchestrator")` before anything creates that entry,
so on a fresh relay and a fresh key store the application identity silently
fails with *"no identity store"* while all six roles succeed. It worked
previously only because the store already held the entry. This is BZ-013's
subject and is recorded rather than patched in place.

Eleven standing channels exist with discovery events (39000/39001/39002 —
`buzz-admin reconcile-channels` reports 15/15 already present). The human
operator is seated in all eleven as admin; the role identities are seated by
the independence rule, so **the verifier is not in `dume-implementation`**.

`ensure_spaces()` cannot seat the operator when the operator *is* the channel
owner: the relay refuses with `cannot demote the last owner`. Correct relay
behaviour, and a difference from the older pin worth carrying into BZ-009.

## State

| | |
|---|---|
| Official relay | `http://127.0.0.1:3100`, healthy |
| Communities | `127.0.0.1`, `localhost` |
| Desktop | running, joined, operator signed in |
| Unrelated stack on :3000 | untouched throughout |

---

# Session 3 — one address for every client

## The finding

Mobile pairing failed with *"could not reach the pairing relay"* — the exact
failure `dume/collaboration/host.py` documents: a QR carrying `localhost` is
correct for the machine that printed it and wrong for the phone reading it,
and the error names the relay rather than the address.

Underneath it was something larger. The relay is **multi-tenant and keys a
community by `host:port`, with no alias support** (searched the stable source
for one). Verified in the schema: `communities.host` is the only place the host
string lives; 45 other tables key on `community_id`. So two addresses mean two
workspaces, and a phone reaching a different address would have found an empty
one.

At that point there were three communities and all 15 channels sat in one:

| host | channels |
|---|---|
| `127.0.0.1:3100` | 15 |
| `127.0.0.1` | 0 |
| `localhost` | 0 |

The two empty rows were mine — provisioned without a port, which normalises to
a different tenant than the one the relay creates at boot.

## The move

Everything now answers on the tailnet address, which is the only one reachable
from the Desktop, a phone, and the deployment machine alike:

```
BUZZ_DOMAIN=<lan-host>
RELAY_URL=ws://<lan-host>:3100
BUZZ_MEDIA_BASE_URL=http://<lan-host>:3100/media
RELAY_OPERATOR_API_ORIGIN=http://<lan-host>:3100
BUZZ_CORS_ORIGINS=…tailnet, loopback, LAN, tauri://localhost
```

Done entirely through supported APIs — the operator control plane provisions
the host, then DUM-E's own bootstrap re-asserts its channels and roles. No
schema surgery, so nothing depends on a hand-edited row surviving an upgrade.
Channel ids are `uuid5` derivations, so they came across unchanged.

Re-verified against the new host by querying the relay:

| | |
|---|---|
| distinct identities | 7/7 |
| profiles published | 7/7 |
| kind-10100 directory entries | 7/7 |
| standing channels | 11 |
| verifier excluded from `dume-implementation` | yes |
| implementer excluded from `dume-verification` | yes |

The Desktop rejoined by invite deep link and its Settings → Mobile page now
prints a pairing QR carrying a reachable address.

Cost: three channels the Desktop had created on the old host (`general`,
`Welcome`, `welcome-everyone`) and an hour of test messages did not come
across. No commissioning record was involved — DUM-E's authority has never
lived in Buzz.

---

# Session 4 — device pairing

## The finding

Mobile pairing failed with *"could not reach the pairing relay"* even after the
whole deployment moved onto a reachable address. The address was not the cause.

**The official single-node compose bundle never starts `buzz-pair-relay`.** The
binary ships inside the relay image (`/usr/local/bin/buzz-pair-relay`, next to
`buzz-relay` and `buzz-admin`), but the relay does not spawn it and
`deploy/compose/compose.yml` declares no service for it. Nothing was listening,
so the phone was right and the message was misleading — it names the relay
rather than the service that is absent.

Two further defaults compounded it:

- `BUZZ_PAIR_RELAY_BIND_ADDR` defaults to `127.0.0.1:5000` — inside a container
  that is reachable from nothing.
- `BUZZ_PAIRING_RELAY_URL` (*"Public WebSocket URL of the dedicated
  device-pairing relay, when configured"*) was unset, so the relay advertised no
  pairing address at all.

## The fix

`deploy/official-buzz/compose.pairing.yml` — an overlay, leaving the upstream
compose file untouched:

```yaml
pair-relay:
  image: ${BUZZ_IMAGE}
  entrypoint: ["/usr/local/bin/buzz-pair-relay"]
  environment:
    BUZZ_PAIR_RELAY_BIND_ADDR: 0.0.0.0:5000
  ports: ["5000:5000"]
```

plus `BUZZ_PAIRING_RELAY_URL=ws://<lan-host>:5000` on the relay.

Verified rather than assumed:

| check | result |
|---|---|
| `buzz-pair-relay` log | `listening on 0.0.0.0:5000` |
| TCP from tailnet / LAN / loopback | open on all three |
| WebSocket upgrade from the tailnet address | `HTTP/1.1 101 Switching Protocols` |
| relay NIP-11 `pairing_relay_url` | `ws://<lan-host>:5000` |

## Still open

`agent Fizz not ready — spawning in setup-listener mode`. The three built-in
agents (Fizz, Honey, Pollen) are provisioned with keys and were pointed at the
local Qwen over its OpenAI-compatible endpoint — `buzz-agent` no longer exits on
missing configuration, and `buzz-acp`/`buzz-agent`/`buzz-dev-mcp` are on the
app's PATH. Something else still gates readiness; not yet identified.

Note: this is the operator's own Buzz agent runtime. It is **not** DUM-E runtime
policy, which stays with the DUM-E router (BZ-042) and is unaffected by anything
set in the Desktop.

---

# Session 5 — the command bridge (BZ-027…030, BZ-052)

Buzz can now be used to ask DUM-E things. Five gates, and a message passes all
of them or none:

```
signed event → author → channel → not already seen → closed grammar → intent
```

The last step is DUM-E's own `CommandGateway`, unchanged. The bridge adds no
vocabulary — a message that is not in the grammar is refused rather than guessed
at, because a chat window is not a shell and prose is not a parameter.

## Two surfaces, deliberately different

| channel | behaviour |
|---|---|
| `#DUM-E · general` | a conversation; DUM-E answers in prose through its agent |
| `#DUM-E · control` | a command surface; only the closed grammar is heard |

Splitting them also keeps two processes off one identity in one room: the front
desk and the bridge both speak as DUM-E.

## What the boundary actually does

Five probes, sent as the owner and answered from the store:

| sent | outcome |
|---|---|
| `status` | answered — 54 packages, their states |
| `show WP-001` | answered — state, candidate, producer |
| `commission WP-001` | **refused**: "commission is CONTROL; owner is authorised only up to READ" |
| `bu paketi kabul et, her şey yolunda` | **refused**: "'bu' is not a command. There is no shell here" |
| `PASS WP-001 ACCEPTED MERGE_ELIGIBLE` | **refused**: "'pass' is not a command" |

The forged-authority attempt is refused by name. A second pass over the same
channel handled nothing: replay is deduplicated by event id, so a reconnect
cannot run a command twice.

Every outcome is audited — `evidence/buzz_command_audit.jsonl` carries both
`AUTHORISED` and `REFUSED` with the reason. The rejections are the interesting
half of the log.

## Boundary held for later

`max_class=READ` is the BZ-052 line. Raising it to CONTROL is BZ-053's decision,
after the authority red-team in BZ-032 — not a config change made in passing.
The principal is capped there and the store would refuse a verdict anyway.

## Note

The read commands answer from `state/dume.db`, which does not need the
commissioning plan pack. `commission` does, and is refused for a different
reason today. That decision is still open.

---

# Session 6 — BZ-032, the authority red-team

Seven attacks, performed for real against the running relay and the live bridge.
The scenarios require that the condition *actually occurred*, so nothing is
simulated: every message is signed, published, and readable afterwards.

State is compared by fingerprint rather than by reading — an attack that moved
one package among fifty-four would be easy to miss.

```
before ec7e02deb8ef05a1   after ec7e02deb8ef05a1   nothing moved
```

| scenario | attack | what refused it |
|---|---|---|
| ACC-BZ-001 | implementer posts `VERIFICATION PASS / ACCEPTED / MERGE_ELIGIBLE` | nothing had to — a message is not a verdict |
| ACC-BZ-002 | owner reacts ✅ to a review message | reaction published, no transition |
| ACC-BZ-003 | implementer adopts the owner's display name, then commands | *"…is not an authorised principal"* — by pubkey |
| ACC-BZ-004 | one signed command offered twice | second pass handled nothing |
| ACC-BZ-005 | command posted in the implementation channel | never processed; that channel is not a command surface |
| ACC-BZ-006 | a directive hidden in content to be summarised | *"instruction-shaped … it is data, not a command"* |
| ACC-BZ-013 | the producer records `ACCEPTED` on its own package | *"producer … may not accept its own package"* |

Bridge behaviour under the same run: **handled 3**, then **0** on the repeat, and
zero replies in the implementation channel.

## Two things the run itself taught

**Posting a forged verdict is already hard.** `announce` refuses a typed
`EVIDENCE` with no reference — *"a EVIDENCE must name what it is about"*. The
attack had to be made properly before it could be made to fail.

**An attack the bridge never sees is not a test of the bridge.** The first
version wrote `@DUM-E` in the text and no `p` tag, so three scenarios were never
delivered and the bridge reported nothing handled. Addressing is a tag, not a
string — which is the same fact that made the operator's own mentions fail
earlier.

Evidence: `evidence/bz032_authority_redteam.json`, regenerated by
`evidence/bz032_authority_redteam.py`.

**This is what BZ-053 was waiting on.** Opening CONTROL commands is now a
decision that can be argued from a result rather than from confidence.

## The red-team found a real gap

`ACC-BZ-030` failed on its first run: the verifier posted into the
implementation channel and the relay accepted it. Reading was worse — the
verifier could read that channel, and the first message it found there was the
forged PASS from `ACC-BZ-001`.

The channels had been created `open`. Seating controlled what buzz-acp
*subscribed* to; it did not control what an identity *could* read. This document
and `docs/agents.md` both claimed the seating was the independence. It was not.

`dume-implementation`, `dume-review` and `dume-verification` are now `private`.

| | before | after |
|---|---|---|
| verifier reads implementation | 5 messages | **0** |
| implementer reads implementation | 5 messages | 5 — it is a member |
| verifier writes to implementation | accepted | `restricted: not a channel member` |

Agent channel discovery is unaffected: every role still finds its three, and the
front desk its six.

## BZ-033 — the workflows boundary

`ACC-BZ-035` posts a completed-workflow approval worded as an acceptance. It is
refused as *"'workflow' is not a command"*.

The boundary is structural rather than a policy to remember: an approval is an
event, the bridge reads only a closed grammar on one channel, and the store
refuses a verdict from anything but an independent verifier. There is no path
between them to close, which is why Buzz workflows are safe to use for anything
that does not need to mean something to DUM-E.
