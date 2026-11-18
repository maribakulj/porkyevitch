#!/usr/bin/env python3
"""État de chaque idée du tableau, lu dans le graphe, et rapports lisibles (IDEES.md, idees.html).

Statut d'une idée (un seul) : « couverte » (une hypothèse la cite, ou la couvre), sinon « gardée » (aucun notateur
ne l'écarte), « écartée » (tous l'écartent), « désaccord » (un l'écarte, l'autre la garde). À part, le drapeau
« à réexaminer » : idée non couverte dont un écartement a une condition de levée maintenant remplie, ou en désaccord.

Usage : python3 graphe.py --config config.toml rapport-idees
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphe  # noqa: E402
from graphe import DCTERMS, LAB, PROV, RDF, SKOS  # noqa: E402

STATUTS = ("gardée", "écartée", "désaccord", "couverte", "à réexaminer")


def couvertes(g) -> set:
    """Idées déjà traitées : citées en source d'une hypothèse, en proche_de d'une idée interne, ou couvertes."""
    c = set(g.objects(None, LAB.couvre)) | {o for _, o in g.subject_objects(PROV.wasDerivedFrom)
                                            if (o, RDF.type, LAB.Idee) in g}
    for i in g.subjects(DCTERMS.source, LAB.interne):
        c |= set(g.objects(i, DCTERMS.relation))
    return c


def _txt(g, s, p) -> str:
    v = g.value(s, p)
    return str(v) if v is not None else ""


def _ident(g, n) -> str:
    return _txt(g, n, DCTERMS.identifier) or str(n).rsplit("/", 1)[-1].removeprefix("agent-")


def _score(g, n):
    v = g.value(n, LAB["score_S"])
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def conditions(g) -> dict:
    sortie = {}
    for c in g.subjects(SKOS.inScheme, LAB.conditions):
        etat, quand = _txt(g, c, LAB.etatCondition), _txt(g, c, LAB.leveeQuand) or "vraie"
        sortie[c] = {"id": _ident(g, c), "etat": etat, "levee_quand": quand, "levee": etat == quand,
                     "description": _txt(g, c, DCTERMS.description)}
    return sortie


def dernier_verdict(g, h) -> tuple[str, str] | None:
    """(identifiant, étiquette du statut) du dernier verdict non remplacé de l'hypothèse."""
    remplaces = set(g.objects(None, PROV.wasRevisionOf))
    cand = [(_txt(g, v, DCTERMS.created), str(v), v) for v in g.subjects(LAB.portesur, h) if v not in remplaces]
    if not cand:
        return None
    v = max(cand)[2]
    st = g.value(v, LAB.statut)
    return _ident(g, v), (_txt(g, st, SKOS.prefLabel) if st is not None else "?")


def hypotheses_par_idee(g) -> dict:
    """Idée -> hypothèses liées (source, couvre, ou idée interne proche) avec leur dernier verdict."""
    lien: dict = {}
    for h in g.subjects(RDF.type, LAB.Hypothese):
        cibles = set(g.objects(h, LAB.couvre))
        for o in g.objects(h, PROV.wasDerivedFrom):
            if (o, RDF.type, LAB.Idee) in g:
                cibles.add(o)
                if (o, DCTERMS.source, LAB.interne) in g:
                    cibles |= set(g.objects(o, DCTERMS.relation))
        v = dernier_verdict(g, h)
        for i in cibles:
            lien.setdefault(i, []).append({"id": _ident(g, h), "verdict": v[1] if v else "aucun verdict"})
    for i in lien:
        lien[i].sort(key=lambda x: x["id"])
    return lien


def etat_idees(g) -> list[dict]:
    conds, couv, hyps = conditions(g), couvertes(g), hypotheses_par_idee(g)
    sortie = []
    for i in sorted(g.subjects(RDF.type, LAB.Idee), key=str):
        if (i, DCTERMS.source, LAB.interne) in g:
            continue   # idée interne née d'une hypothèse, hors du tableau de 648
        nots = []
        for n in sorted(g.objects(i, LAB.notation), key=str):
            cond = g.value(n, LAB.leveeSi)
            dbl = g.value(n, LAB.doublonDe)
            el = g.value(n, LAB.elimine)
            nots.append({"notateur": _ident(g, g.value(n, LAB.notePar)) if g.value(n, LAB.notePar) else "?",
                         "elimine": bool(el) if el is not None else False,
                         "motif": _txt(g, n, LAB.motif), "justification": _txt(g, n, DCTERMS.description),
                         "condition": conds[cond]["id"] if cond in conds else None,
                         "levee": bool(cond in conds and conds[cond]["levee"]),
                         "doublon_de": (_ident(g, dbl) if (dbl, RDF.type, LAB.Idee) in g else str(dbl)) if dbl else None,
                         "s": _score(g, n)})
        n_el = sum(1 for n in nots if n["elimine"])
        if i in couv:
            statut = "couverte"
        elif nots and n_el == len(nots):
            statut = "écartée"
        elif n_el == 0:
            statut = "gardée"
        else:
            statut = "désaccord"
        raisons = []
        if i not in couv:
            for n in nots:
                if n["elimine"] and n["condition"] and n["levee"]:
                    raisons.append(f"levée : {n['condition']} ({n['notateur']})")
            if statut == "désaccord":
                raisons.append("désaccord entre notateurs")
        s_garde = max((n["s"] for n in nots if not n["elimine"] and n["s"] is not None), default=None)
        sortie.append({"id": _ident(g, i), "idee": _txt(g, i, DCTERMS.description), "source": "" if
                       (i, DCTERMS.source, LAB.interne) in g else _txt(g, i, DCTERMS.source),
                       "theme": _txt(g, i, LAB.theme), "statut": statut, "notations": nots, "hypotheses": hyps.get(i, []),
                       "a_reexaminer": bool(raisons), "raisons": raisons, "s_garde": s_garde})
    return sortie


def a_reexaminer(etats: list[dict]) -> list[dict]:
    """Levées d'abord (par identifiant), puis les désaccords par S décroissant du notateur qui garde."""
    lev = sorted((e for e in etats if e["a_reexaminer"] and any(r.startswith("levée") for r in e["raisons"])),
                 key=lambda e: e["id"])
    dis = sorted((e for e in etats if e["a_reexaminer"] and e not in lev),
                 key=lambda e: (e["s_garde"] is None, -(e["s_garde"] or 0), e["id"]))
    return lev + dis


def comptes(etats: list[dict]) -> dict:
    c = {s: 0 for s in STATUTS}
    for e in etats:
        c[e["statut"]] += 1
        c["à réexaminer"] += e["a_reexaminer"]
    return c


# ---------------------------------------------------------------- rendu

def _motifs(e: dict) -> list[str]:
    sortie = []
    for n in e["notations"]:
        if not n["elimine"]:
            sortie.append(f"{n['notateur']} : garde" + (f" (S {n['s']:g})" if n["s"] is not None else ""))
        else:
            t = n["motif"] + (f" : {n['justification']}" if n["justification"] else "")
            if n["doublon_de"]:
                t += f" [doublon de {n['doublon_de']}]"
            sortie.append(f"{n['notateur']} : écarte, {t}")
    return sortie


def _levee(e: dict) -> str:
    cs = sorted({n["condition"] + (" (levée)" if n["levee"] else "") for n in e["notations"]
                 if n["elimine"] and n["condition"]})
    return ", ".join(cs) or "—"


def _hyp(e: dict) -> str:
    return ", ".join(f"{h['id']} ({h['verdict']})" for h in e["hypotheses"]) or "—"


def en_markdown(etats: list[dict]) -> str:
    c = comptes(etats)
    L = ["# Idées du tableau", "",
         "Généré par `graphe.py rapport-idees` ; ne pas éditer à la main. Un statut par idée : couverte (une hypothèse "
         "la cite ou la couvre), sinon gardée, écartée (par les deux notateurs) ou en désaccord. « À réexaminer » est "
         "un drapeau à part : écartement dont la condition de levée est remplie, ou désaccord.", "",
         f"{len(etats)} idées : " + ", ".join(f"{s} {c[s]}" for s in STATUTS) + ".", ""]
    for s in STATUTS:
        lot = [e for e in a_reexaminer(etats) if True] if s == "à réexaminer" else [e for e in etats if e["statut"] == s]
        if not lot:
            continue
        L += [f"## {s[0].upper() + s[1:]} ({len(lot)})", "",
              "| id | idée | source | thème | statut | motifs des notateurs | condition de levée | hypothèses |",
              "|---|---|---|---|---|---|---|---|"]
        for e in lot:
            cell = lambda t: t.replace("|", "/").replace("\n", " ")   # noqa: E731
            L.append("| " + " | ".join(cell(x) for x in (
                e["id"], e["idee"], e["source"] or "—", e["theme"] or "—", e["statut"] + (" · à réexaminer" if e["a_reexaminer"] else ""),
                " ; ".join(_motifs(e)), _levee(e), _hyp(e))) + " |")
        L.append("")
    return "\n".join(L)


CSS = """
:root{--bg:#fafaf7;--fg:#1d1d1b;--mut:#66665f;--card:#fff;--bd:#d8d8d0;--ac:#2a5db0;--chip:#eceae2;--on:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17181a;--fg:#e8e8e3;--mut:#9a9a92;--card:#212326;--bd:#383b3f;--ac:#7aa7ee;--chip:#2b2e32;--on:#101214}}
:root[data-theme=dark]{--bg:#17181a;--fg:#e8e8e3;--mut:#9a9a92;--card:#212326;--bd:#383b3f;--ac:#7aa7ee;--chip:#2b2e32;--on:#101214}
*{box-sizing:border-box}body{margin:0;padding:12px 16px;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
h1{font-size:1.3rem;margin:.2em 0}p.n{color:var(--mut);margin:.2em 0 .8em}
.bar{display:flex;flex-wrap:wrap;gap:6px;margin:.6em 0}
button,input{font:inherit;color:inherit;background:var(--chip);border:1px solid var(--bd);border-radius:16px;padding:6px 12px}
button[aria-pressed=true]{background:var(--ac);color:var(--on);border-color:var(--ac)}
input{border-radius:8px;flex:1 1 220px;min-width:0;background:var(--card)}
table{border-collapse:collapse;width:100%}th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--bd)}
th{position:sticky;top:0;background:var(--bg);font-size:.85rem;color:var(--mut)}td.id{white-space:nowrap;font-weight:600}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;background:var(--chip);font-size:.8rem;white-space:nowrap}
.mot{font-size:.88rem}.mot div{margin-bottom:3px}
@media (max-width:760px){thead{display:none}table,tbody,tr,td{display:block;width:100%}
tr{background:var(--card);border:1px solid var(--bd);border-radius:8px;margin:0 0 10px;padding:6px 4px}
td{border:0;padding:3px 8px}td[data-l]::before{content:attr(data-l) " : ";color:var(--mut);font-size:.8rem}}
"""

JS = """
const rows=[...document.querySelectorAll('tbody tr')],bs=[...document.querySelectorAll('button[data-f]')],q=document.getElementById('q'),c=document.getElementById('cpt');
let f='toutes';
function run(){const t=q.value.toLowerCase();let n=0;rows.forEach(r=>{const ok=(f==='toutes'||r.dataset.s.split('|').includes(f))&&(!t||r.textContent.toLowerCase().includes(t));r.hidden=!ok;n+=ok});c.textContent=n+' idée(s) affichée(s)'}
bs.forEach(b=>b.onclick=()=>{f=b.dataset.f;bs.forEach(x=>x.setAttribute('aria-pressed',x===b));run()});q.oninput=run;run();
"""


def en_html(etats: list[dict]) -> str:
    e_ = html.escape
    c = comptes(etats)
    boutons = [f'<button data-f="toutes" aria-pressed="true">toutes ({len(etats)})</button>'] + [
        f'<button data-f="{e_(s)}" aria-pressed="false">{e_(s)} ({c[s]})</button>' for s in STATUTS]
    lignes = []
    for e in etats:
        tags = e["statut"] + ("|à réexaminer" if e["a_reexaminer"] else "")
        mot = "".join(f"<div>{e_(m)}</div>" for m in _motifs(e))
        lignes.append(
            f'<tr data-s="{e_(tags)}"><td class="id" data-l="id">{e_(e["id"])}</td><td data-l="idée">{e_(e["idee"])}</td>'
            f'<td data-l="source">{e_(e["source"] or "—")}</td><td data-l="thème">{e_(e["theme"] or "—")}</td>'
            f'<td data-l="statut"><span class="tag">{e_(e["statut"])}</span>'
            + (' <span class="tag">à réexaminer</span>' if e["a_reexaminer"] else "") + f'</td>'
            f'<td class="mot" data-l="notateurs">{mot}</td><td data-l="levée si">{e_(_levee(e))}</td>'
            f'<td data-l="hypothèses">{e_(_hyp(e))}</td></tr>')
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Idées du tableau</title>'
            f"<style>{CSS}</style></head><body><h1>Idées du tableau</h1>"
            '<p class="n">Un statut par idée ; « à réexaminer » : condition de levée remplie ou désaccord entre notateurs.</p>'
            f'<div class="bar">{"".join(boutons)}</div>'
            '<div class="bar"><input id="q" type="search" placeholder="Chercher (id, mot, motif, hypothèse)…"></div>'
            '<p class="n" id="cpt"></p><table><thead><tr><th>id</th><th>idée</th><th>source</th><th>thème</th>'
            '<th>statut</th><th>motifs des notateurs</th><th>condition de levée</th><th>hypothèses liées</th></tr></thead>'
            f'<tbody>{"".join(lignes)}</tbody></table><script>{JS}</script></body></html>\n')


def ecrire_rapports(g, cfg) -> list[Path]:
    etats = etat_idees(g)
    dossier = cfg.sortie("rapports", "rapports")
    dossier.mkdir(parents=True, exist_ok=True)
    md, ht = dossier / "IDEES.md", dossier / "idees.html"
    md.write_text(en_markdown(etats), encoding="utf-8")
    ht.write_text(en_html(etats), encoding="utf-8")
    return [md, ht]
