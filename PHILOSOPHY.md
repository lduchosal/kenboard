# PHILOSOPHY.md

> Distillé d'une conversation entre Luc et Claude, le 2026-06-10 — la journée
> où le gate qualité (ken #788) a été construit et où les cinq paliers ont été
> franchis. Ce document explique *pourquoi* kenboard est développé comme il
> l'est. Le *comment* vit dans [doc/code-quality.md](doc/code-quality.md) et
> [doc/architecture.md](doc/architecture.md).

## 1. La qualité est gratuite

Kenboard est développé à 100 % en agentique. Cela renverse l'économie
classique du logiciel : payer la dette technique ne coûte plus des semaines
d'équipe, mais des heures d'agent. Les arguments habituels pour tolérer la
médiocrité — « on n'a pas le temps », « ça bloquerait la release », « on
nettoiera plus tard » — perdent leur fondement.

Conséquence : les cibles de qualité sont exigeantes et **bloquantes**. Un
gate rouge n'est pas un obstacle, c'est le signal qui force à payer. Si
l'agent a codé de la dette, l'agent la résorbe.

La première version du gate avait été calibrée avec le réflexe inverse — « ne
pas bloquer les humains », seuils posés sur l'état courant. Luc l'a refusée
en une phrase :

> « Avec le dev agentique, on a de la qualité gratuite et tu me mets des
> bâtons dans les roues pour garder une qualité médiocre. »

Il avait raison. C'est la décision fondatrice de ce document.

## 2. Un gate vert n'est jamais un état stable

La qualité ne se décrète pas en un jour ; elle se conquiert **par paliers
bloquants**. Chaque palier est un chantier fini : le gate liste les
contrevenants, les agents paient, le gate passe au vert — et le vert est le
signal de resserrage, jamais un état de repos.

Trois verrous empêchent tout retour en arrière :

1. **Les familles ruff** : chaque famille de règles tombée à zéro est activée
   dans le lint — l'acquis devient une erreur de compilation, pas une bonne
   intention.
2. **Les cibles absolues** : taille des fichiers, longueur des fonctions,
   complexité, dette, couverture — bloquantes dans `publish.sh`.
3. **Le ratchet best-ever** : aucun compteur ne peut redevenir pire que son
   meilleur niveau historique enregistré. Le ratchet se resserre tout seul, à
   chaque snapshot committé.

Règle d'or : on ne **détend jamais** un seuil sans décision humaine
explicite, tracée. Les agents peuvent tout faire, sauf baisser la barre.

## 3. La mémoire de l'artisan est externalisée

Le bon programmeur de Larry Wall repasse sur son code, le polit, le reconnaît
des semaines plus tard — sa fierté est une mémoire incarnée. Un agent n'a pas
cette continuité : chaque session repart de presque rien.

Kenboard compense en externalisant tout ce qui compte : le board ken et ses
blocs *Résolution* (l'audit trail de chaque tâche), `doc/quality-history.csv`
(une ligne par snapshot, committée), la doc des paliers, le wiki. Quand un
agent rouvre le projet, il retrouve l'équivalent fonctionnel du regard de
l'artisan : la trace de l'intention, vérifiable, et la suite évidente.

C'est aussi pour cela que la description d'une tâche est mise à jour *avant*
le passage en review : le commit dit ce qui a changé, la carte dit pourquoi
et comment c'est garanti.

## 4. Les vertus de Larry Wall, version agentique

Les trois vertus du programmeur se traduisent — étrangement bien :

- **La paresse** : automatiser le gate pour que plus personne n'ait jamais à
  se souvenir de vérifier. `pdm run check` et `publish.sh` portent la
  vigilance à la place des développeurs.
- **L'impatience** : cinq paliers en une journée, parce qu'attendre n'avait
  pas de sens quand la dette se paie en heures.
- **L'hubris** : « écrire du code dont personne ne voudra dire du mal » est
  littéralement la définition du palier final — fichier ≤ 300 lignes,
  fonction ≤ 50, complexité ≤ 10, dette zéro.

L'hubris n'est plus une vertu individuelle du programmeur : elle est
committée dans `publish.sh`. Être fier de son code est devenu une propriété
du système.

## 5. L'agent amplifie la discipline qui existe déjà

Le matin du 2026-06-10, SonarCloud mesurait, rien ne bloquait, et la qualité
dérivait — *avec* des agents qui codaient. Le soir, les mêmes agents avaient
ramené la dette de 267 findings à 9 et le plus gros fichier de 2 266 à 386
lignes. La variable n'était pas l'agent : c'était le harnais.

Ce qui a rendu la journée possible : des critères vérifiables, des tests qui
font foi, un pipeline qui bloque, un board qui trace — et des arbitrages
humains aux moments qui comptaient (le régime strict, les paliers documentés,
la séparation des rôles entre agents). Sans gates, la vitesse d'un agent
produit de la dérive plus vite. Avec, elle produit de l'excellence plus vite.

L'équipage complet, c'est : un humain qui a du goût et qui tranche, des
agents qui paient la dette sans fatigue ni ego, des gates qui ne dorment
jamais.

## 6. Mesurable ≠ bon

Les métriques ne voient pas tout. Un nom juste, une abstraction cohérente, un
module qui *chante* — `funcs_over_50 = 0` n'en garantit aucun. Le risque d'un
agent fier est d'être fier de ce qui se mesure.

C'est pourquoi le polissage humain garde sa place : la colonne `done` du
board appartient à Luc, et à lui seul. Les agents s'arrêtent à `review`.

## 7. Des règles dures plutôt que des couches

L'architecture suit la même philosophie : peu de règles, mais inviolables,
plutôt que des couches d'indirection en assurance contre un futur incertain.

- **Pas d'ORM** : les fichiers `queries/*.sql` sont le contrat.
- **Pydantic aux frontières**, jamais comme générateur de SQL.
- **Les transversales en middleware Flask** (auth, perf, erreurs,
  historisation) — formalisées par l'usage, pas par un framework.
- **Des modules par feature** plutôt qu'une couche service horizontale : la
  logique sort des routes sous la pression des paliers, par découpage
  vertical. CQRS et clean architecture attendront le jour — improbable — où
  ce kanban aura des projections de lecture divergentes.
- **Le frontend est plafonné** : un bundler, un test runner, un linter.

Les couches sont des assurances qui coûtent tous les jours et remboursent
peut-être. Ici, le filet est ailleurs : mypy strict, la couverture, le gate,
les règles structurelles. À l'échelle de kenboard, c'est le bon trade-off.

## La journée qui a tout établi (2026-06-10)

| Critère | Matin (v0.1.132) | Soir (v0.1.138) |
|---|---:|---:|
| Dette ruff | 267 | 9 → 0 (palier 5) |
| Plus gros fichier | 2 266 lignes | 386 |
| Plus longue fonction | 126 lignes | 60 |
| Complexité > 10 | 3 | 0 |
| Couverture | 89.3 % | 92.7 % |
| Pire fichier couvert | 30 % | 71 % |
| Releases publiées | — | 5, toutes gates verts |

Cinq paliers, cinq cartes ken (#789, #798, #803, #805, #807), chaque acquis
verrouillé à triple niveau. La dérive observée sur SonarCloud ne peut
structurellement plus se reproduire — ni vers le bas, ni silencieusement.
