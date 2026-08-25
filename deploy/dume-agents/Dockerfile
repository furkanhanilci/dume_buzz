# Runtime for DUM-E's role agents on Buzz.
#
# ubuntu:24.04 because buzz-acp and buzz-agent are built against GLIBC_2.39 and
# this host provides 2.35. The binaries themselves are mounted from the official
# AppImage payload — nothing is rebuilt.
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git curl python3 \
    && rm -rf /var/lib/apt/lists/* \
    && (getent passwd 1000 >/dev/null || useradd -m -u 1000 -s /bin/bash agent)
USER 1000:1000
WORKDIR /home/ubuntu
ENTRYPOINT ["/opt/buzz/usr/bin/buzz-acp"]
