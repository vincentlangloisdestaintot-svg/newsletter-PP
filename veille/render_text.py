# -*- coding: utf-8 -*-
"""Rendus markdown et HTML — version développée.

Le PDF rend le condensé (`texte`), ces deux rendus rendent le développé
(`developpe`). Même JSON, deux profondeurs. Si le développé manque, on retombe
sur le condensé plutôt que de rendre une section vide.
"""
from __future__ import annotations

import html

LIB_STATUT = {
    "EN VIGUEUR": "En vigueur",
    "VOTE NON APPLICABLE": "Voté, non applicable",
    "EN DISCUSSION": "En discussion",
}


def long(bloc: dict, cle_repli: str = "texte") -> str:
    """Version développée d'un bloc, ou son condensé à défaut."""
    if not isinstance(bloc, dict):
        return ""
    return (bloc.get("developpe") or bloc.get(cle_repli) or "").strip()


def markdown(brief: dict, sante: str, constats: list[str]) -> str:
    L: list[str] = [f"# Veille patrimoniale — {brief['date_titre'].title()}", ""]
    L += [f"> Contrôle automatique : {sante}", ""]
    if constats:
        L.append("> **Contrôles bloquants à relire avant réutilisation :**")
        L += [f"> - {c}" for c in constats]
        L.append("")

    b1 = brief["bloc1"]
    L += ["## 1. Le chiffre du jour", "",
          f"**{b1['valeur']}**", "", long(b1), "", _src(b1["sources"]), ""]

    L += ["## 2. Marchés actions et matières premières", "",
          long(brief["bloc2"]), "", _src(brief["bloc2"]["sources"]), ""]

    L += ["## 3. Taux et obligataire", "",
          long(brief["bloc3"]), "", _src(brief["bloc3"]["sources"]), ""]

    L += ["## 4. Fiscalité et réglementaire", ""]
    for el in brief["bloc4"]["elements"]:
        L.append(f"**{LIB_STATUT.get(el['statut'], el['statut'])}**")
        L.append("")
        L.append(long(el))
        L.append("")
    L += [_src(brief["bloc4"]["sources"]), ""]

    L += ["## 5. Assurance vie, retraite, épargne", ""]
    for t in brief["bloc5"].get("tuiles", []):
        L.append(f"- **{t['label']}** : {t['valeur']} — {t['contexte']}")
    if brief["bloc5"].get("tuiles"):
        L.append("")
    L += [long(brief["bloc5"]), "", _src(brief["bloc5"]["sources"]), ""]

    b6 = brief["bloc6"]
    L += [f"## 6. Le point du jour — format {b6['format'].lower()}", "",
          long(b6, "intro"), "", f"> {b6['formulation']}", "",
          _src(b6["sources"]), ""]

    if brief.get("chiffres_non_confirmes"):
        L += ["### Non confirmé à la source ce matin", ""]
        L += [f"- {x}" for x in brief["chiffres_non_confirmes"]]
        L.append("")

    cit = brief["citation"]
    L += ["---", "", f"*{cit['texte']}*"]
    if cit.get("attribution"):
        L.append(f"— {cit['attribution']}")
    return "\n".join(L)


def _src(urls: list[str]) -> str:
    return "*Sources : " + (" · ".join(urls) if urls else "non renseignée") + "*"


# --------------------------------------------------------------------------
CSS = """
body{margin:0;background:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,
"Segoe UI",Helvetica,Arial,sans-serif;color:#1a1a2e;}
.wrap{max-width:660px;margin:0 auto;background:#fff;}
.band{background:#12213b;color:#fff;padding:20px 24px 8px;}
.band h1{margin:0;font-size:21px;letter-spacing:.2px;}
.band h1 span{color:#c81e2c;}
.band .ed{font-size:11px;font-weight:700;opacity:.85;margin-top:6px;
letter-spacing:.6px;}
.band .tag{font-size:12px;font-style:italic;color:#c9cedb;margin:8px 0 12px;}
.health{background:#eef1f5;color:#41506b;font-size:12px;padding:9px 24px;
border-bottom:1px solid #dde1e8;}
.alert{background:#fdf2f2;border:1px solid #e6b8bb;margin:14px 24px;
padding:10px 12px;border-radius:4px;}
.alert b{color:#7a3b3b;font-size:12px;display:block;margin-bottom:5px;}
.alert li{font-size:12px;line-height:1.5;}
.hero{background:#c81e2c;color:#fff;padding:18px 24px;}
.hero .k{font-size:11px;font-weight:700;color:#f5c6ca;letter-spacing:.6px;}
.hero .v{font-size:36px;font-weight:800;line-height:1.1;margin:2px 0 8px;}
.hero .t{font-size:14.5px;line-height:1.6;}
.sec{padding:4px 24px 2px;}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:#12213b;
margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid #12213b;}
p{font-size:15px;line-height:1.68;margin:0 0 13px;}
.src{font-size:11px;font-style:italic;color:#6b7280;margin:0 0 6px;
word-break:break-word;}
table.tiles{width:100%;border-collapse:separate;border-spacing:4px;}
table.tiles td{background:#f2f4f7;border:1px solid #dde1e8;padding:8px;
width:25%;vertical-align:top;}
.tl{font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.3px;}
.tv{font-size:16px;font-weight:800;color:#12213b;margin:2px 0;}
.tc{font-size:9px;color:#6b7280;line-height:1.35;}
.st{border:1px solid #dde1e8;margin-bottom:10px;}
.st .lab{color:#fff;font-size:10px;font-weight:700;padding:8px 9px;width:104px;
text-align:center;vertical-align:top;}
.st .txt{font-size:14.5px;line-height:1.62;padding:10px 12px;background:#fbfbfc;}
.point{background:#12213b;color:#fff;padding:18px 24px;margin-top:22px;}
.point h3{margin:0 0 10px;font-size:14px;letter-spacing:.4px;}
.point p{color:#fff;font-size:14.5px;line-height:1.65;}
.point .q{color:#ffd9dc;font-weight:700;font-style:italic;font-size:15px;
border-left:3px solid #c81e2c;padding-left:12px;}
.quote{text-align:center;padding:24px;}
.quote .q{color:#c81e2c;font-style:italic;font-weight:700;font-size:16px;}
.quote .a{color:#12213b;font-size:11px;font-weight:700;margin-top:6px;
text-transform:uppercase;}
.foot{padding:14px 24px 26px;font-size:11px;color:#6b7280;line-height:1.55;
border-top:1px solid #dde1e8;}
"""

COULEUR_STATUT = {"EN VIGUEUR": "#2f6f4f", "VOTE NON APPLICABLE": "#a8781f",
                  "EN DISCUSSION": "#7a3b3b"}


def _e(t) -> str:
    return html.escape(str(t or ""), quote=False)


def _paras(texte: str) -> str:
    """Découpe un texte long en paragraphes HTML."""
    blocs = [b.strip() for b in str(texte or "").split("\n\n") if b.strip()]
    if not blocs:
        blocs = [str(texte or "").strip()]
    return "".join(f"<p>{_e(b)}</p>" for b in blocs if b)


def _tiles_html(tuiles: list[dict]) -> str:
    if not tuiles:
        return ""
    out = ["<table class='tiles'>"]
    for i in range(0, len(tuiles), 4):
        out.append("<tr>")
        rang = tuiles[i:i + 4]
        for t in rang:
            out.append(
                f"<td><div class='tl'>{_e(t['label'])}</div>"
                f"<div class='tv'>{_e(t['valeur'])}</div>"
                f"<div class='tc'>{_e(t['contexte'])}</div></td>")
        out += ["<td></td>"] * (4 - len(rang))
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def email_html(brief: dict, sante: str, constats: list[str]) -> str:
    b1, b6 = brief["bloc1"], brief["bloc6"]

    alerte = ""
    if constats:
        items = "".join(f"<li>{_e(c)}</li>" for c in constats[:8])
        alerte = (f"<div class='alert'><b>Contrôles bloquants — à relire avant "
                  f"toute réutilisation en rendez-vous</b><ul>{items}</ul></div>")

    fiscal = "".join(
        f"<table class='st' width='100%'><tr>"
        f"<td class='lab' style='background:{COULEUR_STATUT.get(el['statut'], '#6b7280')}'>"
        f"{_e(LIB_STATUT.get(el['statut'], el['statut'])).upper()}</td>"
        f"<td class='txt'>{_paras(long(el))}</td></tr></table>"
        for el in brief["bloc4"]["elements"])

    nc = ""
    if brief.get("chiffres_non_confirmes"):
        items = "".join(f"<li>{_e(x)}</li>" for x in brief["chiffres_non_confirmes"])
        nc = (f"<div class='sec'><h2>Non confirmé à la source ce matin</h2>"
              f"<ul style='font-size:14px;line-height:1.65;color:#41506b'>{items}</ul></div>")

    cit = brief["citation"]
    attribution = (f"<div class='a'>— {_e(cit['attribution'])}</div>"
                   if cit.get("attribution") else "")

    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veille patrimoniale — {_e(brief['date_titre'])}</title><style>{CSS}</style>
</head><body><div class="wrap">

<div class="band">
  <h1>VEILLE <span>PATRIMONIALE</span></h1>
  <div class="ed">ÉDITION DU {_e(brief['date_titre'])}</div>
  <div class="tag">Marchés, taux, fiscalité et épargne — sourcé et opposable.
  Le PDF joint en donne la version deux pages.</div>
</div>

<div class="health">Contrôle automatique : {_e(sante)}</div>
{alerte}

<div class="hero">
  <div class="k">LE CHIFFRE DU JOUR</div>
  <div class="v">{_e(b1['valeur'])}</div>
  <div class="t">{_e(b1.get('texte') or long(b1))}</div>
</div>

<div class="sec">
  {_paras(b1.get('developpe', ''))}
  <p class="src">Sources : {_e(' · '.join(b1['sources']))}</p>

  <h2>Stats du jour</h2>
  {_tiles_html(brief['stats'])}
  <p style="font-size:13.5px;margin-top:12px">{_e(brief['note_echeance'])}</p>

  <h2>Taux et obligataire</h2>
  {_paras(long(brief['bloc3']))}
  <p class="src">Sources : {_e(' · '.join(brief['bloc3']['sources']))}</p>

  <h2>Marchés actions et matières premières</h2>
  {_paras(long(brief['bloc2']))}
  <p class="src">Sources : {_e(' · '.join(brief['bloc2']['sources']))}</p>

  <h2>Fiscalité et réglementaire</h2>
  {fiscal}
  <p class="src">Sources : {_e(' · '.join(brief['bloc4']['sources']))}</p>

  <h2>Assurance vie, retraite, épargne</h2>
  {_tiles_html(brief['bloc5'].get('tuiles', []))}
  {_paras(long(brief['bloc5']))}
  <p class="src">Sources : {_e(' · '.join(brief['bloc5']['sources']))}</p>
</div>

<div class="point">
  <h3>LE POINT DU JOUR — {_e(b6['format'])}</h3>
  {_paras(long(b6, 'intro'))}
  <p class="q">{_e(b6['formulation'])}</p>
</div>

{nc}

<div class="quote">
  <div class="q">{_e(cit['texte'])}</div>
  {attribution}
</div>

<div class="foot">
  Document de veille à usage professionnel interne. Ne constitue ni une
  recommandation d'investissement, ni un conseil personnalisé. Les performances
  passées ne préjugent pas des performances futures. La version deux pages de
  cette édition est jointe en PDF.
</div>

</div></body></html>"""
