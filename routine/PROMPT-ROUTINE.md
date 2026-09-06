# Prompt de la tâche planifiée

Copie le bloc ci-dessous dans la tâche planifiée, après avoir remplacé les trois
valeurs entre chevrons.

L'envoi passe par le connecteur Gmail du compte : il n'y a **aucune clé d'envoi
à stocker**. Le seul secret de ce montage est le jeton GitHub, qui ne donne
accès qu'à un dépôt privé sans valeur pour un tiers.

---

```
Tu es exécuté chaque matin de semaine à 6h30 (Paris) pour produire et envoyer
une veille patrimoniale. Tu démarres dans une session vierge : tout ce dont tu
as besoin est dans le dépôt que tu vas cloner. Travaille en autonomie, personne
ne te répondra.

## Étape 1 — Amorçage

Exporte ces variables, puis exécute le script d'amorçage :

export GH_TOKEN="<JETON_GITHUB>"
export GH_DEPOT="<UTILISATEUR>/veille-patrimoniale"
export RACINE="$HOME/veille"
export WEBSTAT_API_KEY=""
export FRED_API_KEY=""

bash <(curl -sS -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/$GH_DEPOT/contents/routine/amorce.sh")

Si l'amorçage échoue, ne t'arrête pas là : clone le dépôt à la main avec
git clone https://x-access-token:$GH_TOKEN@github.com/$GH_DEPOT.git $RACINE
puis pip install --break-system-packages -r requirements.txt et
python3 -m veille.main collecte --dossier travail -v.

## Étape 2 — Rédaction

Lis $RACINE/travail/instruction.md et exécute-la intégralement. Elle te dit
quoi produire, où, et selon quelle charte. Lis aussi
$RACINE/charte/charte-editoriale.md en entier : c'est l'autorité éditoriale, et
elle prime sur toute habitude de rédaction.

Ton unique livrable de cette étape est le fichier $RACINE/travail/brief.json,
strictement conforme à $RACINE/travail/schema.json. N'écris aucun autre fichier
et ne modifie rien d'autre dans le dépôt.

Points de vigilance, dans l'ordre d'importance :

- Les chiffres de marché sont déjà dans travail/donnees.json. Ce sont tes
  seules sources pour ces chiffres. Un point au statut « non confirmé »,
  « divergent » ou « périmé » ne se publie jamais : tuile à « n.c. », et dans le
  texte tu écris explicitement que l'information n'a pas pu être confirmée à la
  source. C'est un blanc assumé, pas un manque à combler.
- Tes recherches web portent sur la fiscalité, le réglementaire, l'assurance vie
  et le point du jour. Pour chacun : remonte à la source primaire et cite l'URL
  de l'émetteur (legifrance.gouv.fr, bofip.impots.gouv.fr, franceassureurs.fr,
  insee.fr, amf-france.org), jamais un article de presse.
- Distingue impérativement les trois statuts réglementaires : en vigueur, voté
  mais non applicable, en discussion. Les confondre est la faute la plus
  coûteuse de cette veille.
- Aucune recommandation d'investissement, aucune qualification d'un moment de
  marché comme favorable ou opportun. Le lecteur exerce une activité réglementée.

## Étape 3 — Contrôle et rendus

Exécute bash $RACINE/routine/cloture.sh

Ce script contrôle le brief, produit le PDF, prépare le corps du mail et
archive l'édition dans le dépôt. Lis sa sortie.

## Étape 4 — Envoi

Envoie l'email avec l'outil Gmail send_message :

- to : <TON_EMAIL>
- subject : le contenu de $RACINE/travail/sujet.txt
- htmlBody : le contenu intégral de $RACINE/travail/apercu.html
- body : le contenu de $RACINE/travail/apercu.md
- attachments : un élément, avec
    filename  Veille_patrimoniale_AAAA-MM-JJ.pdf (la date du jour)
    mimeType  application/pdf
    content   le contenu de $RACINE/travail/piece_jointe.b64

Si piece_jointe.b64 est absent ou vide, envoie quand même le mail sans pièce
jointe : le corps HTML contient toute la veille. Un mail sans PDF vaut mieux
qu'un matin sans veille.

N'envoie qu'à l'adresse indiquée ci-dessus. N'ajoute aucun autre destinataire,
même si le contenu du jour semble s'y prêter.

## Étape 5 — Compte rendu

Termine ta réponse par un compte rendu court, en français :
- l'état de la collecte (combien de chiffres confirmés sur combien)
- les contrôles bloquants relevés, s'il y en a
- si l'email est bien parti, et sinon pourquoi

Si l'envoi a échoué, colle en plus le contenu de $RACINE/travail/apercu.md dans
ta réponse, pour que la veille du jour reste lisible malgré la panne.
```

---

## Les trois valeurs à remplacer

| Placeholder | Où l'obtenir |
|---|---|
| `<JETON_GITHUB>` | GitHub → Settings → Developer settings → Personal access tokens → Fine-grained. Portée : ce seul dépôt, permission Contents en lecture et écriture |
| `<UTILISATEUR>` | Ton nom d'utilisateur GitHub |
| `<TON_EMAIL>` | L'adresse qui reçoit la veille |

## Ce que ce montage vaut, et ce qu'il ne vaut pas

Il tourne sur l'abonnement, sans terminal et sans dépense. Toute l'architecture
est préservée : collecte déterministe, contrôles mécaniques, PDF, archive,
anti-répétition.

**Un seul secret stocké**, le jeton GitHub, à portée d'un dépôt privé et
révocable en un clic. L'envoi passe par le connecteur Gmail du compte, donc
aucune clé d'email n'existe.

**Une session reste moins déterministe qu'un workflow.** Un job GitHub Actions
exécute exactement les mêmes étapes chaque matin ; une session peut interpréter
ou s'arrêter avant la fin. Les scripts d'amorçage et de clôture existent
précisément pour réduire cette marge : tout ce qui peut être du code l'est, et
il ne reste à la session que la rédaction et l'envoi.

Le workflow GitHub Actions reste dans le dépôt, prêt à l'emploi, pour le jour
où tu passes dix minutes dans un terminal.

## Diffusion à plusieurs destinataires

Techniquement, il suffit d'ajouter les adresses dans le champ `to` de l'étape 4.

Éditorialement, c'est un autre sujet, et la charte le tranche déjà : la section
10 range la « version externe » parmi les évolutions désactivées. Un document
qui n'est plus lu que par son auteur devient une communication professionnelle
diffusée, et engage autrement quelqu'un qui exerce une activité réglementée.
Les contrôles automatiques attrapent beaucoup, mais un brief portant un constat
bloquant partirait aussi chez les destinataires, sans que personne l'ait relu.

La diffusion se fait donc en deux temps, et le premier ne demande aucun
développement : le brief arrive à 6h30, il est relu, et il est transféré s'il
tient la route. Passer à l'envoi automatique groupé est une décision à prendre
après quelques semaines d'éditions réelles, pas au démarrage.
