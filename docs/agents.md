# The agents, and what decides which model each one gets

## The boundary this is all built around

Buzz shows, routes, launches, notifies and collaborates. It cannot decide that a
DUM-E package passed.

That is not a slogan about this document — it is why the architecture looks the
way it does. Every verdict is recorded through the DUM-E store by an identity
the store checks for independence, and the gate reads the store. A message, a
reaction, or a model saying `PASS` creates nothing.

## Who is who

| in Buzz | role | runtime | family |
|---|---|---|---|
| `@DUM-E` | the harness itself | claude | claude |
| `@DUM-E Architect` | turns a frozen packet into a plan | qwen-local | qwen |
| `@DUM-E Implementer` | writes code in an assigned worktree | qwen-local | qwen |
| `@DUM-E Spec Reviewer` | reviews against the frozen specification | claude | claude |
| `@DUM-E Code Reviewer` | reviews the diff | claude | claude |
| `@DUM-E Verifier` | fresh verification, no producer history | codex / gpt-5.6 | gpt |

Plus Buzz's own `@Fizz`, `@Honey` and `@Pollen`, on the local Qwen.

## Two surfaces, deliberately different

| channel | what happens there |
|---|---|
| `#DUM-E · general` | a conversation — DUM-E answers in prose, and asks a role when the answer is work that role did |
| `#DUM-E · control` | a command surface — only the closed grammar is heard, prose is refused |
| `#DUM-E · implementation` | the architect and implementer work here |
| `#DUM-E · review` | both reviewers |
| `#DUM-E · verification` | the verifier — and **not** the implementer |

The seating *is* the independence — but only because the channels are
**private**. That was not true when they were first created, and the red-team
found it: with the channels `open`, any relay member could read any of them, so
the verifier could read the implementation channel and the first thing it found
there was a forged PASS. Seating controlled what buzz-acp *subscribed* to, not
what an identity *could* read, and a verifier that wanted to look could.

`dume-implementation`, `dume-review` and `dume-verification` are now private.
The relay refuses a non-member with `restricted: not a channel member`, so it is
a fact it enforces rather than a convention agents are trusted to keep.

## One process, one identity

Each role runs in its own container with its own key. buzz-acp's README is
explicit that every worker under a single `--agents N` instance shares one Nostr
identity — so a pool cannot stand in for roles that must be epistemically
independent, however many workers it has.

Each is also restricted to its own channels with `--channels`, and gated with
`--respond-to allowlist` so only the human owner and DUM-E itself can drive it.

### Fresh sessions where freshness is the point

The two reviewers and the verifier run with `--max-turns-per-session 1`. A
reviewer that carries yesterday's conversation into today's review is reading
its own earlier reasoning as if it were evidence, and a verifier that does it is
not performing a fresh verification at all. One turn per session means there is
no prior turn to carry — which is the proof, where `!rotate` is only a
mechanism.

The architect keeps continuity: planning benefits from remembering the shape of
the thing being planned, and it decides no stage.

## Who picks the model

Not the scripts. `bindings.json` is generated from DUM-E's own
`RuntimeRegistry.bind()` — the same binder a live run uses, with the same
constraints — and the runner reads it.

The rules come from DUM-E's role registry, as data:

```
spec_reviewer   family_independent_of: implementer
code_reviewer   family_independent_of: implementer
verifier        family_independent_of: implementer
```

A reviewer from the implementer's family fails the same way the implementer
failed, so its PASS is not independent evidence. That is the whole rule, and it
is why the binder spreads the pipeline across four families:

```
architect qwen · implementer qwen · spec_reviewer mistral
code_reviewer claude · verifier gpt
```

### The chat projection is weaker, and that is fine

Only two families can post in a channel: Qwen calls the tool that sends, Claude
does through its adapter. Mistral answers without sending. So the chat agents
lean on fewer families than the pipeline does.

This costs nothing that matters. Verdicts are recorded by the pipeline, where
the binding is unchanged and the four families hold. Nothing said in a channel
moves a package, so chat-side family diversity is a nicety rather than
assurance.

## Cheap by default, expensive on purpose

Ordering is `(cost_tier, local first, id)`, so routine work lands on the local
pair and spends no quota. The implementer never leaves local Qwen — it is the
highest-volume slot, and paying per token there buys nothing.

Two runtimes are reserved:

| work class | role that gets the reserved runtime |
|---|---|
| `ARCHITECTURE_CRITICAL` | architect → `codex-sol` |
| `SPEC_CONFLICT` | spec reviewer → `codex-sol` |
| `HIGH_RISK_REVIEW` | code reviewer and verifier → `codex-sol`, `claude-fable-5` |

Only the role the class is about is upgraded. Spending premium quota on the
implementer during an architecture-critical package burns the budget on the
busiest slot and changes nothing about the decision that made the work critical.

## Qualification is measured, not assumed

A runtime may hold a role only after answering live trials — tool calling,
structured output, refusing an unsound claim, admitting uncertainty. A CLI on
`PATH` says a file exists; a trial says the runtime answered.

```bash
python3 -m dume.cli qualify <runtime> --record
```

Seven runtimes hold recorded qualifications, each with an evidence file and a
hash.

## Superpowers, per role

Each role's prompt carries its own engineering skills, injected whole from
`bundle_for(role)` — the same injection a DUM-E run makes, not a retyped summary.
The revision is pinned and checked against the lockfile.

Injection is an **input**. Whether the discipline was obeyed is answered by
red-then-green exit codes and independent review, never by a skill file being
present.

The front desk carries none of it: it writes no code, and the bundle was two
thousand tokens of prefill on every turn for nothing.
