#!/usr/bin/env bash
# Buzz's own trio — Fizz, Honey, Pollen — on the Qwen already serving here.
#
# The Desktop cannot run them: it gates spawning on provider and model, and it
# reverts both on every write because it wants a provider configured with
# credentials. It does keep agent_command_override, so the binding is applied
# by a wrapper inside the process instead.
#
# They stay listed in the Desktop but inactive, so only one process holds each
# key — an agent the Desktop considers its own and unconfigured gets a
# setup-listener that answers mentions with a nudge and races the real runtime.
set -euo pipefail
cd "$(dirname "$0")"
# The deployment address, from one place. See deploy/host.env.example.
DUME_BUZZ_HOST_WSS=""; DUME_BUZZ_HOST_HTTPS=""
. "../../deploy/host.env"
DUME_BUZZ_HOST_WSS="wss://$DUME_BUZZ_HOST"
DUME_BUZZ_HOST_HTTPS="https://$DUME_BUZZ_HOST"

RELAY="${DUME_BUZZ_HOST_WSS}"
OWNER="9d07f4c96b5e9e890c950769d73eac26b3186581ab7862295dad92e90734e09c"
APP="$PWD/../desktop/squashfs-root"
IMAGE=dume-agent:0.5.18
CONF="$PWD/buzz-builtin.json"

names() { python3 -c "import json;print(' '.join(a['name'] for a in json.load(open('$CONF'))))"; }
field() { python3 -c "import json,sys;print(next(a[sys.argv[2]] for a in json.load(open('$CONF')) if a['name']==sys.argv[1]))" "$1" "$2"; }

case "${1:-start}" in
  stop)   for n in $(names); do docker rm -f "buzz-agent-$(echo "$n" | tr 'A-Z' 'a-z')" >/dev/null 2>&1 || true; done; echo "stopped"; exit 0 ;;
  status) docker ps -a --filter "name=buzz-agent-" --format '{{.Names}}\t{{.Status}}'; exit 0 ;;
  logs)   exec docker logs -f "buzz-agent-${2:?usage: ./run-buzz-agents.sh logs <name>}" ;;
esac

for name in $(names); do
  low=$(echo "$name" | tr 'A-Z' 'a-z')
  mkdir -p "$PWD/work/$low"
  docker rm -f "buzz-agent-$low" >/dev/null 2>&1 || true
  docker run -d --name "buzz-agent-$low" \
    --network host \
    -e PATH=/opt/buzz/usr/bin:/usr/local/bin:/usr/bin:/bin \
    -v "$APP:/opt/buzz:ro" \
    -v "$PWD/wrappers:/opt/dume:ro" \
    -v "$PWD/work/$low:/home/ubuntu/.buzz" \
    --entrypoint /opt/buzz/usr/bin/buzz-acp \
    "$IMAGE" \
      --relay-url "$RELAY" \
      --private-key "$(field "$name" private_hex)" \
      --agent-owner "$OWNER" \
      --agent-command /opt/dume/buzz-builtin.sh \
      --agent-args "" \
      --mcp-command buzz-dev-mcp \
      --dedup queue \
    >/dev/null
  echo "  $name → qwen-local : started"
done

echo
echo "status: ./run-buzz-agents.sh status   logs: ./run-buzz-agents.sh logs <name>"
