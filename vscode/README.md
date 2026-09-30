# kenboard — extension VS Code (preuve de concept, ken #1127)

Affiche les tâches kenboard du projet courant dans la barre latérale.

- Liste des tâches todo / doing / review ; clic = ouvrir la tâche dans le navigateur.
- Clic droit sur une tâche → **Move to…** (changement de statut).
- Boutons de la vue : rafraîchir, ouvrir le board.

Aucune configuration : l'extension lit `ken.ini` et `.ken` (même chaîne que
le CLI `ken` : `KEN_*` > `.ken` > `ken.ini`, recherche vers le haut depuis le
workspace) et parle à l'API REST `/api/v1` avec le token Bearer. Le site web
n'est pas encapsulé (CSP `frame-ancestors 'none'`, cookies `SameSite=Lax`,
contrôle CSRF sur `Origin`).

## Build / install

```sh
pdm run vscode-lint       # biome (config racine)
pdm run vscode-typecheck  # tsc strict, @types/vscode aligné sur engines.vscode
pdm run vscode-test       # node --test, zéro dépendance
pdm run vscode-package    # → vscode/kenboard-vscode-<version>.vsix
code --install-extension vscode/kenboard-vscode-0.0.1.vsix
```

Les trois premiers tournent dans `sh publish.sh --quality`. Le rendu du
détail reprend la vue plein écran du site : `marked` et `DOMPurify` sont
copiés depuis `src/dashboard/static/` à chaque package (`media/vendor/`,
non versionné).
