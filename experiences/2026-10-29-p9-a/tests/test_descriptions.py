"""Synthetic tests of the official-description conflict rule in p9a_prepare.descriptions().

Functions are extracted by AST (torch is not needed); input_path is replaced by a plain resolve.
The last test reads the pinned public files and the E0 vocabulary if present locally, never tensors:
the checkpoint pickle is read with an unpickler that maps every class to an inert object.
Run: python3 -I tests/test_descriptions.py
"""
import ast
import collections
import hashlib
import io
from pathlib import Path
import pickle
import re
import tempfile
import unicodedata
import unittest
import zipfile

HERE = Path(__file__).resolve().parents[1]
ICONCLASS = Path.home() / "porkyevitch-donnees/p9a/iconclass"
E0_CHECKPOINT = Path.home() / "porkyevitch-donnees/e0-complet/t_long.pt"
CONFLICT = "83(SHAKESPEARE, Othello, Act 4, scene 1)"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load(module, names, **extra):
    tree = ast.parse((HERE / "scripts" / module).read_text())
    code = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign)) and
            (getattr(n, "name", None) in names or
             any(getattr(t, "id", None) in names for t in getattr(n, "targets", [])))]
    namespace = {"hashlib": hashlib, "re": re, "unicodedata": unicodedata, "require": require,
                 "input_path": lambda p: Path(p).resolve(strict=True),
                 "sha": lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(), **extra}
    exec(compile(ast.Module(code, []), module, "exec"), namespace)
    return namespace


common = load("p9a_common.py", {"PART", "TOKEN", "_anc", "ancestors"})
prepare = load("p9a_prepare.py", {"ENGLISH_BLOBS", "descriptions", "texts_for_vocab"},
               ancestors=common["ancestors"])


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def vocabulary_from_checkpoint(path):
    class Inert(dict):
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return Inert()

        def __setstate__(self, state):
            pass

    class Safe(pickle.Unpickler):
        def find_class(self, module, name):
            return collections.OrderedDict if (module, name) == ("collections", "OrderedDict") else Inert

        def persistent_load(self, pid):
            return None

    archive = zipfile.ZipFile(path)
    name = next(n for n in archive.namelist() if n.endswith("data.pkl"))
    return list(Safe(io.BytesIO(archive.read(name))).load()["vocab"])


class DescriptionConflictTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved = dict(prepare["ENGLISH_BLOBS"])

    def tearDown(self):
        prepare["ENGLISH_BLOBS"].clear()
        prepare["ENGLISH_BLOBS"].update(self.saved)
        self.tmp.cleanup()

    def files(self, contents):
        prepare["ENGLISH_BLOBS"].clear()
        for name, text in contents.items():
            path = self.root / "txt/en" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
            prepare["ENGLISH_BLOBS"]["txt/en/" + name] = git_blob(text.encode())

    def test_conflict_outside_vocabulary_dropped_and_logged(self):
        self.files({"a.txt": "11|Christ\n83(X, Act 4)|first\n", "b.txt": "83(X, Act 4)|second\n11H|saints\n"})
        dictionary, provenance, dropped = prepare["descriptions"](self.root, {"11", "11H"})
        self.assertEqual(dictionary, {"11": "Christ", "11H": "saints"})
        self.assertEqual([d["code"] for d in dropped], ["83(X, Act 4)"])
        self.assertEqual([(o["path"], o["line"]) for o in dropped[0]["occurrences"]],
                         [("txt/en/a.txt", 2), ("txt/en/b.txt", 1)])
        self.assertEqual(len(provenance), 2)

    def test_conflict_inside_vocabulary_stops(self):
        self.files({"a.txt": "11|Christ\n11|other\n"})
        with self.assertRaisesRegex(RuntimeError, "conflicting exact description in vocabulary: 11"):
            prepare["descriptions"](self.root, {"11"})

    def test_identical_duplicate_kept_not_logged(self):
        self.files({"a.txt": "11|Christ\n", "b.txt": "11|Christ\n"})
        dictionary, _, dropped = prepare["descriptions"](self.root, {"11"})
        self.assertEqual(dictionary, {"11": "Christ"})
        self.assertEqual(dropped, [])

    def test_pinned_blob_mismatch_still_refused(self):
        self.files({"a.txt": "11|Christ\n"})
        prepare["ENGLISH_BLOBS"]["txt/en/a.txt"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "pinned Iconclass blob mismatch"):
            prepare["descriptions"](self.root, {"11"})

    def test_dropped_key_never_changes_vocabulary_texts(self):
        # V is closed under ancestors, so a key outside V is never looked up for an exact text or a broader one.
        self.files({"a.txt": "1|religion\n11|Christ\n11X|first\n", "b.txt": "11X|second\n"})
        vocab = ["1", "11", "11A"]
        data = type("Data", (), {"vocab": vocab})
        dictionary, _, _ = prepare["descriptions"](self.root, set(vocab))
        for kept in ("first", "second"):
            with_choice = dict(dictionary, **{"11X": kept})
            self.assertEqual(prepare["texts_for_vocab"](data, dictionary), prepare["texts_for_vocab"](data, with_choice))

    @unittest.skipUnless((ICONCLASS / "txt/en").is_dir() and E0_CHECKPOINT.is_file(), "pinned public files absent")
    def test_real_pinned_files_and_e0_vocabulary(self):
        vocab = vocabulary_from_checkpoint(E0_CHECKPOINT)
        self.assertEqual((len(vocab), len(set(vocab))), (7907, 7907))
        dictionary, provenance, dropped = prepare["descriptions"](ICONCLASS, set(vocab))
        self.assertEqual([d["code"] for d in dropped], [CONFLICT])
        self.assertEqual([(o["path"], o["line"]) for o in dropped[0]["occurrences"]],
                         [("txt/en/txt_en_shakespeare.txt", 483), ("txt/en/txt_en_shakespeare.txt", 486)])
        self.assertNotIn(CONFLICT, dictionary)
        self.assertEqual(len(provenance), 7)
        self.assertTrue(all(ancestors <= set(vocab) for ancestors in map(common["ancestors"], vocab)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
