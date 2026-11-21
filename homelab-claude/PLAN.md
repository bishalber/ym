# خطة: كلود كله على الهوم لاب، وتوصله من أي حتة عبر Tailscale

> **المعطيات:** سيرفر Debian + Docker · اشتراك Claude Pro · وصول بـ SSH/tmux + Web terminal + Remote Control · أتمتة بـ n8n و Home Assistant ومهام مجدولة.

## 0) الخلاصة في سطرين

حاوية واحدة اسمها **`claude-box`** شايلة Claude Code و tmux والـ Remote Control وبوابة الأتمتة. كل الداتا بتاعتها في فولدر واحد على السيرفر (**`/srv/claude`**).
مفيش أي بورت مفتوح على النت ولا على الـ LAN. كل حاجة متاحة **لأجهزتك إنت بس** جوه الـ tailnet. المتابعة على Grafana، والأتمتة كلها بتعدّي من باب واحد عليه حدود صرف.

---

## 1) الحقيقة عن «كل الداتا عندي ومش في أي حتة تانية»

الموديل نفسه شغال عند Anthropic، فأي برومبت لازم يتبعت لهم. اللي نقدر نتحكم فيه هو كل حاجة تانية:

| الحاجة | مكانها في الخطة دي |
|---|---|
| الكود والمشاريع والملفات | `/srv/claude/projects` على السيرفر بس |
| تاريخ الجلسات (transcripts) والميموري والإعدادات وتسجيل الدخول | `/srv/claude/home/.claude` على السيرفر بس |
| سجل الأتمتة واللوجز والمتريكس والداشبورد | `/srv/claude/{logs,prometheus,grafana}` على السيرفر بس |
| تنفيذ الأوامر والأدوات | على السيرفر بس |
| البرومبتات وردود الموديل | **بتعدّي على API بتاع Anthropic** (مفيش مهرب) |
| جلسات **Remote Control** | transcript الجلسة **بيتخزن على سيرفرات Anthropic** طول ما هي متوصلة (موثّق رسميًا) |
| شات claude.ai / تطبيق Claude العادي | على Anthropic، **مش** جزء من الخطة دي |

**القرار العملي:** الشغل الحساس يتعمل من **SSH أو الـ Web terminal**، لأن الجلسة فيهم بتفضل على السيرفر والـ API بيشوف البرومبت بس. **Remote Control** للراحة من الموبايل في الشغل العادي.
**اعمل كمان:** claude.ai ← Settings ← Privacy ← اقفل «Help improve Claude».

---

## 2) المعمارية

```
  موبايلك / لابتوبك / أي جهاز عليه Tailscale
     │  ① ssh homelab → cc            (Tailscale SSH + tmux)
     │  ② https://homelab.<tailnet>.ts.net        (web terminal)
     │  ③ تطبيق Claude ← Code ← "homelab"          (Remote Control، عبر Anthropic)
     ▼
┌──────────────── Debian homelab (Tailscale: tag:homelab) ────────────────┐
│ tailscale serve (tailnet فقط):  :443→ttyd   :8443→Grafana   :10000→n8n  │
│                                                                          │
│  docker network: claude-net                                              │
│  ┌─────────────── claude-box ───────────────┐                            │
│  │ tmux "main": [work] شِل  +  [rc] remote-control                        │
│  │ ttyd :7681 ──► نفس جلسة tmux                                           │
│  │ claude-runner :8787 ◄── n8n / HA (jobs بقائمة بيضاء + حدود)            │
│  └──────┬───────────────────────────────────┘                            │
│         │ OTLP                                  scrape                   │
│         ▼                                         ▲                      │
│  otel-collector ──► Prometheus ◄──────────────────┘ ──► Grafana          │
│                                                                          │
│  /srv/claude/{home,projects,logs,prometheus,grafana,n8n} ──► restic backup│
└──────────────────────────────────────────────────────────────────────────┘
```

**ليه حاوية مش تثبيت مباشر؟** بتعزل كلود عن السيستم (مايشوفش غير `/workspace`)، وبتخلي الباك أب والنقل لسيرفر تاني مجرد نسخ فولدر، وبتثبّت النسخة (تحدّث بـ rebuild مش بتحديث مفاجئ).

---

## 3) التنفيذ خطوة بخطوة

### المرحلة 1: Tailscale والأمان (30 دقيقة)
1. في https://login.tailscale.com/admin/acls الزق محتوى `host/tailscale-acl.hujson` وعدّله بإيميلك. **لازم الأول**، عشان `tag:homelab` يبقى موجود.
2. انسخ الفولدر ده على السيرفر في `/opt/homelab-claude` وشغّل:
   ```bash
   sudo TS_HOSTNAME=homelab bash host/setup-tailscale.sh
   ```
3. على الموبايل نزّل Tailscale وسجّل بنفس الحساب. **فعّل MagicDNS و HTTPS Certificates** من لوحة Tailscale.
4. **اقفل SSH العادي على الـ LAN** (اختياري لكن أفضل): `sudo ufw allow in on tailscale0 && sudo ufw deny 22`.

✅ **اختبار:** من الموبايل على 4G (مش الواي فاي) جرّب `ssh homelab`. لازم يطلب تأكيد هويتك في المتصفح (check mode) ويدخل.

### المرحلة 2: claude-box (20 دقيقة)
```bash
cd /opt/homelab-claude
cp .env.example .env && chmod 600 .env
#  RUNNER_TOKEN=$(openssl rand -hex 32), GRAFANA_ADMIN_PASSWORD, TS_FQDN, HA_URL/HA_TOKEN
sudo mkdir -p /srv/claude/{home,projects,logs,prometheus,grafana,n8n}
sudo chown -R 1000:1000 /srv/claude
docker compose up -d --build            # أضف --profile n8n لو معندكش n8n أصلًا
cc                                       # تدخل tmux جوه الحاوية
claude                                   # أول مرة: /login بحساب Claude Pro
```
بعد الـ login، شبّاك `rc` (Ctrl-b 1) هيشغّل Remote Control لوحده خلال دقيقة.

✅ **اختبار:** `docker compose ps` يبيّن كله healthy/running. وجوه `cc` يظهر شبّاكين: `work` و `rc`.

### المرحلة 3: الوصول من أي حتة (3 طرق، نفس الجلسة)

| الطريقة | إمتى | إزاي |
|---|---|---|
| **SSH + tmux** | شغل جد من لابتوب أو Termius/Termux | `ssh -t homelab cc` |
| **Web terminal** | من أي متصفح على جهاز عليه Tailscale، من غير تطبيقات | `https://homelab.<tailnet>.ts.net` |
| **Remote Control** | من تطبيق Claude على الموبايل بواجهة مريحة | تطبيق Claude ← Code ← جلسة `homelab` |

الطرق الـ 3 بتوصل لنفس الـ tmux، يعني تبدأ مهمة من اللابتوب وتكمّلها من الموبايل. ولو قفلت الاتصال الجلسة بتفضل شغالة (Ctrl-b d للخروج من غير ما توقفها).

✅ **اختبار:** ابدأ `claude` من اللابتوب، افتح الـ web terminal من الموبايل، ولازم تلاقي نفس الشاشة.

### المرحلة 4: الأتمتة (n8n + Home Assistant + مهام مجدولة)

**المبدأ:** مفيش workflow بيكلم كلود مباشرة. كله بيعدّي من **`claude-runner`**، اللي:
- بيشغّل **سكريبتات معروفة بس** من `jobs/` (مفيش برومبت حر جاي من بره)
- بيشغّل **job واحد في المرة** (التاني ياخد 409 بدل ما يتراكم الاستهلاك)
- عليه **سقف يومي** `JOB_MAX_RUNS_PER_DAY` (بعده 429)، فلو workflow عمل loop مش هيخلّص حدّ الأسبوع
- بيسجّل كل تشغيل في `/srv/claude/logs/jobs.jsonl` وبيطلع metrics لـ Grafana

**من n8n** (لو n8n في stack تاني، ضيفه على شبكة `claude-net`):
- Node **Schedule Trigger** (مثلًا 03:30) ← **HTTP Request**:
  `POST http://claude-box:8787/run/repo-review` · Header `Authorization: Bearer <RUNNER_TOKEN>`
- الرد JSON فيه `result` و `usage` و `status`، فتوديه Telegram أو إيميل أو Home Assistant notification.
- حط n8n **Error Trigger** workflow يبعتلك لو أي job رجع `status != ok`.

**الـ jobs الجاهزة:**
| Job | بيعمل إيه | الموديل | ليه رخيص |
|---|---|---|---|
| `summarize` | يلخّص أي نص n8n يبعته | haiku | turn واحد، صفر أدوات، صفر MCP |
| `repo-review` | يراجع commits آخر 24 ساعة في كل الريبوهات | sonnet | السكريبت بيجمع الـ diff ويقصّه، وكلود مابيلفّش في الريبو |
| `home-report` | تقرير يومي عن البيت من Home Assistant | haiku | بيحمّل HA MCP بس، ومسموحله أداة القراءة بس (مايقدرش يشغّل/يقفل حاجة) |

**Job جديد** = سكريبت في `jobs/` يعمل `source _lib.sh` ويجهّز الداتا بـ bash ويستدعي `run_claude` مرة واحدة. القاعدة: **bash يعمل الشغل الحتمي، وكلود ياخد القرار بس.**

**Home Assistant:**
- فعّل integration اسمها **Model Context Protocol Server** في HA، وطلّع Long-lived token وحطه في `.env`.
- للاستخدام التفاعلي: `cp -r project-templates/home /srv/claude/projects/home`. أدوات HA هتتحمّل **بس** لما تشتغل في `/workspace/home`، فباقي المشاريع ماتدفعش تمنها.
- ومن HA نفسه تقدر تنادي الـ runner بـ `rest_command` (نفس الـ POST).

### المرحلة 5: المتابعة (Grafana)
افتح `https://homelab.<tailnet>.ts.net:8443`، ولوحة **Claude homelab** متجهّزة لوحدها:
- **فوق:** توكنز آخر 24 ساعة، نسبة الـ cache (كل ما تعلى كل ما أرخص)، تكلفة تقديرية (Pro سعره ثابت، فاستخدمها كمقياس «وزن»)، عدد الجلسات، والتوكنز بالساعة حسب النوع والموديل.
- **تحت (تدفّق الأتمتة):** تشغيلات النهارده مقابل السقف، الفاشل والـ timeout، job شغال دلوقتي؟، كام ساعة من آخر تشغيل لكل job (لو job وقف تعرف)، والتوكنز لكل job في 7 أيام.

وكمان من جوه الحاوية:
- `ccusage blocks --live`: استهلاكك في **نافذة الـ 5 ساعات بتاعة Pro** لحظة بلحظة
- `ccusage daily`: يومي
- `tail -f /srv/claude/logs/jobs.jsonl | jq`: سجل الأتمتة
- `/usage` و `/context` جوه كلود: إيه اللي واكل الـ context

### المرحلة 6: الباك أب (15 دقيقة)
```bash
sudo apt install restic
sudo install -m 755 host/backup.sh /usr/local/bin/claude-backup
sudo install -m 600 /dev/null /etc/claude-backup.env   # واملاه زي ما مكتوب في أول backup.sh
sudo cp host/claude-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now claude-backup.timer
sudo claude-backup                                      # أول نسخة يدوي
```
الباك أب **مشفّر** (فيه tokens الدخول). **احفظ `RESTIC_PASSWORD` بره السيرفر.** ولازم الـ repository يبقى على **ديسك تاني أو NAS**، مش نفس الديسك.

✅ **اختبار:** `restic snapshots` وبعدين جرّب `restic restore latest --target /tmp/r --include /srv/claude/home/.claude/settings.json`.

---

## 4) قواعد توفير التوكنز على Claude Pro

على Pro مفيش فاتورة. المشكلة إنك **تخلّص حدّ الـ 5 ساعات أو الحد الأسبوعي** (الاتنين مشتركين بين claude.ai و Claude Code). عشان كده الهدف إن كل رسالة تبقى خفيفة:

**أ. الـ context هو اللي بيكلّف.** قِسنا: «hi» واحدة في `claude -p` بكل الـ connectors متحمّلة كلّفت **~45 ألف توكن context** قبل ما الموديل يرد بكلمة، لأن تعريفات الأدوات بتتبعت مع كل طلب.
1. **`/mcp` في كل مشروع:** اقفل أي MCP أو connector مش محتاجه (عندك connectors كتير على حساب claude.ai زي Gmail و Drive و Calendar… وكلهم بيتحمّلوا).
2. MCP بتاع مشروع معيّن يتحط في `.mcp.json` بتاع المشروع ده بس (زي `project-templates/home`).
3. الـ jobs بتشتغل بـ `--strict-mcp-config` و `--tools ""` من الأول، ومش بتضيف غير اللي محتاجاه.
4. `CLAUDE.md` قصير (أقل من 200 سطر حسب توصية Anthropic). المعرفة التفصيلية تتنقل لـ skills (بتتحمّل وقت الحاجة بس).

**ب. الموديل الصح:**
5. الافتراضي **Sonnet** (متظبط في `settings.json`). **Opus** بـ `/model` للمشاكل الصعبة بس. **Haiku** للـ jobs والـ subagents اللي بتدوّر.
6. `/effort` أقل للمهام البسيطة.

**ج. عادات الجلسة:**
7. **`/clear`** بين أي مهمتين مالهمش علاقة ببعض. ده أكبر توفير منفرد.
8. **`/compact`** مع تركيز («ركّز على الـ API بس») لما الجلسة تطول.
9. Plan mode للمهام الكبيرة، و Esc أو `/rewind` أول ما تلاقيه ماشي غلط، بدل ما تسيبه يكمّل.
10. ماتلزقش لوجز كاملة: `grep -i error | tail -50` الأول.
11. `permissions.deny` في `settings.json` بيمنع قراية `node_modules` و lockfiles و `.env`.

**د. توزيع الحمل على نوافذ Pro:**
12. الـ jobs التقيلة (`repo-review`) تتجدول **بالليل** (3–5 الفجر). نافذة الـ 5 ساعات دي كده كده مش مستخدمة، فمش هتاكل من شغلك بالنهار.
13. `ccusage blocks --live` قبل ما تبدأ شغل كبير: لو النافذة قربت تخلص، استنى الـ reset.
14. لو اتعودت على أتمتة تقيلة كتير، ساعتها بس فكّر في Max أو API key منفصل **للـ jobs بس**، والـ dashboard هيقولك إمتى.

> ⚠️ **أوعى تحط `ANTHROPIC_API_KEY`** في أي مكان: `claude -p` هيستخدمه بدل اشتراكك ويحاسبك بالتوكن، و Remote Control مابيشتغلش بيه. `_lib.sh` بيرفض يشتغل لو لقاه.
> ⚠️ **ماتحطش `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`**: بيقفل Remote Control. الخطة بتقفل error reporting بس (`DISABLE_ERROR_REPORTING`).

---

## 5) أخطاء شائعة وحلها
| المشكلة | الحل |
|---|---|
| شبّاك `rc` بيقول not logged in | `cc` ← شبّاك 0 ← `claude` ← `/login` |
| `tailscale up --advertise-tags` بيرفض | الـ ACL لازم يتحفظ الأول وفيه `tag:homelab` |
| الـ web terminal مابيفتحش | `tailscale serve status`، واتأكد إن MagicDNS و HTTPS مفعّلين في لوحة Tailscale |
| Grafana فاضية | `docker logs claude-otel`. وبعد أول جلسة كلود استنى 30 ثانية (فترة التصدير) |
| job رجع 409 | فيه job تاني شغال. خلّي n8n يعمل retry بعد 5 دقايق |
| job رجع 429 | السقف اليومي خلص. راجع `jobs.jsonl`، أكيد فيه workflow بيلفّ |
| بعد `docker compose up --build` الجلسات المفتوحة اتقفلت | طبيعي. `claude --continue` يكمّل آخر جلسة (الـ transcripts محفوظة على الـ volume) |
| تحديث كلود | غيّر `CLAUDE_CODE_VERSION` في `.env` ← `docker compose build claude-box && docker compose up -d` |

---

## 6) ناس عملت حاجات شبه كده ونجحت (والاستفادة)
- **Tailscale + SSH + tmux من الموبايل** هو أكتر نمط متكرر وناجح: [Harper Reed](https://harper.blog/2026/01/05/claude-code-is-better-on-your-phone/) · [Termux + Tailscale](https://dev.to/skeptrune/how-i-use-claude-code-on-my-phone-with-termux-and-tailscale-nge) · [Termius + Tailscale](https://dev.to/kaikina/claude-code-from-my-phone-tailscale-termius-and-the-whole-machine-in-my-pocket-28ob) · [iPhone + Tailscale SSH](https://tonyh2021.github.io/posts/2026-04-03-tailscale-ssh) · [Mac mini headless](https://dev.classmethod.jp/en/articles/reona-herdr-remote-mac-mini/). **أخدنا منه:** tmux كجلسة دايمة + Tailscale SSH.
- **Web terminal بـ ttyd + tmux ورا Tailscale:** [buckle42/claude-code-remote](https://github.com/buckle42/claude-code-remote)، وهو نفسه بيحذّر إن أي حد على حسابك في Tailscale ياخد shell. **أخدنا منه:** ttyd، وزوّدنا عليه ACL بيحدد إنت بس، و check mode، وحاوية معزولة.
- **Remote Control الرسمي:** [التوثيق](https://code.claude.com/docs/en/remote-control). متاح على Pro، و server mode بيقبل كذا جلسة. **أخدنا منه:** شبّاك `rc` دايم جوه tmux وبيعيد تشغيل نفسه.
- **متابعة بـ OpenTelemetry + Grafana:** [ColeMurray/claude-code-otel](https://github.com/ColeMurray/claude-code-otel) · [Grafana dashboard 25255](https://grafana.com/grafana/dashboards/25255) · [التوثيق الرسمي](https://code.claude.com/docs/en/monitoring-usage). **أخدنا منه:** collector ← Prometheus ← Grafana، وزوّدنا metrics للـ jobs.
- **توفير التوكنز:** [التوصيات الرسمية](https://code.claude.com/docs/en/costs) · [KDnuggets](https://kdnuggets.com/7-practical-ways-to-reduce-claude-code-token-usage) · [Composio](https://composio.dev/content/ways-to-cut-token-consumption-in-claude-code). أرقام التوفير اللي في المقالات (30–90%) غير موثّقة. اعتمد على الداشبورد بتاعك.

---

## 7) مراحل جاية (بعد ما الأساس يستقر)
- **Loki** للـ OTel logs: تفاصيل كل request (الموديل والمدة والتوكنز لكل طلب).
- **إشعارات** (ntfy على الـ tailnet) لما كلود يستنى موافقتك، عن طريق Notification hook.
- **job لمراجعة الاستهلاك أسبوعيًا:** يقرا `jobs.jsonl` ويقترح أي job يتحوّل لـ haiku أو يتقلّل.
