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
        ca-certificates curl git tmux python3 nodejs npm jq ripgrep less \
        openssh-client procps tzdata vim-tiny \
    && rm -rf /var/lib/apt/lists/*

# ttyd is not packaged in Debian trixie: use the upstream static binary, pinned and checksum-verified.
ARG TTYD_VERSION=1.7.7
RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      amd64) f=ttyd.x86_64;  sum=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55 ;; \
      arm64) f=ttyd.aarch64; sum=b38acadd89d1d396a0f5649aa52c539edbad07f4bc7348b27b4f4b7219dd4165 ;; \
      *) echo "no ttyd build for this architecture" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /usr/local/bin/ttyd "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/${f}"; \
    echo "${sum}  /usr/local/bin/ttyd" | sha256sum -c -; \
    chmod 755 /usr/local/bin/ttyd; \
    ttyd --version

# Claude Code + ccusage (reads local transcripts to show your Pro 5-hour window usage)
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" ccusage \
    && npm cache clean --force

RUN groupadd -g "${PGID}" claude \
    && useradd -m -u "${PUID}" -g "${PGID}" -s /bin/bash claude

COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 runner.py /usr/local/bin/claude-runner
COPY --chmod=755 ncfiles /usr/local/bin/ncfiles
COPY --chmod=644 tmux.conf /etc/tmux.conf
COPY home-template/ /opt/home-template/

USER claude
WORKDIR /workspace
EXPOSE 7681 8787
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
