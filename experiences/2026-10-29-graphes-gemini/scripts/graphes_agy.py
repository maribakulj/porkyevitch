"""Gemini pass of the scene-graph pilot (PREINSCRIPTION.md): one fresh `agy -p` session per call, on the Mac (network calls only).

Usage: graphes_agy.py PILOTE CONSIGNE SCHEMA [--jobs 3]
  PILOTE   the downloaded draw (images/pNNN.*, verite.json, tirage.json); verite.json and tirage.json are never given to Gemini
  CONSIGNE consigne.md (fixed before any call), SCHEMA graphe.schema.json (structure enforced by agy --json-schema)
Model gemini-3.8-flash-medium (Marcel's choice, 18/10). Corrections B2 and B3 of Codex wA:p4 (29/10).

Proof that the image was shown to the model (B2): in agy's own conversation log (read only), a tool-result step
(step_type 132) with status 3 and no error, whose payload holds a read_file or view_file call on the canonical path of the
attached copy AND image bytes (mime image/jpeg or image/png). This is the shape of all 443 successful image reads found in
earlier logs on this Mac (29/10); a mere mention of the path, a failed or refused step, another image or an absent log is not a
proof. It proves the image was given to the model, not that the model understood it.

Attempts and resumption (B3): at most 3 calls per image IN TOTAL, across invocations. Persistent state per image in
PILOTE/graphes/pNNN/: attempts.jsonl (append only, fsync), one "started" line written before each call and one result line after,
and g.json for an accepted graph. A call runs in a fresh directory PILOTE/appels/pNNN-aK/ that holds only a copy of the image and
is deleted afterwards. On a new invocation: an image with an accepted attempt is re-checked (g.json parses and matches the recorded
sha256; image, prompt, model and schema sha256 equal the current ones; otherwise the run stops with an error, nothing is
overwritten); a g.json without an accepted record is set aside as g.orphan-N.json; started attempts count against the 3, even
without a result line. Costs are summed over every recorded attempt. Failed images stay in the denominator of 200.
"""
import hashlib, json, os, re, shutil, signal, sqlite3, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODEL = "gemini-3.8-flash-medium"
HISTORY = Path.home() / ".gemini/antigravity-cli/conversations"
TIMEOUT, ATTEMPTS = 900, 3
NO_TOOLS = ("Do not run any command and do not use any tool other than reading the attached image. Do not read any other file. "
            "Open the attached image first. If you cannot see it, answer only IMAGE_ABSENT: never describe an image you have not seen.")
READ_RESULT, DONE = 132, 3


def sha(b):
    return hashlib.sha256(b).hexdigest()


def image_shown(cid, path):
    """True only if agy's log holds a successful read_file/view_file result for exactly `path` carrying image bytes."""
    if not cid or not re.fullmatch(r"[0-9a-f-]{36}", cid):
        return False
    db = HISTORY / f"{cid}.db"
    if not db.exists():
        return False
    target = json.dumps(str(path))[1:-1].encode()
    try:
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
            rows = list(con.execute("SELECT step_type, status, error_details, step_payload FROM steps"))
    except sqlite3.Error:
        return False
    for step_type, status, error, payload in rows:
        if step_type != READ_RESULT or status != DONE or error is not None or not isinstance(payload, bytes):
            continue
        calls = re.findall(rb'(?:read_file|view_file)[^{]{0,8}\{"(?:Absolute)?Path":"([^"]+)"\}', payload)
        if calls and all(c == target for c in calls) and (b"image/jpeg" in payload or b"image/png" in payload):
            return True
    return False


def run_agy(cmd, cwd):
    """agy in its own process group, killed as a whole at the (wall-clock) deadline; returns stdout or ''."""
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    deadline = time.time() + TIMEOUT
    while True:
        try:
            out, _ = p.communicate(timeout=min(30, max(1, deadline - time.time())))
            return out
        except subprocess.TimeoutExpired:
            if time.time() >= deadline:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    p.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
                return ""


def append(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_atomic(path, text):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def one(image, root, consigne, schema_path, keys):
    out = root / "graphes" / image.stem
    out.mkdir(parents=True, exist_ok=True)
    log = out / "attempts.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    prompt = f"{consigne}\n\nImage: @{image.name}\n\n{NO_TOOLS}"
    ident = dict(keys, image_sha256=sha(image.read_bytes()), prompt_sha256=sha(prompt.encode()))
    accepted = [r for r in records if r.get("phase") == "result" and r.get("accepted")]
    g = out / "g.json"
    if accepted:
        r = accepted[0]
        if any(r.get(k) != v for k, v in ident.items()) or not g.exists() or sha(g.read_bytes()) != r.get("graph_sha256"):
            raise RuntimeError(f"{image.stem}: accepted attempt does not match the current inputs or its g.json; stopping")
        json.loads(g.read_text())
        return image.stem
    if g.exists():
        g.rename(out / f"g.orphan-{len(list(out.glob('g.orphan-*.json')))}.json")
    started = sum(1 for r in records if r.get("phase") == "started")
    for attempt in range(started, ATTEMPTS):
        call = root / "appels" / f"{image.stem}-a{attempt}"
        if call.exists():
            shutil.rmtree(call)
        call.mkdir(parents=True)
        local = call / image.name
        shutil.copyfile(image, local)
        append(log, dict(ident, phase="started", attempt=attempt, time=time.time()))
        t = time.time()
        stdout = run_agy(["agy", "-p", prompt, "--print-timeout", f"{TIMEOUT - 60}s", "--output-format", "json",
                          "--model", MODEL, "--json-schema", str(schema_path)], call)
        try:
            env = json.loads(stdout) if stdout.strip().startswith("{") else {}
        except json.JSONDecodeError:
            env = {}
        resp = (env.get("response") or "").strip()
        cid = env.get("conversation_id")
        shown = image_shown(cid, local.resolve()) and "IMAGE_ABSENT" not in resp
        try:
            parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", resp))
        except json.JSONDecodeError:
            parsed = None
        ok = env.get("status") == "SUCCESS" and shown and parsed is not None
        rec = dict(ident, phase="result", attempt=attempt, seconds=round(time.time() - t, 1), status=env.get("status"),
                   usage=env.get("usage"), conversation_id=cid, image_shown=shown, json_ok=parsed is not None, accepted=ok)
        if ok:
            text = json.dumps(parsed, ensure_ascii=False, indent=1)
            write_atomic(g, text)
            rec["graph_sha256"] = sha(text.encode())
        append(log, rec)
        shutil.rmtree(call)
        if ok:
            break
    return image.stem


def summary(root, images):
    """Counts over every recorded attempt. A started attempt without a result line (interrupted run) consumed a call whose duration
    and usage are unknown: it is counted in `unfinished`, and the recorded seconds are then marked incomplete (never read as zero)."""
    accepted, failed, seconds, calls, unfinished = [], [], 0.0, 0, 0
    for im in images:
        log = root / "graphes" / im.stem / "attempts.jsonl"
        recs = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        started = {r["attempt"] for r in recs if r.get("phase") == "started"}
        results = {r["attempt"] for r in recs if r.get("phase") == "result"}
        calls += len(started)
        unfinished += len(started - results)
        seconds += sum(r.get("seconds", 0) for r in recs if r.get("phase") == "result")
        (accepted if any(r.get("accepted") for r in recs if r.get("phase") == "result") else failed).append(im.stem)
    return accepted, failed, seconds, calls, unfinished


root, consigne_path, schema_path = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 3
consigne = consigne_path.read_text()
keys = {"model": MODEL, "consigne_sha256": sha(consigne.encode()), "schema_sha256": sha(schema_path.read_bytes())}
images = sorted((root / "images").glob("p[0-9][0-9][0-9].*"))
assert len(images) == 200, len(images)
t0 = time.time()
with ThreadPoolExecutor(jobs) as ex:
    list(ex.map(lambda im: one(im, root, consigne, schema_path, keys), images))
accepted, failed, seconds, calls, unfinished = summary(root, images)
write_atomic(root / "graphes" / "run.json", json.dumps(dict(keys, script_sha256=sha(Path(__file__).read_bytes()), images=len(images),
             accepted=len(accepted), failed=failed, calls=calls, calls_without_result=unfinished,
             recorded_call_seconds=round(seconds, 1), cost_complete=unfinished == 0,
             wall_seconds_this_invocation=round(time.time() - t0, 1), jobs=jobs), indent=1))
print(f"accepted {len(accepted)}/200, failed {len(failed)}, calls {calls}, without result {unfinished}")
