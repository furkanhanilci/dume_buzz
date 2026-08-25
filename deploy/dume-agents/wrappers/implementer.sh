#!/bin/sh
# implementer → qwen-local (qwen).
# The Desktop spawns every agent in one process tree with one set of provider
# variables. A reviewer bound to a different family has to reach a different
# endpoint, so the binding is applied here, per role, rather than shared.
export BUZZ_AGENT_PROVIDER=openai
export OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_COMPAT_MODEL=/models/Qwen3.8-27B-UD-Q4_K_M.gguf
export OPENAI_COMPAT_API_KEY=local-no-auth
exec /opt/buzz/usr/bin/buzz-agent "$@"
