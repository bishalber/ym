FROM debian:trixie-slim

ARG CLAUDE_CODE_VERSION=latest
ARG PUID=1000
ARG PGID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    TERM=xterm-256color \
    # Updates happen by rebuilding the image (reproducible), not in place.
    DISABLE_AUTOUPDATER=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git tmux ttyd python3 nodejs npm jq ripgrep less \
        openssh-client procps tzdata vim-tiny \
    && rm -rf /var/lib/apt/lists/*

# Claude Code + ccusage (reads local transcripts to show your Pro 5-hour window usage)
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" ccusage \
    && npm cache clean --force

RUN groupadd -g "${PGID}" claude \
    && useradd -m -u "${PUID}" -g "${PGID}" -s /bin/bash claude

COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 runner.py /usr/local/bin/claude-runner
COPY --chmod=644 tmux.conf /etc/tmux.conf
COPY home-template/ /opt/home-template/

USER claude
WORKDIR /workspace
EXPOSE 7681 8787
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
