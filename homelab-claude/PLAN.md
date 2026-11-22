# خطة: كلود كله على الهوم لاب، وتوصله من أي حتة عبر Tailscale

> **المعطيات:** سيرفر Debian + Docker · اشتراك Claude Pro · وصول بـ SSH/tmux + Web terminal + Remote Control · أتمتة بـ n8n (جديد، جوه نفس الـ stack) و Home Assistant ومهام مجدولة · إشعارات على ntfy · باك أب على نفس سيرفر الـ Debian.

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
| سجل الأتمتة واللوجز والمتريكس والداشبورد | `/srv/claude/{logs,prometheus,grafana,n8n,ntfy}` على السيرفر بس |
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
     │  ① ssh <server> → cc           (Tailscale SSH + tmux)
     │  ② https://<server>.<tailnet>.ts.net:8449  (web terminal)
     │  ③ تطبيق Claude ← Code ← "homelab"          (Remote Control، عبر Anthropic)
     ▼
┌──────────── Debian homelab (نفس جهازك في Tailscale، من غير tags) ────────┐
│ tailscale serve (tailnet فقط): :8449→ttyd  :8450→Grafana  :2586→ntfy     │
│                                                                          │
│  docker network: claude-net                                              │
│  ┌─────────────── claude-box ───────────────┐                            │
│  │ tmux "main": [work] شِل  +  [rc] remote-control                        │
│  │ ttyd :7681 ──► نفس جلسة tmux                                           │
│  │ claude-runner :8787 ◄── n8n / HA (jobs بقائمة بيضاء + حدود) ──► ntfy   │
│  └──────┬───────────────────────────────────┘                            │
│         │ OTLP                                  scrape                   │
│         ▼                                         ▲                      │
│  otel-collector ──► Prometheus ◄──────────────────┘ ──► Grafana          │
│                                                                          │
│  /srv/claude/{…,n8n,ntfy} ──► restic ──► /var/backups/claude-restic (محلي)│
└──────────────────────────────────────────────────────────────────────────┘
```

**ليه حاوية مش تثبيت مباشر؟** بتعزل كلود عن السيستم (مايشوفش غير `/workspace`)، وبتخلي الباك أب والنقل لسيرفر تاني مجرد نسخ فولدر، وبتثبّت النسخة (تحدّث بـ rebuild مش بتحديث مفاجئ).

---

## 3) التنفيذ خطوة بخطوة

### المرحلة 1: Tailscale (15 دقيقة)
الخطوة دي معمولة لسيرفر **متسجّل في Tailscale من قبل وعليه apps شغالة** (Nextcloud و n8n وغيرهم). مش بتغيّر اسم الجهاز ولا بتضيف tags ولا بتلمس أي بورت مستخدم. بتعمل حاجتين بس: بتشغّل Tailscale SSH، وبتفتح 3 بورتات جديدة جوه الـ tailnet بس.

1. **الـ ACL:** افتح https://login.tailscale.com/admin/acls واتأكد إن فيه قاعدة `ssh` زي اللي في `host/tailscale-acl.hujson`. لو مش موجودة ضيفها. **ماتلزقش الملف مكان الـ policy كلها**، لأن ده هيقفل أي حاجة مش مكتوبة فيه.
2. **السكريبت** (من `/opt/homelab-claude`):
   ```bash
   sudo bash host/setup-tailscale.sh
   ```
   لو أي بورت من 8449 و 8450 و 2586 مستخدم، السكريبت هيرفض من غير ما يغيّر حاجة. تقدر تختار بورتات تانية بـ `TTYD_PORT=... GRAFANA_PORT=... NTFY_PORT=...`.
   في الآخر هيطبعلك `TS_FQDN` اللي هتحطه في `.env` في المرحلة 2.
3. **الموبايل:** Tailscale متسجّل بنفس الحساب، و **MagicDNS و HTTPS Certificates** مفعّلين (لو بتفتح Nextcloud بـ `https://…ts.net` يبقى مفعّلين أصلًا).
4. **SSH العادي على الـ LAN:** سيبه زي ما هو دلوقتي، لأنه الطريق الاحتياطي لو Tailscale وقع. ممكن تقفله بعدين لما كل حاجة تستقر.

✅ **اختبار:**
- من اللابتوب: `ssh <user>@<server>` (اسم الجهاز في `tailscale status`). أول مرة هيفتحلك صفحة في المتصفح تأكّد فيها هويتك (check mode)، وبعدها يدخل.
- من الموبايل على 4G (مش الواي فاي): نفس الكلام من Termius أو أي تطبيق SSH.
- `sudo tailscale serve status`: البورتات القديمة زي ما هي، وفيه 3 جداد (8449 و 8450 و 2586). اللي بيوجّهوا على 7681 و 3000 و 2586 هيدّوا 502 لحد ما الحاويات تشتغل في المرحلة 2، وده طبيعي.

### المرحلة 2: claude-box (20 دقيقة)
```bash
cd /opt/homelab-claude
cp .env.example .env && chmod 600 .env
#  RUNNER_TOKEN=$(openssl rand -hex 32), GRAFANA_ADMIN_PASSWORD, TS_FQDN, HA_URL/HA_TOKEN
sudo mkdir -p /srv/claude/{home,projects,logs,prometheus,grafana,n8n,ntfy}
sudo chown -R 1000:1000 /srv/claude
docker compose up -d --build            # بيشغّل كمان n8n و ntfy
cc                                       # تدخل tmux جوه الحاوية
claude                                   # أول مرة: /login بحساب Claude Pro
```
بعد الـ login، شبّاك `rc` (Ctrl-b 1) هيشغّل Remote Control لوحده خلال دقيقة.

**n8n:** لو عندك n8n شغال قبل كده، **ماتشغّلش** اللي في الملف ده (هو ورا `--profile n8n`، ومش بيشتغل غير لو طلبته). هنوصّل الـ n8n بتاعك بـ `claude-net` في المرحلة 4.

**ntfy (الإشعارات):**
```bash
docker exec -it claude-ntfy ntfy user add --role=admin me   # يوزر وباسورد لتطبيق الموبايل
docker exec claude-ntfy ntfy token add me                   # التوكن ده حطه في NTFY_RUNNER_TOKEN في .env
docker compose up -d                                        # عشان claude-box ياخد التوكن
```
على الموبايل نزّل تطبيق **ntfy**، وضيف السيرفر `https://<server>.<tailnet>.ts.net:2586` باليوزر اللي عملته، واشترك في topic اسمه `claude-jobs`.
- **آيفون:** التنبيه الفوري لازم يعدّي على Apple، فـ ntfy.sh بيوصّل «poll request» فيه رقم الرسالة بس (والـ topic متشفّر بـ hash). نص الرسالة نفسه التطبيق بيجيبه من سيرفرك عبر Tailscale. لو مش عايز ده خالص فضّي `NTFY_UPSTREAM_BASE_URL`، بس الإشعارات هتتأخر لحد ما تفتح التطبيق.
- **أندرويد:** فضّي `NTFY_UPSTREAM_BASE_URL`، والتطبيق بيفضل متوصل بسيرفرك مباشرة.

✅ **اختبار:** `docker compose ps` يبيّن كله running. وجوه `cc` يظهر شبّاكين: `work` و `rc`. وجرّب الإشعار:
```bash
curl -H "Authorization: Bearer <NTFY_RUNNER_TOKEN>" -d "تجربة من الهوم لاب" http://127.0.0.1:2586/claude-jobs
```
لازم يوصل على الموبايل حتى وهو على 4G (و Tailscale شغال).

### المرحلة 2ب: كلود يشوف ملفاتك (read-only)
الحاوية مابتشوفش غير `/workspace` إلا لو إنت ضفت فولدرات. كل فولدر بيتضاف **read-only** تحت `/data/...` في ملف `docker-compose.override.yml` على السيرفر بس. الملف ده في `.gitignore`، لأن المسارات بتاعتك شخصية والريبو public. والـ compose بيقراه لوحده.
```yaml
services:
  claude-box:
    volumes:
      - /path/to/nextcloud-data/<user>/files:/data/nextcloud:ro
      - /path/to/shared:/data/shared:ro
      - type: tmpfs              # يخبّي فولدر جوه mount (مثلًا configs فيها passwords)
        target: /data/shared/secrets
```
وبعدها `docker compose up -d`. خلّي كلود يعرف بيهم بسطر في `/srv/claude/home/.claude/CLAUDE.md`.
- **Nextcloud:** اعمل mount لفولدر `files` بتاع اليوزر مباشرة، مش لفولدر `data` كله. ولو الـ server-side encryption شغال، الملفات على الديسك متشفّرة وكلود مش هيقدر يقراها.
- **أي فولدر فيه configs أو قواعد بيانات تطبيقات:** خبّيه بـ tmpfs زي المثال، عشان كلود مايقراش passwords ويبعتها في برومبت.
- **read-write:** شيل `:ro` من فولدر معيّن بس، ولما تبقى متأكد. والباك أب مش بيغطي الفولدرات دي.

### المرحلة 3: الوصول من أي حتة (3 طرق، نفس الجلسة)

| الطريقة | إمتى | إزاي |
|---|---|---|
| **SSH + tmux** | شغل جد من لابتوب أو Termius/Termux | `ssh -t <server> cc` |
| **Web terminal** | من أي متصفح على جهاز عليه Tailscale، من غير تطبيقات | `https://<server>.<tailnet>.ts.net:8449` |
| **Remote Control** | من تطبيق Claude على الموبايل بواجهة مريحة | تطبيق Claude ← Code ← جلسة `homelab` |

الطرق الـ 3 بتوصل لنفس الـ tmux، يعني تبدأ مهمة من اللابتوب وتكمّلها من الموبايل. ولو قفلت الاتصال الجلسة بتفضل شغالة (Ctrl-b d للخروج من غير ما توقفها).

✅ **اختبار:** ابدأ `claude` من اللابتوب، افتح الـ web terminal من الموبايل، ولازم تلاقي نفس الشاشة.

### المرحلة 4: الأتمتة (n8n + Home Assistant + مهام مجدولة)

**المبدأ:** مفيش workflow بيكلم كلود مباشرة. كله بيعدّي من **`claude-runner`**، اللي:
- بيشغّل **سكريبتات معروفة بس** من `jobs/` (مفيش برومبت حر جاي من بره)
- بيشغّل **job واحد في المرة** (التاني ياخد 409 بدل ما يتراكم الاستهلاك)
- عليه **سقف يومي** `JOB_MAX_RUNS_PER_DAY` (بعده 429)، فلو workflow عمل loop مش هيخلّص حدّ الأسبوع
- بيسجّل كل تشغيل في `/srv/claude/logs/jobs.jsonl` وبيطلع metrics لـ Grafana

**الإشعارات:** الـ runner نفسه بيبعت على ntfy بعد كل job:
- ✅ لما يخلص: اسم الـ job والمدة والتوكنز وأول 400 حرف من النتيجة.
- ❌ لما يفشل أو يعدّي الـ timeout: نفس الكلام وآخر سطور الخطأ، بأولوية عالية.
- ⚠️ لما السقف اليومي يخلص: إشعار واحد في اليوم.

لو إشعارات النجاح كتير وبتزعجك حط `NTFY_ON_OK=0` في `.env`، وساعتها هيوصلك الفشل بس. ومايفرقش مين نادى الـ job (n8n أو HA أو curl)، الإشعار بيوصل.

**من n8n:** الـ n8n لازم يبقى على شبكة `claude-net` عشان يوصل لـ `claude-box`. لو n8n بتاعك في compose تاني، ضيف في الـ compose بتاعه:
```yaml
services:
  n8n:
    networks: [default, claude-net]
networks:
  claude-net:
    external: true
```
وبعدين `docker compose up -d` في فولدر الـ n8n. (أو مؤقتًا: `docker network connect claude-net <اسم حاوية n8n>`، بس دي بتروح لما الحاوية تتعمل من جديد.)

- Node **Schedule Trigger** (مثلًا 03:30) ← **HTTP Request**:
  `POST http://claude-box:8787/run/repo-review` · Header `Authorization: Bearer <RUNNER_TOKEN>`
- في الـ HTTP Request فعّل **Never Error** (أو Continue On Fail)، عشان 409 (مشغول) و 429 (السقف) مايوقفوش الـ workflow. وحط retry بعد 5 دقايق للـ 409.
- n8n مش محتاج يبعت إشعار، الـ runner بيعمل ده. ولو workflow معيّن عايز إشعار مخصوص، يعمل POST على `http://ntfy/claude-jobs` بنفس التوكن.

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
افتح `https://<server>.<tailnet>.ts.net:8450`، ولوحة **Claude homelab** متجهّزة لوحدها:
- **فوق:** توكنز آخر 24 ساعة، نسبة الـ cache (كل ما تعلى كل ما أرخص)، تكلفة تقديرية (Pro سعره ثابت، فاستخدمها كمقياس «وزن»)، عدد الجلسات، والتوكنز بالساعة حسب النوع والموديل.
- **تحت (تدفّق الأتمتة):** تشغيلات النهارده مقابل السقف، الفاشل والـ timeout، job شغال دلوقتي؟، كام ساعة من آخر تشغيل لكل job (لو job وقف تعرف)، والتوكنز لكل job في 7 أيام.

وكمان من جوه الحاوية:
- `ccusage blocks --live`: استهلاكك في **نافذة الـ 5 ساعات بتاعة Pro** لحظة بلحظة
- `ccusage daily`: يومي
- `tail -f /srv/claude/logs/jobs.jsonl | jq`: سجل الأتمتة
- `/usage` و `/context` جوه كلود: إيه اللي واكل الـ context

### المرحلة 6: الباك أب على سيرفر الـ Debian نفسه (15 دقيقة)
```bash
sudo apt install restic curl
sudo install -m 755 host/backup.sh /usr/local/bin/claude-backup
sudo install -m 600 /dev/null /etc/claude-backup.env
sudoedit /etc/claude-backup.env        # الصق القيم اللي تحت
```
محتوى `/etc/claude-backup.env`:
```ini
RESTIC_REPOSITORY=/var/backups/claude-restic
RESTIC_PASSWORD=<طلّعه بـ: openssl rand -base64 32، وانسخه في password manager>
DATA_ROOT=/srv/claude
STACK_DIR=/opt/homelab-claude
NTFY_URL=http://127.0.0.1:2586/claude-jobs
NTFY_TOKEN=<نفس NTFY_RUNNER_TOKEN>
NTFY_ON_OK=0
```
وبعدين:
```bash
sudo cp host/claude-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now claude-backup.timer
sudo claude-backup                     # أول نسخة يدوي
```
- الباك أب **مشفّر** (فيه tokens الدخول) وبيشتغل كل يوم الساعة 04:30. لو فشل هيوصلك إشعار على ntfy (حط `NTFY_ON_OK=1` لو عايز إشعار بالنجاح كمان).
- **احفظ `RESTIC_PASSWORD` بره السيرفر.** من غيره الباك أب ملوش لازمة.
- **حدود الباك أب على نفس السيرفر:** بيحميك من مسح بالغلط، أو تحديث بايظ، أو كلود يبوّظ ملفات (تقدر ترجع لأي يوم من آخر 7 أيام، أو أي أسبوع من آخر 5، أو أي شهر من آخر 12). بس **مش بيحميك لو الديسك نفسه باظ أو السيرفر اتسرق**. لو عندك ديسك تاني في نفس الجهاز اعمله mount على `/var/backups`، وده ببلاش وبيحل أغلب المشكلة.
- السكريبت بيرفض يشتغل لو الـ repository جوه `/srv/claude`، عشان مايعملش باك أب لنفسه.

✅ **اختبار:**
```bash
sudo bash -c 'set -a; . /etc/claude-backup.env; restic snapshots'
sudo bash -c 'set -a; . /etc/claude-backup.env; restic restore latest --target /tmp/r --include /srv/claude/home/.claude/settings.json'
```

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
| `ssh` بيطلب باسورد بدل صفحة Tailscale | Tailscale SSH مش شغال: `tailscale debug prefs \| grep RunSSH` لازم يبقى `true`، وقاعدة `ssh` لازم تكون في الـ ACL |
| الـ web terminal مابيفتحش | `tailscale serve status`، واتأكد إن MagicDNS و HTTPS مفعّلين في لوحة Tailscale |
| Grafana فاضية | `docker logs claude-otel`. وبعد أول جلسة كلود استنى 30 ثانية (فترة التصدير) |
| job رجع 409 | فيه job تاني شغال. خلّي n8n يعمل retry بعد 5 دقايق |
| مفيش إشعارات بتوصل | `docker logs claude-box 2>&1 \| grep ntfy` (لو 401 يبقى التوكن غلط). وعلى الموبايل اتأكد إن Tailscale شغال وإنك مشترك في `claude-jobs` |
| `tailscale serve --https=2586` رفض | حدّث Tailscale. حد الـ 3 بورتات (443/8443/10000) موثّق لـ Funnel بس، مش لـ Serve. أو اختار بورت تاني بـ `NTFY_PORT=` وغيّر `NTFY_BASE_URL` |
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
- **إشعار لما كلود يستنى موافقتك** في جلسة تفاعلية: Notification hook في `settings.json` يعمل POST على نفس ntfy. (إشعارات الـ jobs والباك أب خلاص اتعملت.)
- **job لمراجعة الاستهلاك أسبوعيًا:** يقرا `jobs.jsonl` ويقترح أي job يتحوّل لـ haiku أو يتقلّل.
