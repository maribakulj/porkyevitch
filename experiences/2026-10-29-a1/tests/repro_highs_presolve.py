"""Reproduces the HiGHS presolve case of CODE.md from the frozen fixture (no a1 code involved).
Run: python -I tests/repro_highs_presolve.py   (prints versions, then presolve on/off x objective unscaled/scaled)"""
import json
from pathlib import Path
import platform
import sys

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

f = json.loads((Path(__file__).resolve().parent / "fixtures" / "highs_presolve_case.json").read_text())
w = np.array(f["w"])
n = len(w)
data, ri, ci = [], [], []
for r, row in enumerate(f["rows"]):
    for col, val in row:
        data.append(val), ri.append(r), ci.append(col)
A = csr_matrix((data, (ri, ci)), shape=(len(f["rows"]), n))
lo = [-np.inf if v is None else v for v in f["lo"]]
try:
    from scipy.optimize._highspy import _core as hc
    highs = f"{hc.HIGHS_VERSION_MAJOR}.{hc.HIGHS_VERSION_MINOR}.{hc.HIGHS_VERSION_PATCH}"
except Exception:
    highs = "not exposed"
print("python", sys.version.split()[0], platform.platform(), "numpy", np.__version__, "scipy", scipy.__version__,
      "HiGHS", highs)
print("sort value (closed, feasible)", repr(f["sort_value"]))
x_sort = np.zeros(n)
x_sort[f["sort_set"]] = 1
print("sort set feasible:", bool(np.all(A @ x_sort >= np.array(lo) - 1e-12) and np.all(A @ x_sort <= np.array(f["hi"]) + 1e-12)))
for scale_name, scale in (("unscaled (as found)", 1.0), ("scaled max w = 1e6 (current a1_core)", 1e6 / w.max())):
    for presolve in (True, False):
        res = milp(-scale * w, constraints=LinearConstraint(A, lo, f["hi"]), integrality=np.ones(n), bounds=Bounds(0, 1),
                   options={"mip_rel_gap": 0.0, "presolve": presolve})
        x = np.round(res.x).astype(int)
        print(f"{scale_name:40s} presolve={presolve!s:5s} status={res.status} value={float(w @ x)!r} "
              f"dual_gap={abs(res.mip_dual_bound - res.fun):.3g}")
