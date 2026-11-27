#!/usr/bin/env python3
"""Build the BishuFinnish_bot n8n workflows (playbook: 'build as code').

Usage:  FI_OWNER_CHAT_ID=123 FI_NC_BASE=https://cloud.x/remote.php/dav/files/me/FinnishBot \
        FI_CRED_TG=<id> FI_CRED_ANTHROPIC=<id> FI_CRED_NC=<id> python3 build_all.py

Writes build/*.json (import-ready) and nextcloud/vocab.json + notes.json seeds.
No secrets are ever written here: only credential ids/names that n8n resolves itself.
"""
import json, os, re, sys, uuid
from pathlib import Path

ROOT = Path(__file__).parent
SRC, JS, BUILD, NCDIR = ROOT / "src", ROOT / "src" / "js", ROOT / "build", ROOT / "nextcloud"
BUILD.mkdir(exist_ok=True)

# ------------------------------------------------------------------ config
OWNER = os.environ.get("FI_OWNER_CHAT_ID", "REPLACE_OWNER_CHAT_ID")
NC_BASE = os.environ.get("FI_NC_BASE", "https://YOUR-NEXTCLOUD/remote.php/dav/files/YOUR-USER/FinnishBot").rstrip("/")
CRED_TG = {"telegramApi": {"id": os.environ.get("FI_CRED_TG", "REPLACE_TG"), "name": "BishuFinnish_bot"}}
CRED_AN = {"anthropicApi": {"id": os.environ.get("FI_CRED_ANTHROPIC", "REPLACE_ANTHROPIC"), "name": "Anthropic account"}}
CRED_NC = {"httpBasicAuth": {"id": os.environ.get("FI_CRED_NC", "REPLACE_NEXTCLOUD"), "name": "Nextcloud FinnishBot"}}
ANTHROPIC_VERSION = os.environ.get("FI_ANTHROPIC_VERSION", "2026-10-21")  # value from the Agent Foundry Playbook
M_CHAT = os.environ.get("FI_MODEL_CHAT", "claude-opus-5-5")      # tutor + homework + lessons
M_FAST = os.environ.get("FI_MODEL_FAST", "claude-haiku-5-5")     # not used by default; for bulk jobs
TZ = "Europe/Helsinki"

PROMPT = (SRC / "teacher_prompt.md").read_text(encoding="utf-8").replace(
    "__FACTS__", (SRC / "facts.md").read_text(encoding="utf-8").strip())
COMMON = (JS / "common.js").read_text(encoding="utf-8")


def js(name, common=True, **subs):
    s = (JS / name).read_text(encoding="utf-8")
    for k, v in subs.items():
        s = s.replace(k, v)
    return (COMMON + s) if common else s


def lit(x):  # JS literal
    return json.dumps(x, ensure_ascii=False)


# ------------------------------------------------------------------ schemas
def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


S = {"type": "string"}
LESSON_SCHEMA = obj(
    title=S, intro_ar=S,
    new_words={"type": "array", "items": obj(fi=S, ar=S, en=S, example_fi=S, example_ar=S, mnemonic_ar=S)},
    sentences={"type": "array", "items": obj(fi=S, ar=S)},
    grammar_ar=S,
    real_life=obj(scenario_ar=S, lines={"type": "array", "items": obj(who=S, fi=S, ar=S)}),
    yki=obj(skill=S, task_fi=S, task_ar=S),
    question=obj(fi=S, ar=S), homework_ar=S)
INGEST_SCHEMA = obj(chapter=S, words={"type": "array", "items": obj(fi=S, ar=S, en=S, example=S, mnemonic=S)})


# ------------------------------------------------------------------ workflow helper
class WF:
    def __init__(self, wid, name):
        assert len(wid) == 16, wid
        self.id, self.name, self.nodes, self.conn, self.x = wid, name, [], {}, 0

    def add(self, name, typ, tv, params, cred=None, pos=None, **extra):
        assert all(n["name"] != name for n in self.nodes), "duplicate node " + name
        self.x += 240
        n = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id + name)), "name": name, "type": typ,
             "typeVersion": tv, "position": pos or [self.x, 0], "parameters": params}
        if cred:
            n["credentials"] = cred
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, a, b, out=0, typ="main"):
        arr = self.conn.setdefault(a, {}).setdefault(typ, [])
        while len(arr) <= out:
            arr.append([])
        arr[out].append({"node": b, "type": typ, "index": 0})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def check(self):
        names = {n["name"] for n in self.nodes}
        for a, d in self.conn.items():
            assert a in names, f"{self.name}: connection from unknown node {a}"
            for outs in d.values():
                for lst in outs:
                    for t in lst:
                        assert t["node"] in names, f"{self.name}: {a} -> unknown node {t['node']}"

    def dump(self, fname):
        self.check()
        wf = [{"id": self.id, "name": self.name, "active": False,
               "settings": {"executionOrder": "v1", "timezone": TZ}, "nodes": self.nodes, "connections": self.conn}]
        (BUILD / fname).write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding="utf-8")
        print("wrote build/" + fname, f"({len(self.nodes)} nodes)")


# ------------------------------------------------------------------ node factories
def code(w, name, src, each=False):
    return w.add(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForEachItem" if each else "runOnceForAllItems", "jsCode": src})


def nc_get(w, name, path):
    return w.add(name, "n8n-nodes-base.httpRequest", 4.2, {
        "method": "GET", "url": f"{NC_BASE}/{path}" if not path.startswith("=") else path,
        "authentication": "genericCredentialType", "genericAuthType": "httpBasicAuth",
        "options": {"timeout": 30000, "response": {"response": {"fullResponse": True, "neverError": True, "responseFormat": "text"}}}},
        cred=CRED_NC, onError="continueRegularOutput")


def nc_put(w, name, url, body, ctype="application/json; charset=utf-8"):
    return w.add(name, "n8n-nodes-base.httpRequest", 4.2, {
        "method": "PUT", "url": url,
        "authentication": "genericCredentialType", "genericAuthType": "httpBasicAuth",
        "sendBody": True, "contentType": "raw", "rawContentType": ctype, "body": body,
        "options": {"timeout": 30000, "response": {"response": {"fullResponse": True, "neverError": True}}}},
        cred=CRED_NC, onError="continueRegularOutput")


def claude(w, name):
    return w.add(name, "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.anthropic.com/v1/messages",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
        "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": ANTHROPIC_VERSION}]},
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"timeout": 180000}}, cred=CRED_AN)


def tg_send(w, name):
    return w.add(name, "n8n-nodes-base.telegram", 1.2, {
        "resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}",
        "text": "={{ $json.text }}", "additionalFields": {"appendAttribution": False}}, cred=CRED_TG)


def tg_typing(w, name="Typing"):
    return w.add(name, "n8n-nodes-base.telegram", 1.2, {
        "resource": "chat", "operation": "sendChatAction", "chatId": "={{ $('Telegram Trigger').first().json.message.chat.id }}",
        "action": "typing"}, cred=CRED_TG)


def if_bool(w, name, expr):
    return w.add(name, "n8n-nodes-base.if", 2.2, {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, w.id + name)), "leftValue": expr, "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}})


# ------------------------------------------------------------------ tool sub-workflows
TOOLS = {}  # key -> (id, tool name, description, [(arg, description)])


def build_tool(key, wid, title, inputs, logic_js, store=None, write=True, desc="", args=()):
    """store = nextcloud file to load/save (vocab.json | notes.json) ; None = direct write (save_file)."""
    w = WF(wid, f"Finnish - tool {title}")
    w.add("When called", "n8n-nodes-base.executeWorkflowTrigger", 1.1, {
        "inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": i} for i in inputs]}})
    if store:
        nc_get(w, "Load", store)
        code(w, "Logic", logic_js)
        w.chain("When called", "Load", "Logic")
        if write:
            nc_put(w, "Put", f"{NC_BASE}/{store}", "={{ $json.payload }}")
            code(w, "Out", js("tool_out.js", common=False))
            w.chain("Logic", "Put", "Out")
        else:
            code(w, "Out", js("tool_out_ro.js", common=False))
            w.chain("Logic", "Out")
    else:
        code(w, "Logic", logic_js)
        nc_put(w, "Put", "={{ $json.url }}", "={{ $json.payload }}", "text/markdown; charset=utf-8")
        code(w, "Out", js("tool_out.js", common=False))
        w.chain("When called", "Logic", "Put", "Out")
    w.dump(f"tool_{key}.json")
    TOOLS[key] = (wid, key, desc, list(args))


build_tool("vocab_add", "FItoolVocabAdd01", "vocab_add", ["words"], js("tool_vocab_add.js"), "vocab.json",
           desc="Save new Finnish words to Bishu's spaced-repetition list. words = JSON array of {fi, ar, en, example, mnemonic, chapter}.",
           args=[("words", "JSON array text of word objects with keys fi, ar, en, example, mnemonic, chapter")])
build_tool("vocab_due", "FItoolVocabDue01", "vocab_due", ["limit"], js("tool_vocab_due.js"), "vocab.json", write=False,
           desc="List words due for review today (Leitner boxes) plus stats. limit = max words, default 10.",
           args=[("limit", "Max number of due words to return, e.g. 10")])
build_tool("vocab_grade", "FItoolVocabGrd01", "vocab_grade", ["word", "correct"], js("tool_vocab_grade.js"), "vocab.json",
           desc="Record whether Bishu answered a saved word correctly; moves it between Leitner boxes and sets the next review date.",
           args=[("word", "The Finnish word exactly as saved, e.g. talo"), ("correct", "yes if he answered correctly, no otherwise")])
build_tool("remember", "FItoolRemember01", "remember", ["note"], js("tool_remember.js"), "notes.json",
           desc="Save one short sentence about Bishu's progress, repeated mistakes or preferences. It is shown to you in every future chat.",
           args=[("note", "One short sentence about progress or a repeated mistake")])
build_tool("save_file", "FItoolSaveFile01", "save_file", ["path", "content"], js("tool_save_file.js", common=False, __BASE__=lit(NC_BASE)),
           desc="Save a markdown file to Bishu's Nextcloud. path must start with lessons/, notes/ or homework/.",
           args=[("path", "e.g. lessons/2026-12-01-kauppa.md"), ("content", "The markdown text to save")])

# ------------------------------------------------------------------ chat workflow
def build_chat():
    w = WF("FIchat0000000001", "Finnish - 10 Teacher chat (Telegram)")
    w.add("Telegram Trigger", "n8n-nodes-base.telegramTrigger", 1.2, {"updates": ["message"], "additionalFields": {}},
          cred=CRED_TG, webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "FIchat-webhook")))
    w.add("Owner only", "n8n-nodes-base.if", 2.2, {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "owner")), "leftValue": "={{ String($json.message.chat.id) }}",
                        "rightValue": OWNER, "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}, "options": {}})
    tg_typing(w)
    for n, p in [("Get notes", "notes.json"), ("Get vocab", "vocab.json")]:
        nc_get(w, n, p)
    nc_get(w, "Get lesson", "=" + "{{ '" + NC_BASE + "/lessons/' + $now.setZone('" + TZ + "').toFormat('yyyy-LL-dd') + '.md' }}")
    nc_get(w, "Get review", "=" + "{{ '" + NC_BASE + "/lessons/' + $now.setZone('" + TZ + "').toFormat('yyyy-LL-dd') + '-review.md' }}")
    code(w, "Build prompt", js("chat_build.js", __PROMPT__=lit(PROMPT)))
    w.chain("Telegram Trigger", "Owner only")
    w.link("Owner only", "Typing", 0)
    w.chain("Typing", "Get notes", "Get vocab", "Get lesson", "Get review", "Build prompt")

    tm = "$('Telegram Trigger').first().json.message"
    if_bool(w, "Is photo?", "={{ !!" + tm + ".photo }}")
    if_bool(w, "Is vocab page?", "={{ /^\\s*(sanasto|vocab|vocabulary|كلمات|مفردات)/i.test(" + tm + ".caption || '') }}")
    if_bool(w, "Has text?", "={{ !!" + tm + ".text }}")
    w.link("Build prompt", "Is photo?")

    # --- vocab-page ingest branch (photo with caption 'sanasto ...')
    w.link("Is photo?", "Is vocab page?", 0)
    getfile = lambda n: w.add(n, "n8n-nodes-base.telegram", 1.2, {
        "resource": "file", "operation": "get", "download": True, "fileId": "={{ " + tm + ".photo.slice(-1)[0].file_id }}"}, cred=CRED_TG)
    getfile("Get page photo")
    code(w, "Ingest request", js("ingest_req.js", __MODEL__=lit(M_CHAT), __SCHEMA__=json.dumps(INGEST_SCHEMA)))
    claude(w, "Claude ingest")
    code(w, "Ingest merge", js("ingest_merge.js"))
    nc_put(w, "Put vocab", f"{NC_BASE}/vocab.json", "={{ $json.payload }}")
    w.link("Is vocab page?", "Get page photo", 0)
    w.chain("Get page photo", "Ingest request", "Claude ingest", "Ingest merge", "Put vocab")
    code(w, "Split (ingest)", js("split.js", common=False, __TEXT__="$('Ingest merge').first().json.reply", __CHAT__=tm + ".chat.id"))
    tg_send(w, "Send (ingest)")
    w.chain("Put vocab", "Split (ingest)", "Send (ingest)")

    # --- homework branch
    getfile("Get homework photo")
    code(w, "Homework request", js("hw_req.js", __MODEL__=lit(M_CHAT)))
    claude(w, "Claude homework")
    code(w, "HW extract", js("hw_extract.js"))
    nc_put(w, "Put notes", f"{NC_BASE}/notes.json", "={{ $json.payload }}")
    w.link("Is vocab page?", "Get homework photo", 1)
    w.chain("Get homework photo", "Homework request", "Claude homework", "HW extract", "Put notes")
    code(w, "Split (homework)", js("split.js", common=False, __TEXT__="$('HW extract').first().json.reply", __CHAT__=tm + ".chat.id"))
    tg_send(w, "Send (homework)")
    w.chain("Put notes", "Split (homework)", "Send (homework)")

    # --- text branch -> agent
    w.link("Is photo?", "Has text?", 1)
    w.add("Teacher", "@n8n/n8n-nodes-langchain.agent", 2.2, {
        "promptType": "define", "text": "={{ " + tm + ".text }}",
        "options": {"systemMessage": "={{ $('Build prompt').first().json.system }}", "maxIterations": 8}})
    w.add("Claude", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.6, {
        "model": {"__rl": True, "mode": "id", "value": M_CHAT}, "options": {"maxTokensToSample": 2500}}, cred=CRED_AN)
    w.add("Memory", "@n8n/n8n-nodes-langchain.memoryBufferWindow", 1.3, {
        "sessionIdType": "customKey", "sessionKey": "={{ 'fi-' + " + tm + ".chat.id }}", "contextWindowLength": 20})
    w.link("Has text?", "Teacher", 0)
    w.link("Claude", "Teacher", 0, "ai_languageModel")
    w.link("Memory", "Teacher", 0, "ai_memory")
    for key, (wid, name, desc, args) in TOOLS.items():
        val = {a: "={{ $fromAI('" + a + "', '" + re.sub(r"[^A-Za-z0-9 ,.:/_-]", "", d) + "', 'string') }}" for a, d in args}
        w.add("Tool " + name, "@n8n/n8n-nodes-langchain.toolWorkflow", 2.2, {
            "name": name, "description": desc,
            "workflowId": {"__rl": True, "mode": "id", "value": wid},
            "workflowInputs": {"mappingMode": "defineBelow", "value": val, "matchingColumns": [],
                               "schema": [{"id": a, "displayName": a, "required": False, "defaultMatch": False,
                                           "display": True, "canBeUsedToMatch": True, "type": "string"} for a, _ in args]}})
        w.link("Tool " + name, "Teacher", 0, "ai_tool")
    code(w, "Split (agent)", js("split.js", common=False, __TEXT__="$json.output", __CHAT__=tm + ".chat.id"))
    tg_send(w, "Send (agent)")
    w.chain("Teacher", "Split (agent)", "Send (agent)")

    # --- unsupported message types (voice, sticker...)
    w.add("Unsupported", "n8n-nodes-base.telegram", 1.2, {
        "resource": "message", "operation": "sendMessage", "chatId": "={{ " + tm + ".chat.id }}",
        "text": "أنا بقرا نص وصور بس دلوقتي. اكتب أو استخدم الإملاء الصوتي 🎤 (voice dictation) وابعت النص.",
        "additionalFields": {"appendAttribution": False}}, cred=CRED_TG)
    w.link("Has text?", "Unsupported", 1)
    # layout: spread vertically so the canvas is readable
    for i, n in enumerate(w.nodes):
        n["position"] = [200 * (i % 12), 220 * (i // 12)]
    w.dump("chat.json")


# ------------------------------------------------------------------ daily lesson + evening review
def build_daily():
    w = WF("FIdaily000000001", "Finnish - 20 Daily lesson (07:30)")
    w.add("Every day 07:30", "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [{"field": "cronExpression", "expression": "30 7 * * *"}]}})
    nc_get(w, "Get vocab", "vocab.json")
    nc_get(w, "Get notes", "notes.json")
    code(w, "Lesson request", js("lesson_req.js", __PROMPT__=lit(PROMPT), __SCHEMA__=json.dumps(LESSON_SCHEMA), __MODEL__=lit(M_CHAT)))
    claude(w, "Claude lesson")
    code(w, "Check request", js("lesson_check_req.js", __SCHEMA__=json.dumps(LESSON_SCHEMA), __MODEL__=lit(M_CHAT)))
    claude(w, "Claude check")
    w.nodes[-1]["onError"] = "continueRegularOutput"
    code(w, "Finalize", js("lesson_final.js", __BASE__=lit(NC_BASE)))
    nc_put(w, "Put vocab", f"{NC_BASE}/vocab.json", "={{ $json.vocabPayload }}")
    nc_put(w, "Put lesson", "={{ $('Finalize').first().json.lessonUrl }}", "={{ $('Finalize').first().json.lessonMd }}", "text/markdown; charset=utf-8")
    code(w, "Split", js("split.js", common=False, __TEXT__="$('Finalize').first().json.msg", __CHAT__=lit(OWNER)))
    tg_send(w, "Send lesson")
    w.chain("Every day 07:30", "Get vocab", "Get notes", "Lesson request", "Claude lesson", "Check request",
            "Claude check", "Finalize", "Put vocab", "Put lesson", "Split", "Send lesson")
    w.dump("daily_lesson.json")

    r = WF("FIreview00000001", "Finnish - 30 Evening review (19:00)")
    r.add("Every day 19:00", "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [{"field": "cronExpression", "expression": "0 19 * * *"}]}})
    nc_get(r, "Get vocab", "vocab.json")
    code(r, "Build review", js("review_build.js", __BASE__=lit(NC_BASE)))
    nc_put(r, "Put review", "={{ $('Build review').first().json.reviewUrl }}", "={{ $('Build review').first().json.reviewMd }}", "text/markdown; charset=utf-8")
    code(r, "Split", js("split.js", common=False, __TEXT__="$('Build review').first().json.msg", __CHAT__=lit(OWNER)))
    tg_send(r, "Send review")
    r.chain("Every day 19:00", "Get vocab", "Build review", "Put review", "Split", "Send review")
    r.dump("evening_review.json")


# ------------------------------------------------------------------ nextcloud seed files
def build_seed():
    nums = [("yksi", "واحد", "one"), ("kaksi", "اتنين", "two"), ("kolme", "تلاتة", "three"), ("neljä", "أربعة", "four"),
            ("viisi", "خمسة", "five"), ("kuusi", "ستة", "six"), ("seitsemän", "سبعة", "seven"), ("kahdeksan", "تمانية", "eight"),
            ("yhdeksän", "تسعة", "nine"), ("kymmenen", "عشرة", "ten"), ("yksitoista", "احداشر", "eleven"), ("kaksitoista", "اتناشر", "twelve"),
            ("kello", "الساعة", "clock, o'clock"), ("yli", "بعد (الساعة)", "past (minutes after the hour)"),
            ("vaille", "قبل / ناقص", "to (minutes before the hour)"), ("puoli", "نص", "half")]
    ex = {"kello": "Kello on kolme.", "yli": "Kello on viisi yli kolme.", "vaille": "Kello on viittä vaille neljä.", "puoli": "Kello on puoli neljä."}
    words = {k: {"fi": k, "ar": ar, "en": en, "example": ex.get(k, ""), "mnemonic": "", "chapter": "time (lesson 2026-11-20)",
                 "box": 1, "due": "2026-11-28", "added": "2026-11-27", "lapses": 0, "seen": 0} for k, ar, en in nums}
    (NCDIR / "vocab.json").write_text(json.dumps({"words": words}, ensure_ascii=False, indent=1), encoding="utf-8")
    (NCDIR / "notes.json").write_text(json.dumps({"notes": [
        {"date": "2026-11-27", "text": "Position: Suomen Mestari 1, kappale 3-4. Covered telling the time; his answer to 'kello on viisi' is still pending."},
        {"date": "2026-11-27", "text": "Wants memorization techniques, real-life drills and YKI practice; Egyptian Arabic explanations; short answers; one question at a time."}]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote nextcloud/vocab.json, notes.json")


if __name__ == "__main__":
    build_seed()
    build_chat()
    build_daily()
