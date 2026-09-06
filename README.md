# Veille patrimoniale quotidienne

Brief de veille économique, financière et patrimoniale, produit chaque matin de
semaine à 6 h 30 (heure de Paris), envoyé par email en HTML avec le PDF en pièce
jointe, et archivé dans ce dépôt.

Destiné à un conseiller en gestion de patrimoine et courtier exerçant une
activité réglementée : chaque chiffre porte son émetteur, sa date et son statut
de vérification, et rien n'est publié qui n'ait été confirmé à la source.

**Coût : 0 € au-delà de l'abonnement Claude déjà payé.** Voir
[Coût](#coût) pour le détail.

---

## Architecture

Cinq couches séparées, là où la version précédente était un prompt unique
recopié dans une tâche planifiée.

| Couche | Rôle | Fichiers |
|---|---|---|
| **Données** | Récupère les chiffres de marché de façon déterministe, avec émetteur, URL et statut. Ne devine jamais. | `veille/providers/`, `veille/collect.py` |
| **Éditorial** | Rédige ce qui demande du jugement : fiscalité, réglementaire, assurance vie, point du jour. | `charte/`, `veille/schema.py` |
| **Contrôle** | Vérifie le texte produit par du code, pas par auto-déclaration. | `veille/validate.py` |
| **Rendu** | PDF, HTML et markdown depuis un JSON unique. | `veille/render_*.py` |
| **Livraison** | Email, puis archivage de l'édition. | `veille/deliver.py`, `archive.py` |

Trois principes tiennent l'ensemble.

**Un blanc assumé plutôt qu'une approximation.** Une donnée non récupérée part
en `non confirmé`, le brief l'écrit, et l'email affiche en tête combien de
chiffres ont été confirmés à la source. Aucun champ n'est comblé.

**Le contrôle n'est pas auto-déclaratif.** L'ancienne checklist demandait à
l'agent de se noter lui-même, à 6 h 30, sans témoin. Ici, `validate.py` relit le
texte produit et détecte : un chiffre publié alors que la collecte ne l'a pas
confirmé, une qualification d'opportunité de marché, une recommandation
d'investissement, un texte en discussion rédigé comme acquis, une source de
presse citée à la place de l'émetteur, une citation apocryphe, une projection à
l'indicatif futur. Les constats bloquants apparaissent en tête d'email et dans
le PDF — ils ne sont jamais masqués.

**Un seul JSON, trois rendus.** Le markdown, le HTML et le PDF dérivent du même
objet. Ils ne peuvent plus diverger.

---

## Comment tourne le brief

Trois étapes, dont deux sans aucun appel de modèle.

```
1. collecte    Python pur. Interroge BCE, Banque de France, FRED, sources de
               marché. Écrit travail/donnees.json, schema.json, instruction.md.

2. rédaction   claude-code-action lit instruction.md, la charte et les données,
               fait ses recherches sur le fiscal et le réglementaire, et écrit
               travail/brief.json.

3. finalise    Python pur. Contrôle, PDF, HTML, email, archive.
```

Ce découpage n'est pas cosmétique : il permet à l'étape 2 de tourner **sur ton
abonnement Claude** via `CLAUDE_CODE_OAUTH_TOKEN`, au lieu d'une clé API
facturée à l'usage.

---

## Deux façons de le faire tourner

| | Tâche planifiée Claude | GitHub Actions |
|---|---|---|
| Mise en place | 100 % navigateur | Une commande dans un terminal, une fois |
| Coût | 0 € | 0 € |
| Secrets | En clair dans le texte de la tâche | Dans les secrets GitHub, chiffrés |
| Régularité | Une session peut s'écarter du script | Étapes identiques chaque matin |
| Mode d'emploi | [`routine/PROMPT-ROUTINE.md`](routine/PROMPT-ROUTINE.md) | Ci-dessous |

Les deux exécutent exactement le même code : collecte déterministe, contrôles
mécaniques, PDF, email, archive. Seule change la façon de déclencher la
rédaction. Passer de l'une à l'autre ne demande aucune modification du projet.

---

## Mise en route — GitHub Actions

### 1. Générer le jeton d'abonnement

Sur ta machine, avec Claude Code installé :

```bash
claude setup-token
```

La commande rend un jeton OAuth, valable sur les offres Pro, Max, Team et
Enterprise. C'est lui qui fera tourner la rédaction sur ton abonnement.

### 2. Créer le dépôt et installer l'application GitHub

```bash
git init && git add . && git commit -m "Veille patrimoniale — socle"
gh repo create veille-patrimoniale --private --source=. --push
```

Puis installe l'[application GitHub de Claude](https://github.com/apps/claude)
sur ce dépôt.

### 3. Renseigner secrets et variables

`Settings → Secrets and variables → Actions`.

**Secrets** — `CLAUDE_CODE_OAUTH_TOKEN` (celui de l'étape 1), plus le secret
d'envoi selon le canal choisi : `RESEND_API_KEY`, ou `SMTP_UTILISATEUR` et
`SMTP_MOT_DE_PASSE`. Optionnels et gratuits : `WEBSTAT_API_KEY`, `FRED_API_KEY`.

**Variables** — `VEILLE_DESTINATAIRE` (ton email), `VEILLE_CANAL` (`resend` ou
`smtp`), `VEILLE_EXPEDITEUR`.

### 4. Vérifier quelles sources répondent

Onglet `Actions` → **Diagnostic des sources** → `Run workflow`.

Étape à ne pas sauter. Le diagnostic dit, série par série, ce qui répond
réellement. Les clés de séries n'ont pas pu être validées empiriquement à
l'écriture du code — l'environnement de développement était derrière une
allowlist réseau qui bloquait BCE, AFT, FRED et Stooq. Le diagnostic tranche, et
`veille/providers/bdf.py` se corrige avec le résultat.

### 5. Premier brief à blanc

`Actions` → **Veille patrimoniale** → `Run workflow`, en cochant « Produire le
brief sans expédier l'email ». Le dossier `travail/` est récupérable dans les
artefacts du run en cas d'échec.

Puis relancer sans cocher : le brief arrive dans la boîte mail.

---

## Coût

| Poste | Coût |
|---|---|
| GitHub Actions | Gratuit — 2 000 min/mois sur dépôt privé, le brief en consomme environ 100 |
| Rédaction (abonnement Claude) | Inclus dans l'abonnement, via `CLAUDE_CODE_OAUTH_TOKEN` |
| Resend | Gratuit jusqu'à 3 000 emails/mois — le brief en envoie 21 |
| SMTP Gmail (variante) | Gratuit |
| Webstat (Banque de France) | Gratuit |
| FRED (Fed de Saint-Louis) | Gratuit |

**Total : 0 € par mois.**

Le dépôt contient aussi `.github/workflows/veille-api.yml`, une variante qui
passe par l'API Anthropic (`ANTHROPIC_API_KEY`) et qui, elle, est facturée à
l'usage — de l'ordre de 15 à 25 € par mois. Elle est **désactivée par défaut**,
en déclenchement manuel uniquement. Elle n'a d'intérêt que sur un dépôt
d'organisation, où un jeton OAuth reste attaché à la personne qui l'a généré.
N'active jamais les deux workflows en quotidien : deux briefs partiraient chaque
matin.

---

## Utilisation locale

```bash
pip install -r requirements.txt
cp .env.example .env          # à compléter
set -a && source .env && set +a

python -m veille.doctor                              # quelles sources répondent
python -m veille.main collecte --dossier travail     # étape 1
#   … rédiger travail/brief.json …
python -m veille.main finalise --dossier travail --sans-envoi   # étape 3

python -m veille.main complet --sans-envoi           # tout en un, via l'API
python -m tests.test_chaine                          # contrôles et rendus
python -m tests.apercu_mise_en_page                  # maquette sans appel modèle
```

---

## Calendrier

Le workflow tourne du lundi au vendredi. Deux crons sont déclarés — 04:30 et
05:30 UTC — parce que GitHub Actions ignore le changement d'heure ; une garde en
début de job arrête l'exécution qui ne tombe pas sur 6 h à Paris. Sans elle, le
brief partirait deux fois par jour la moitié de l'année.

Les crons GitHub sont exécutés au mieux : un retard de 5 à 20 minutes est
courant aux heures de pointe. Le brief arrive donc entre 6 h 30 et 7 h.

Les échéances déductibles du calendrier civil (INSEE fin de mois et mi-mois,
France Assureurs vers le 30, épargne réglementée en janvier et août, séquence
PLF) sont calculées automatiquement. Les dates fixes — réunions BCE et FOMC,
revues de notation, adjudications AFT — se renseignent dans `calendrier.yml`,
une fois par an, depuis les calendriers publiés par les émetteurs.

---

## Archive

Chaque édition est écrite dans `archive/AAAA/AAAA-MM-JJ.{json,md,pdf}` et
committée par le workflow.

Elle sert deux fois. Elle constitue le corpus réutilisable en présentation
client — c'était l'usage n° 2 déclaré de la veille, et rien ne le capitalisait
jusqu'ici. Et elle alimente l'anti-répétition : `archive.py` relit les éditions
passées et interdit une citation déjà servie dans les 90 jours, un angle de bloc
6 repris dans les 15 jours, et plus de trois éditions consécutives au même
format.

---

## Points ouverts

- **La clé de série du TEC 10 quotidien** est à figer avec le diagnostic
  (étape 4). Tant qu'elle ne l'est pas, l'OAT 10 ans du bloc 3 sort en « non
  confirmé » ou en série mensuelle explicitement dégradée.
- **Les indices actions** reposent sur la règle des deux sources convergentes,
  faute d'API d'émetteur accessible. En cas de divergence au-delà de 0,15 %, le
  chiffre n'est pas publié et l'écart est nommé.
- **Le CME FedWatch** n'a pas d'API publique : les anticipations de taux Fed
  restent à traiter par la couche éditoriale, avec l'émetteur nommé et la
  mention que la probabilité bouge en séance.
- **La fréquence quotidienne** est à réévaluer après deux semaines. France
  Assureurs publie une fois par mois, la BCE huit fois par an, le BOFiP de façon
  irrégulière : plusieurs matins par semaine sortiront avec un bloc 4 vide et un
  bloc 3 à niveaux plats. Trois éditions par semaine attendues valent peut-être
  mieux que cinq survolées — la décision se prend sur les éditions réelles.
