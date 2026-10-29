"""Gemini pass of the scene-graph pilot (PREINSCRIPTION.md): one fresh `agy -p` session per image, on the Mac (network calls only).

Usage: graphes_agy.py PILOTE CONSIGNE SCHEMA [--jobs 3]
  PILOTE   the downloaded draw (images/pNNN.*, verite.json, tirage.json); verite.json and tirage.json are never given to Gemini
  CONSIGNE consigne.md (fixed before any call), SCHEMA graphe.schema.json (structure enforced by agy --json-schema)
For each image: a fresh directory PILOTE/agy/pNNN/ holding only a copy of the image; agy runs there with the image attached by
@name, the instruction to use no tool but reading that image, model gemini-3.8-flash-medium (Marcel's choice, 18/10).
Accepted only if the envelope status is SUCCESS, the response parses as JSON, and agy's own conversation log (read only) shows the
image was opened; otherwise up to 3 attempts, then the image is recorded as failed (it stays in the denominator).
Outputs per image: g.json (the graph, or absent), provenance.json (prompt sha256, calls with seconds, status, usage, conversation
id, image opened). Summary: PILOTE/agy/run.json (script sha256, model, consigne sha256, schema sha256, counts, seconds).
Nothing is retried after a success and nothing is selected by content.
"""
import hashlib, json, os, re, shutil, signal, sqlite3, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODEL = "gemini-3.8-flash-medium"
HISTORY = Path.home() / ".gemini/antigravity-cli/conversations"
TIMEOUT, ATTEMPTS = 900, 3
NO_TOOLS = ("Do not run any command and do not use any tool other than reading the attached image. Do not read any other file. "
            "Open the attached image first. If you cannot see it, answer only IMAGE_ABSENT: never describe an image you have not seen.")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def opened_paths(cid):
    db = HISTORY / f"{cid}.db"
    if not db.exists():
        return set()
    found = set()
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
        for (payload,) in con.execute("SELECT step_payload FROM steps"):
            if payload:
                text = payload.decode("utf-8", "ignore") if isinstance(payload, bytes) else str(payload)
                found.update(re.findall(r'"AbsolutePath":"([^"]+)"', text))
                found.update(re.findall(r'(?:read_file|view_file)[^{]{0,8}\{"Path":"([^"]+)"', text))
    return found


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


def one(image, root, consigne, schema_path):
    d = root / "agy" / image.stem
    d.mkdir(parents=True, exist_ok=True)
    if (d / "g.json").exists():
        return image.stem, True, 0.0
    local = d / image.name
    shutil.copyfile(image, local)
    prompt = f"{consigne}\n\nImage: @{image.name}\n\n{NO_TOOLS}"
    calls, graph = [], None
    for attempt in range(ATTEMPTS):
        t = time.time()
        out = run_agy(["agy", "-p", prompt, "--print-timeout", f"{TIMEOUT - 60}s", "--output-format", "json",
                       "--model", MODEL, "--json-schema", str(schema_path)], d)
        try:
            env = json.loads(out) if out.strip().startswith("{") else {}
        except json.JSONDecodeError:
            env = {}
        resp = (env.get("response") or "").strip()
        cid = env.get("conversation_id")
        seen = str(local.resolve()) in opened_paths(cid) if cid else False
        if "IMAGE_ABSENT" in resp:
            seen = False
        try:
            parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", resp))
        except json.JSONDecodeError:
            parsed = None
        calls.append({"attempt": attempt, "seconds": round(time.time() - t, 1), "status": env.get("status"),
                      "usage": env.get("usage"), "conversation_id": cid, "image_opened": seen, "json_ok": parsed is not None})
        if env.get("status") == "SUCCESS" and seen and parsed is not None:
            graph = parsed
            break
    if graph is not None:
        (d / "g.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1))
    (d / "provenance.json").write_text(json.dumps({"image": image.name, "image_sha256": sha(local.read_bytes()), "model": MODEL,
                                                   "prompt_sha256": sha(prompt.encode()), "calls": calls,
                                                   "accepted": graph is not None}, ensure_ascii=False, indent=1))
    local.unlink()  # the copy is not kept; the original stays in images/
    return image.stem, graph is not None, sum(c["seconds"] for c in calls)


root, consigne_path, schema_path = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 3
consigne = consigne_path.read_text()
images = sorted((root / "images").glob("p[0-9][0-9][0-9].*"))
assert len(images) == 200, len(images)
t0 = time.time()
with ThreadPoolExecutor(jobs) as ex:
    results = list(ex.map(lambda im: one(im, root, consigne, schema_path), images))
for stem, ok, s in results:
    print(stem, "ok" if ok else "FAILED", s, flush=True)
(root / "agy" / "run.json").write_text(json.dumps({
    "script_sha256": sha(Path(__file__).read_bytes()), "model": MODEL, "consigne_sha256": sha(consigne.encode()),
    "schema_sha256": sha(schema_path.read_bytes()), "images": len(images), "accepted": sum(ok for _, ok, _ in results),
    "failed": [stem for stem, ok, _ in results if not ok], "wall_seconds": round(time.time() - t0, 1),
    "call_seconds": round(sum(s for _, _, s in results), 1), "jobs": jobs}, indent=1))
