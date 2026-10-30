"""Tables and figures of the article (article-figures-v2.md), from the reviewed result files only.

Run: python -I notes/figures/make_figures.py   (CPU, seconds; matplotlib)
Reads aggregate result files under ~/porkyevitch/experiences (verdicts, measures, diagnostics): no raw test data, no
image, no per-row prediction; the head diagnostic is read through its aggregate keys only (never its 'sample' rows).
Writes PNG figures and Markdown tables next to this script. Every value printed comes from a file named in the table.
"""
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

E = Path.home() / "porkyevitch/experiences"
OUT = Path(__file__).resolve().parent
SRC = {
    "verdicts": E / "2026-10-30-mesure-phase1/resultats/test/verdicts.json",
    "mesures_test": E / "2026-10-30-mesure-phase1/resultats/test/mesures_test.json",
    "diag_tete": E / "2026-10-30-diagnostic-tete/resultats/complet/diagnostic.json",
    "non_transfert": E / "2026-10-30-non-transfert/resultats/diagnostic.json",
    "a1": E / "2026-10-29-a1/resultats/diagnostic/diagnostic.json",
    "a1_dev": E / "2026-10-30-a1-dev-rijks/resultats/dev.json",
    "d3_bras1": E / "2026-10-30-d3-traine-profondeur/resultats/complet/bras1.json",
    "d3_bras2": E / "2026-10-30-d3-traine-profondeur/resultats/complet/bras2.json",
    "p9a": E / "2026-10-29-p9-a/resultats/mesures-0/verdicts.json",
    "pe": E / "2026-10-30-petit-eleve/resultats/mesures/resultats.json",
    "accord_oae": E / "2026-10-30-diagnostic-tete/resultats/regard-confiants/ACCORD.md",
}
SYSTEMS = ("T_star", "TK", "T-niv", "T-H", "T-Z", "T-D")


def load(key):
    return json.loads(SRC[key].read_text())


def src(key):
    p = SRC[key]
    return f"`{p.relative_to(E)}` (`{hashlib.sha256(p.read_bytes()).hexdigest()[:8]}`)"


def num(x, n=4):
    """French decimal comma, as in the Results notes."""
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",").replace("-", "−")


def ci(c, n=4):
    return "—" if not c else f"[{num(c[0], n)} ; {num(c[1], n)}]"


def ent(n):
    return f"{n:,}".replace(",", "\u202f")


def table(path, title, source_keys, header, rows, note=""):
    lines = [f"### {title}", "", "Sources : " + ", ".join(src(k) for k in source_keys) + ".", "",
             "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    if note:
        lines += ["", note]
    (OUT / path).write_text("\n".join(lines) + "\n")


def forest(ax, labels, deltas, cis, title, ref=0.0, marks=None):
    ys = range(len(labels))[::-1]
    for y, d, c in zip(ys, deltas, cis):
        if d is None:
            continue
        ax.plot(c, [y, y], color="0.3", lw=2)
        ax.plot(d, y, "o", color="0.1")
    ax.axvline(ref, color="0.5", lw=1, ls="--")
    for x, lab in (marks or []):
        ax.axvline(x, color="0.7", lw=1, ls=":")
        ax.text(x, len(labels) - 0.4, lab, fontsize=7, ha="center", color="0.4")
    ax.set_yticks(list(ys), labels)
    ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=8)


def phase1():
    v, m = load("verdicts")["verdicts"], load("mesures_test")
    rows = []
    for s in ("T0",) + SYSTEMS + ("TK-niv",):
        x = v.get(s, {})
        di, dr = x.get("delta_icai") or {}, x.get("delta_rijks") or {}
        hi = m["icai_test"].get(s, {}).get("hier_f1") if s in m["icai_test"] else None
        hr = m["rijks_test"].get(s, {}).get("hier_f1") if s in m["rijks_test"] else None
        rows.append([s.replace("T_star", "T*"), x.get("reference", "—").replace("T_star", "T*") if x else "—", num(hi), num(hr),
                     num(di.get("delta")), num(di.get("lower_one_sided_99_29")), ci(di.get("ci95_two_sided")),
                     num(dr.get("delta")), num(dr.get("lower_one_sided_99_29")), ci(dr.get("ci95_two_sided")),
                     "non exécutée" if x.get("executed") is False else ("non" if x else "référence")])
    table("tableau2_phase1.md", "Tableau 2 — Phase 1 : sept comparaisons, règle conjointe", ["verdicts", "mesures_test"],
          ["Système", "Réf.", "H ICAI", "H Rijks", "Δ ICAI", "borne 99,29 %", "IC95 ICAI", "Δ Rijks", "borne 99,29 %",
           "IC95 Rijks", "Retenue"], rows,
          "Règle : retenue si borne unilatérale Δ_Rijks > 0 et borne Δ_ICAI > −0,01 (niveau 1 − 0,05/7). IC95 descriptifs.")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
    labs = [s.replace("T_star", "T* − T0") if s == "T_star" else f"{s} − T*" for s in SYSTEMS]
    for ax, bank, name in ((axes[0], "delta_icai", "ICAI test (images)"), (axes[1], "delta_rijks", "Rijksmuseum test (composantes)")):
        forest(ax, labs, [v[s][bank]["delta"] for s in SYSTEMS], [v[s][bank]["ci95_two_sided"] for s in SYSTEMS],
               f"Δ H-F1, IC95 — {name}")
    fig.suptitle("Figure 1 — Phase 1 : aucune brique retenue (TK-niv non exécutée)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "figure1_phase1_ecarts.png", dpi=200)
    plt.close(fig)


def validation_diagnostic():
    d = load("diag_tete")
    b = d["systems"]["B_TZ"]
    rows = [[k + ("" if k in ("1", "6") else " ‡"), num(b["depth_nodes"][k]["recall"], 2), num(b["depth_nodes"][k]["precision"], 2),
             ent(b["depth_nodes"][k]["tp"] + b["depth_nodes"][k]["fn"])] for k in ("1", "2", "3", "4", "5", "6")]
    t = b["tranches_exact_codes"]["5-20"]
    gain = b["tranche_threshold_coordinate_ascent"]["hf1_adjusted_coordinate_ascent"] - b["reproduced_hf1"]
    note = (f"Codes vus 5–20 fois : macro-F1 {num(t['macro_f1'], 2)} sur {ent(t['codes'])} codes, "
            f"{num(t['macro_f1_represented'], 2)} sur les codes présents en validation. Seuils par tranche ajustés sur la "
            f"validation elle-même : +{num(gain)} de H-F1 (score optimiste, ni borne ni recette). Pearson du H-F1 par image, "
            f"T* contre B : {num(d['error_overlap_T_star_vs_B_TZ']['pearson_per_image_hf1'], 2)}. "
            "‡ Profondeurs 2 à 5 : lues dans le même fichier et vérifiées par Codex, mais non citées par les Résultats (à relire avant usage).")
    table("tableau3_diagnostic_validation.md", "Tableau 3 — Diagnostic de la tête B (T-Z) sur la validation ICAI, par profondeur",
          ["diag_tete"], ["Profondeur", "Rappel des nœuds", "Précision", "Nœuds vrais"], rows, note)


def audit():
    # counts copied from ACCORD.md (arbitrated line), recounted independently by Codex
    rows = [["O : motif jugé visible, code précis", 29], ["A : motif jugé visible, code générique", 46],
            ["E : motif jugé absent ou sens jugé faux", 25]]
    lines = ["### Tableau 4 — Jugements de modèles sur 100 « confiants absents » (validation, B p ≥ 0,9)", "",
             f"Source : {src('accord_oae')}, ligne des comptes arbitrés. Codes les plus spécifiques prédits à p ≥ 0,9 et absents de "
             "la vérité fermée, au plus deux par image (95 images). Deux regards de modèles (Claude, Grok), d'accord sur 53 couples "
             "sur 100 ; désaccords arbitrés à l'aveugle par Gemini, selon une règle écrite avant le troisième regard par le juge le "
             "plus strict. **Ni un score, ni une vérité, ni une borne du F1.**", "",
             "| Catégorie | Couples |", "|---|---|"] + [f"| {a} | {n} |" for a, n in rows]
    (OUT / "tableau4_audit.md").write_text("\n".join(lines) + "\n")


def non_transfert():
    n = load("non_transfert")
    ev = [("head_closure", "tête (fermeture)"), ("head_exact", "tête (exact)"), ("vote_available", "disponible chez les voisins"),
          ("vote_alone_at_tk_threshold", "vote seul au seuil de TK"), ("random_available", "contrôle aléatoire")]
    dev, val = n["banks"]["rijks_dev"]["main"], n["banks"]["icai_validation"]["main"]
    table("tableau5_non_transfert.md", "Tableau 5 — Non-transfert, cible G (codes > 100, profondeur ≥ 3), descriptif",
          ["non_transfert"], ["Événement", f"dev Rijks ({ent(dev['pairs'])} paires)", f"validation ICAI ({ent(val['pairs'])} paires)"],
          [[lab, num(dev["recall"][k], 3), num(val["recall"][k], 3)] for k, lab in ev],
          "La disponibilité est une union de 20 voisinages, sans coût en faux positifs : l'écart à la tête n'est pas un gain "
          "récupérable. Lectures interdites : « notices omises », « l'encodeur ne les contient pas », « le seuil est la cause », "
          "toute cause du non-transfert (D10).")
    fig, ax = plt.subplots(figsize=(6, 3))
    xs = range(len(ev))
    ax.bar([x - 0.2 for x in xs], [dev["recall"][k] for k, _ in ev], 0.4, label="dev Rijksmuseum", color="0.35")
    ax.bar([x + 0.2 for x in xs], [val["recall"][k] for k, _ in ev], 0.4, label="validation ICAI", color="0.75")
    ax.set_xticks(list(xs), [lab for _, lab in ev], rotation=20, ha="right", fontsize=7)
    ax.set_ylabel("part des paires (image, code)", fontsize=8)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    ax.set_title("Figure 2 — Non-transfert, descriptif : la tête rend moins que la disponibilité-union, sans cause établie", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figure2_non_transfert.png", dpi=200)
    plt.close(fig)


def a1():
    a, d = load("a1"), load("a1_dev")
    rows = [["V-diagnostic ICAI", "A1 (décodeur, q avec η = 0)", num(a["H"]["A1"])],
            ["", "seuil, même q qu'A1 (η = 0)", num(a["H"]["threshold_same_q"])],
            ["", "seuil, q propre réglé à part (η = 1, secondaire)", num(a["H"]["threshold_own_q"])],
            ["", "B (T-Z)", num(a["H"]["B"])], ["dev Rijksmuseum", "règle figée (seuil, q propre, η = 1)", num(d["H"]["rule"])],
            ["", "B (T-Z)", num(d["H"]["B"])], ["", "T*", num(d["H"]["T_star"])]]
    mb, mt = d["main_contrast_rule_minus_B"], d["reference_contrast_rule_minus_T_star"]
    table("tableau6_a1.md", "Tableau 6 — A1 sur la validation, puis sa règle figée sur le dev Rijksmuseum", ["a1", "a1_dev"],
          ["Banque", "Système", "H-F1"], rows,
          f"Dev : règle − B {num(mb['mean'])} {ci(mb['ci95'])} ; règle − T* {num(mt['mean'])} {ci(mt['ci95'])} "
          f"(composantes, {ent(d['bootstrap']['draws'])} tirages, graine {d['bootstrap']['seed']}) : transfert non établi.")
    fig, ax = plt.subplots(figsize=(6, 1.8))
    forest(ax, ["règle − B (T-Z)", "règle − T*"], [mb["mean"], mt["mean"]], [mb["ci95"], mt["ci95"]],
           "Figure 3 — A1-dev : transfert non établi (Δ ≤ 0, IC95 par composantes contient 0)")
    fig.tight_layout()
    fig.savefig(OUT / "figure3_a1_dev.png", dpi=200)
    plt.close(fig)


def d3():
    b1, b2 = load("d3_bras1"), load("d3_bras2")
    vl = b1["V_lecture"]
    rows = [[f"Bras 1 (vote rares, poids 0,25), validation entière ({ent(b1['arm']['eligible'])} évaluables)", "F_R",
             num(b1["arm"]["F_R"], 3), num(b1["B"]["F_R"], 3), ci(b1["bootstrap"]["F_R_arm_minus_B"], 3), "non"],
            ["", "témoin permuté F_R", num(b1["permuted_memory_witness"]["F_R"], 3), "", "", ""],
            [f"Bras 1, V-lecture ({ent(vl['arm']['eligible'])} évaluables), descriptif", "F_R", num(vl["arm"]["F_R"], 3),
             num(vl["B"]["F_R"], 3), "—", ""]]
    bl = b2["B_Vlec_children"]
    for s, x in sorted(b2["seeds"].items()):
        c = x["Vlec_children"]
        rows.append([f"Bras 2 (tête des enfants), V-lecture, graine {s}, t = {num(x['t'], 2)}"
                     + (" (repli)" if x["t_flagged_no_precision"] else ""), "rappel conditionnel / F1 enfants",
                     f"{num(c['conditional_recall'], 2)} / {num(c['F1'], 2)}", f"{num(bl['conditional_recall'], 2)} / {num(bl['F1'], 2)}", "", "non"])
    table("tableau7_d3.md", "Tableau 7 — D3, résultat négatif : bras 1 sur la validation entière et sur V-lecture, bras 2 sur V-lecture", ["d3_bras1", "d3_bras2"],
          ["Sonde", "Mesure", "Bras", "B", "IC95 de l'écart", "Retenue"], rows,
          f"Comptes en codes bruts exacts. La porte issue de B laisse passer {round(100 * bl['gate_coverage'])} % des vrais enfants. "
          "Bras 2 : aucun seuil n'atteint sur V-réglage la précision de B ; le repli signalé (t = 0,95) a été appliqué aux trois "
          "graines, le bras n'est donc pas mesuré à précision contrôlée. L'IC du bras 1 porte sur la validation entière seulement.")


def p9a():
    p = load("p9a")["verdicts"]
    arms = ("F", "controle_global", "A", "C")
    table("tableau8_p9a.md", "Tableau 8 — P9-A, graine 0 (validation ICAI), aucun bras retenu", ["p9a"],
          ["Bras", "ΔH", "ΔE", "ΔF_R", "Verdict"],
          [[a.replace("controle_global", "contrôle global"), num(p[a]["delta_H"]), num(p[a]["delta_E"]), num(p[a]["delta_F_R"]),
            p[a]["verdict"]] for a in arms], "Seuil de la règle G : ΔH ≥ 0,005. Graines 1 et 2 non lancées (§9.4, D15).")
    fig, ax = plt.subplots(figsize=(5, 2.2))
    xs = range(len(arms))
    ax.bar([x - 0.2 for x in xs], [p[a]["delta_H"] for a in arms], 0.4, label="ΔH", color="0.35")
    ax.bar([x + 0.2 for x in xs], [p[a]["delta_F_R"] for a in arms], 0.4, label="ΔF_R", color="0.75")
    ax.axhline(0.005, color="0.5", ls=":", lw=1)
    ax.text(-0.45, 0.0052, "seuil G (ΔH ≥ 0,005)", fontsize=7, color="0.4", ha="left")
    ax.axhline(0, color="0.2", lw=0.8)
    ax.set_xticks(list(xs), [a.replace("controle_global", "contrôle") for a in arms], fontsize=8)
    ax.set_ylim(-0.004, 0.006)
    ax.legend(fontsize=7, loc="lower left")
    ax.set_title("Figure 4 — P9-A, graine 0 : aucun bras retenu (ΔH sous le seuil G, ΔF_R négatif)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figure4_p9a.png", dpi=200)
    plt.close(fig)


def petit_eleve():
    r = load("pe")
    w = r["witnesses_measures"]
    rows = [[k.replace("x", "×") + ("" if k.startswith("28") else " ‡"), num(a["recall_at_30"], 3), num(a["ap50_agnostic"], 3),
             num(a["objects_per_image_score_ge_0.5"], 1)] for k, a in r["arms"].items()]
    rows += [["a priori (rectangles fixes)", num(w["a_priori"]["recall_at_30"], 3), "—", "—"],
             ["OWLv2", num(w["owlv2_base"]["recall_at_30"], 3), num(w["owlv2_base"]["ap50_agnostic"], 3), "—"],
             ["YOLOE-v8-S texte (descriptif)", num(w["yoloe_v8s_text"]["recall_at_30"], 3), num(w["yoloe_v8s_text"]["ap50_agnostic"], 3), "—"]]
    t = r["timing"]
    table("tableau9_petit_eleve.md", "Tableau 9 — Petit élève, 26 graphes Gemini (fidélité au professeur), lecture D2", ["pe"],
          ["Système", "rappel@30", "AP50 sans classe", "objets/image (score ≥ 0,5)"], rows,
          f"Lecture D2 (bras 28×28) : {', '.join(r['d2_reading']['states'])} → « {r['d2_reading']['issue']} ». Débit, forwards seulement (lot 32) : "
          f"élève complet {num(t['student_full_b32']['images_per_second_median'], 1)} img/s, OWLv2 "
          f"{num(t['owlv2_full']['images_per_second_median'], 1)} img/s (D = {num(t['D'], 2)}). Florence-2 : rappel "
          f"{num(w['florence2_base_od']['recall_all_boxes'], 3)} sur toutes ses boîtes. ‡ Bras 8×8 : secondaires, hors règle D2, "
          "vérifiés par Codex mais non cités par les Résultats (à relire avant usage).")
    prior = w["a_priori"]["recall_at_30"]
    main = {k: a for k, a in r["arms"].items() if k.startswith("28x28")}  # the D2 reading uses the 28×28 arms only
    side = {k: a for k, a in r["arms"].items() if k.startswith("8x8")}  # shown apart: descriptive, outside the D2 rule
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9, 3), sharey=True, gridspec_kw={"width_ratios": [6, 3]})
    names = [k.replace("28x28_seed", "élève 28×28, graine ") for k in main] + ["a priori", "OWLv2", "YOLOE (descriptif)"]
    vals = [a["recall_at_30"] for a in main.values()] + [prior, w["owlv2_base"]["recall_at_30"],
                                                         w["yoloe_v8s_text"]["recall_at_30"]]
    ax.bar(range(len(names)), vals, color=["0.35"] * len(main) + ["0.6", "0.8", "0.8"])
    ax.set_xticks(range(len(names)), names, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("rappel@30 sans classe", fontsize=8)
    ax.set_title("Règle D2 : bras 28×28 et témoins", fontsize=8)
    bx.bar(range(len(side)), [a["recall_at_30"] for a in side.values()], color="white", edgecolor="0.35", hatch="//")
    bx.set_xticks(range(len(side)), [k.replace("8x8_seed", "élève 8×8, graine ") for k in side], rotation=30, ha="right",
                  fontsize=7)
    above = [k.replace("8x8_seed", "graine ") for k, a in side.items() if a["recall_at_30"] > prior]
    bx.set_title("Descriptif, hors règle D2 : bras 8×8", fontsize=8)
    if above:
        bx.text(0.5, 0.03, f"{len(above)} bras 8×8 ({', '.join(above)})\ndépasse l'a priori" if len(above) == 1 else
                f"{len(above)} bras 8×8 ({', '.join(above)})\ndépassent l'a priori", transform=bx.transAxes, ha="center",
                fontsize=7, color="0.2", bbox={"facecolor": "white", "edgecolor": "0.7"})
    for a_ in (ax, bx):
        a_.axhline(prior, color="0.5", ls=":", lw=1)
    fig.suptitle("Figure 5 — Petit élève : les bras 28×28 ne battent pas l'a priori (fidélité à Gemini, 26 images)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figure5_petit_eleve.png", dpi=200)
    plt.close(fig)


def effectifs():
    v, d = load("verdicts")["denominators"], load("a1_dev")["population"]
    lines = ["### Tableau 1 — Effectifs", "",
             f"Sources : Méthodes v4 §1 (ICAI ; effectifs recoupés par Codex), {src('verdicts')} (dénominateurs de test), {src('a1_dev')} (dev).", "",
             "| Banque | Effectif | Nature |", "|---|---|---|",
             "| ICAI apprentissage | 81 951 images | effectif |", "| ICAI validation | 4 265 images, dont 4 241 évaluables | effectif |",
             f"| ICAI test | {v['icai_test']} images au dénominateur ({v['icai_excluded_empty_projected_truth']} vérité vide exclue) | effectif |",
             f"| Rijksmuseum test | {ent(v['rijks_test_images'])} images, {v['rijks_test_components']} composantes | effectif |",
             f"| Rijksmuseum dev | {d['images']} images, {d['components']} composantes | effectif |"]
    (OUT / "tableau1_effectifs.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    for step in (effectifs, phase1, validation_diagnostic, audit, non_transfert, a1, d3, p9a, petit_eleve):
        step()
    print("written:", sorted(p.name for p in OUT.iterdir() if p.suffix in (".png", ".md")))
