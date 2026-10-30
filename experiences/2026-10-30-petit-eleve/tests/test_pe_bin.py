"""D11: the student pilot reads its inputs from a pinned pe-entrees.bin, extracted safely outside /kaggle/working.
Fictitious archives in temporary folders; the real archive is rebuilt and compared when the source folder exists."""
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "outils"))
import kaggle_pe_run as k  # noqa: E402
import construire_entrees_bin as builder  # noqa: E402


def tar_bytes(entries):
    """entries: {name: bytes} or {name: ("symlink", target)}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, body in entries.items():
            info = tarfile.TarInfo(name)
            if isinstance(body, tuple):
                info.type, info.linkname = tarfile.SYMTYPE, body[1]
                tar.addfile(info)
            else:
                info.size = len(body)
                tar.addfile(info, io.BytesIO(body))
    return buf.getvalue()


def good_entries():
    return {"listes.json": b"{}", "scripts/pe_kaggle.py": (ROOT / "scripts/pe_kaggle.py").read_bytes(),
            "scripts/pe_common.py": (ROOT / "scripts/pe_common.py").read_bytes(), "images/p000.jpg": b"\xff\xd8 jpeg"}


class BinTest(unittest.TestCase):
    def setUp(self):
        self.mounted = Path(tempfile.mkdtemp())
        self.work = Path(tempfile.mkdtemp()) / "x"
        self.saved = (k.ENTREES_SHA256, k.SCELLE_SHA256)

    def tearDown(self):
        k.ENTREES_SHA256, k.SCELLE_SHA256 = self.saved

    def put(self, name, body, sub="d1"):
        p = self.mounted / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        return hashlib.sha256(body).hexdigest()

    def test_valid_archive_is_extracted_outside_working(self):
        k.ENTREES_SHA256 = self.put("pe-entrees.bin", tar_bytes(good_entries()))
        root = k.entries(self.work, str(self.mounted))
        self.assertTrue((root / "images/p000.jpg").is_file())
        self.assertEqual(root, self.work / "pe-in")
        self.assertFalse(k.EXTRACT.startswith("/kaggle/working"))

    def test_wrong_sha_two_archives_and_existing_destination_refused(self):
        self.put("pe-entrees.bin", tar_bytes(good_entries()))
        k.ENTREES_SHA256 = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "sha is not the pinned one"):
            k.entries(self.work, str(self.mounted))
        k.ENTREES_SHA256 = self.put("pe-entrees.bin", tar_bytes(good_entries()), sub="d2")
        with self.assertRaisesRegex(RuntimeError, "not found exactly once"):
            k.entries(self.work, str(self.mounted))

    def test_unsafe_members_refused_before_writing(self):
        for bad in ({"../evil": b"x"}, {"/abs": b"x"}, {"lien": ("symlink", "/etc/passwd")}):
            m = Path(tempfile.mkdtemp())
            body = tar_bytes({**good_entries(), **bad})
            (m / "pe-entrees.bin").write_bytes(body)
            k.ENTREES_SHA256 = hashlib.sha256(body).hexdigest()
            work = Path(tempfile.mkdtemp()) / "x"
            with self.assertRaises(RuntimeError):
                k.entries(work, str(m))
            self.assertFalse((work / "pe-in").exists())

    def test_reviewed_scripts_required_and_listes_at_root(self):
        e = good_entries()
        e["scripts/pe_kaggle.py"] = b"changed"
        k.ENTREES_SHA256 = self.put("pe-entrees.bin", tar_bytes(e))
        with self.assertRaisesRegex(RuntimeError, "not the reviewed one"):
            k.entries(self.work, str(self.mounted))
        m = Path(tempfile.mkdtemp())
        e = good_entries()
        e["sub/listes.json"] = e.pop("listes.json")
        body = tar_bytes(e)
        (m / "pe-entrees.bin").write_bytes(body)
        k.ENTREES_SHA256 = hashlib.sha256(body).hexdigest()
        with self.assertRaisesRegex(RuntimeError, "listes.json must be at the root"):
            k.entries(Path(tempfile.mkdtemp()) / "y", str(m))

    def test_sealed_predictions_kernel_output_or_pinned_archive(self):
        self.put("MANIFEST_PREDICTIONS.json", b"{}", sub="sortie")
        self.assertEqual(k.sealed_predictions(self.work, str(self.mounted)), str(self.mounted / "sortie"))
        m = Path(tempfile.mkdtemp())
        body = tar_bytes({"MANIFEST_PREDICTIONS.json": b"{}", "planche/p001.jpg": b"jpg"})
        (m / "pe-scelle.bin").write_bytes(body)
        k.SCELLE_SHA256 = None
        with self.assertRaisesRegex(RuntimeError, "needs a pinned sha"):
            k.sealed_predictions(Path(tempfile.mkdtemp()) / "z", str(m))
        k.SCELLE_SHA256 = hashlib.sha256(body).hexdigest()
        work = Path(tempfile.mkdtemp()) / "z"
        self.assertEqual(k.sealed_predictions(work, str(m)), str(work / "pe-scelle-in"))

    def test_pins(self):
        self.assertEqual(len(k.ENTREES_SHA256), 64)
        self.assertIsNone(k.SCELLE_SHA256)
        for name, want in k.SCRIPT_SHA256.items():
            self.assertEqual(hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest(), want)


class BuilderTest(unittest.TestCase):
    SOURCE = Path.home() / "porkyevitch-donnees/petit-eleve/upload"

    @unittest.skipUnless(SOURCE.is_dir(), "former upload folder absent")
    def test_real_archive_is_reproducible_and_pinned(self):
        out = Path(tempfile.mkdtemp())
        a, n = builder.build(self.SOURCE, out / "a.bin")
        b, _ = builder.build(self.SOURCE, out / "b.bin")
        self.assertEqual(a, b)
        self.assertEqual(a, k.ENTREES_SHA256)
        self.assertEqual(n, 2 + 3 + 166 + 158 + 30)
        with tarfile.open(out / "a.bin") as tar:
            names = tar.getnames()
        self.assertNotIn("scripts/kaggle_pe_run.py", names)
        self.assertFalse(any(Path(x).name.startswith("._") for x in names))


if __name__ == "__main__":
    unittest.main(verbosity=2)
