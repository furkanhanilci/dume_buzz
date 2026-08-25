"""Where this deployment answers. One value, read rather than repeated.

`DUME_BUZZ_HOST` from the environment wins; otherwise `deploy/host.env` is read.
Scripts that hard-code an address disagree with each other the first time it
moves, and this one has moved three times.
"""
import os
import pathlib

_ENV = pathlib.Path(__file__).resolve().parent / "host.env"


def _from_file(key: str) -> str | None:
    if not _ENV.is_file():
        return None
    for line in _ENV.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip()
    return None


def host() -> str:
    value = os.environ.get("DUME_BUZZ_HOST") or _from_file("DUME_BUZZ_HOST")
    if not value:
        raise SystemExit(
            "no relay host: set DUME_BUZZ_HOST or write deploy/host.env "
            "(see deploy/host.env.example)")
    return value


def relay_https() -> str:
    return f"https://{host()}"


def relay_wss() -> str:
    return f"wss://{host()}"


def pair_wss() -> str:
    port = os.environ.get("DUME_BUZZ_PAIR_PORT") or _from_file("DUME_BUZZ_PAIR_PORT") or "5443"
    return f"wss://{host()}:{port}"
