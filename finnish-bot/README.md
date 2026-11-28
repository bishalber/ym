# BishuFinnish_bot — Finnish teacher on Telegram (n8n + Claude + Nextcloud)

Built from the Agent Foundry Playbook: one Telegram bot, an AI Agent with tools, scheduled workers,
everything generated from code (`build_all.py`), state kept in your Nextcloud.

## What it does
| When | What |
|---|---|
| 07:30 daily | Generates a lesson (5 new words + mnemonics, 4 sentences, grammar tip, real-life dialogue, one YKI task, ONE question), proof-reads it with a second Claude pass, sends it to Telegram, saves `lessons/DATE.md`, adds the words to the spaced-repetition list. Weekday rotation: grammar / real life / YKI speaking / YKI reading+writing / sentence building / listening-style dictation / light review. |
| 19:00 daily | Evening review: picks due words (Leitner boxes 1-5 = 1, 2, 4, 8, 16 days), asks the first one. |
| Any time | Chat with the teacher (Egyptian Arabic, one question at a time, praise only when correct). Commands: `/today /review /drill /yki /words /progress`. |
| Photo of homework | Reads it, answers `written -> correct -> ✔/❌ reason`, saves repeated mistakes to `notes.json`. |
| Photo with caption `sanasto kpl 3` | Reads the Suomen Mestari vocabulary page, adds the words (Arabic + English + mnemonic) to `vocab.json`. |

Teaching skills built into the prompt (`src/teacher_prompt.md`): retrieval first, spaced repetition,
keyword mnemonics, chunks, word families, interleaving, shadowing, handwriting; real-life role-play
drills; YKI practice (speaking, writing, reading; listening only as dictation).

## Files
```
build_all.py          generates build/*.json (import-ready) + nextcloud/vocab.json, notes.json
src/teacher_prompt.md the tutor's system prompt        src/facts.md  learner facts
src/js/*.js           code-node bodies (one file each)
build/*.json          8 workflows: chat, daily_lesson, evening_review, 5 tools
deploy.sh             import + publish into n8n (Docker)
nextcloud_upload.sh   one-time transfer of lessons / skill / prompt / metadata to Nextcloud
nextcloud/            seed files uploaded by the script
```
Nextcloud layout (`FinnishBot/`): `vocab.json`, `notes.json`, `lessons/`, `homework/`, `notes/`,
`skill/` (the /teacher skill + portable prompt + bot prompt), `meta/` (learner facts, progress notes, session log).

## Setup (you do steps 1-4; they need your accounts)
1. **Telegram bot**: @BotFather -> `/newbot` -> name it `BishuFinnish_bot` (or reuse yours). Put the token
   in n8n > Credentials > Telegram API. Never paste it in chat.
2. **Your chat id**: send any message to @userinfobot. Only this id can use the bot.
3. **Nextcloud app password**: Settings > Security > Devices & sessions. In n8n create a *Basic Auth*
   credential (user = your Nextcloud user, password = the app password). Also create the *Anthropic* credential.
4. **Public HTTPS URL for n8n** (`WEBHOOK_URL`), needed by the Telegram trigger.
5. Transfer to Nextcloud (creates folders, uploads skill, prompt, lessons, metadata, seed vocab):
   `NC_URL=https://cloud.example.com NC_USER=... NC_APP_PASSWORD=... ./nextcloud_upload.sh`
6. Build with your ids and deploy (`make.sh` reads private settings from `env.local.sh`, which is git-ignored;
   create it with `echo 'export FI_OWNER_CHAT_ID=<your id>' > env.local.sh`, then `./make.sh deploy`). Manual equivalent:
   ```
   export FI_OWNER_CHAT_ID=123456789
   export FI_NC_BASE=https://cloud.example.com/remote.php/dav/files/<user>/FinnishBot
   export FI_CRED_TG=<n8n credential id> FI_CRED_ANTHROPIC=<id> FI_CRED_NC=<id>
   python3 build_all.py && ./deploy.sh
   ```
   (Without the credential ids it still imports; just pick the credentials in each node once in the UI.)
7. Shadow week: read every message, send `/start`, send a `sanasto kpl 3` photo, send a homework photo.

## Tested here (no n8n, no Telegram, no Nextcloud available in this environment)
- All 8 workflow JSONs build; every connection points at an existing node; 24 Code nodes pass `node --check`.
- 16 functional checks with mocked n8n globals and real luxon: vocab add/dedupe/due/grade (Leitner),
  remember, save_file path guard, prompt assembly, homework mistake extraction, vocab-page merge,
  4000-char message splitting, lesson request/proof-read/finalize (+ fallback when the check fails),
  evening review (+ empty case).

## NOT verified — check on first import
- **n8n node parameters** (Telegram, AI Agent, toolWorkflow, IF, HTTP raw body) follow the playbook and
  n8n 2.x conventions but were never loaded into a live n8n. If a node shows a red warning, open it once and
  re-save; the logic in the Code nodes does not depend on it.
- `anthropic-version` header defaults to the playbook's value (`FI_ANTHROPIC_VERSION` to change) and model ids
  to `claude-opus-5-5`; change `FI_MODEL_CHAT` if your account differs.
- Textbook content: the books are not in this repo, so the bot learns your chapters from your photos.
  Finnish produced by the model is proof-read by a second pass but can still contain mistakes; check against the book.
- YKI structure/levels are described from general knowledge; confirm at yki.fi.
- Facebook reel link: could not be opened (login wall + proxy); nothing from it was used.

## Cost & safety
- Cost: rough estimate from the playbook's own figures, not measured: a daily Opus lesson + proof-read plus $0.05-0.20 per chat message. Set a monthly limit in the Anthropic console.
- Every Nextcloud URL in the workflows is under `FinnishBot/`; `save_file` only accepts `lessons/ notes/ homework/`.
  (A Nextcloud app password is not folder-scoped, so keep it out of chat and revoke it if leaked.)
- No email/send tools exist, and only your chat id is answered.
