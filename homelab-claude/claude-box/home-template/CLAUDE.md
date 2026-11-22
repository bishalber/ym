# Homelab defaults (keep this file short: it is sent with every request)

- Talk to me in Egyptian Arabic; write code, commits and file content in English.
- This box is `claude-box` on my Debian homelab. Projects are under /workspace.
- Search before reading: use Grep/Glob to find the exact lines, then read only that range.
- Never read lockfiles, build output, minified files or whole log files; grep logs for errors.
- Summarize long command output in a few lines instead of pasting it back.
- For broad searches, use a subagent with model haiku and return only the conclusion.
- Ask before large refactors or anything touching more than ~5 files.
- Project-specific rules go in that project's own CLAUDE.md, not here.
- If `ncfiles` exists, it reads my Nextcloud files read-only (`ncfiles ls`, `find`, `get`, `cat`). Find by name first; never download whole folders.
