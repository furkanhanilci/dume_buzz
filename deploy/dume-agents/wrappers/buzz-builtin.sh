#!/bin/sh
# Buzz's own trio, on the Qwen already serving here. The Desktop reverts the
# provider and model fields on every write but keeps agent_command_override,
# so the binding is applied in the process instead of in its config.
export BUZZ_AGENT_PROVIDER=openai
export OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_COMPAT_MODEL=/models/Qwen3.8-27B-UD-Q4_K_M.gguf
export OPENAI_COMPAT_API_KEY=local-no-auth
exec /opt/buzz/usr/bin/buzz-agent "$@"
