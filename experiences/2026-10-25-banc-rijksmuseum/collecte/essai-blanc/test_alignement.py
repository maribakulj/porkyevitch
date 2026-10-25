# Synthetic checks of collecte_notices.record (no real data): Codex's N1 counter-example and neighbours.
import sys, tempfile
src = open(sys.argv[1]).read().split("script_sha = ")[0]
sys.argv = ["x", tempfile.mkdtemp(), tempfile.mkdtemp()]
ns = {"__file__": "x"}; exec(src, ns)
PDM, CC0 = ns["PDM"], ns["CC0"]
R = lambda u: {"subject_to": [{"classified_as": [{"id": u}]}]}
def D(i, pdm): return {"id": f"d{i}", "access_point": [{"id": f"https://iiif.micr.io/X{i}/full/max/0/default.jpg"}], **(R(PDM) if pdm else {})}
def V(i, code, digs, pdm=False):
    return {"id": f"v{i}", "represents_instance_of_type": [{"equivalent": [{"id": f"https://iconclass.org/{code}"}]}] if code else [],
            "digitally_shown_by": digs, **(R(PDM) if pdm else {})}
def obj(*vs): return {"id": "o", "subject_of": [R(CC0)], "shows": list(vs)}
store = {}
ns["get"] = lambda u: store[u]
c = {"parts_role_other": 0, "actor_without_id": 0, "iconclass_uri_unsupported": 0, "place_skipped": 0}
cases = {
 "one view, PDM": obj(V(1, "11A", [D(1, False)], pdm=True)),
 "N1: two coded views, only first admissible": obj(V(1, "11A", [D(1, True)]), V(2, "25F", [D(2, False)])),
 "two coded views, both admissible": obj(V(1, "11A", [D(1, True)]), V(2, "25F", [D(2, True)])),
 "coded view without digital": obj(V(1, "11A", [D(1, True)]), V(2, "25F", [])),
 "second view uncoded, other digital": obj(V(1, "11A", [D(1, True)]), V(2, None, [D(2, False)])),
 "single coded digital not admissible": obj(V(1, "11A", [D(1, False)])),
}
for name, o in cases.items():
    store["o"] = o
    r = ns["record"]("o", ["painting"], c)
    print(f"{name:45s} eligible={r['eligible']} excluded={r['excluded']} image={(r['image'] or {}).get('digital')}")
