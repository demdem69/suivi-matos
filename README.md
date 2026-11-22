# Suivi du matériel — base du projet

Outil de suivi du matériel entreposé dans un local : catalogue par catégories,
sorties et entrées de matériel par utilisateur, accessible depuis internet.

## Base de données

La base est organisée autour de 4 tables (voir `db/schema.sql`) :

| Table | Rôle |
|---|---|
| `categories` | Catégories de matériel, arborescence possible via `parent_id` |
| `materiel` | Matériel recensé : nom, référence, n° de série, catégorie, quantité, état, emplacement |
| `utilisateurs` | Personnes habilitées, avec rôle (`admin`, `gestionnaire`, `utilisateur`) |
| `mouvements` | Historique des entrées/sorties : matériel, utilisateur, type, quantité, dates |

L'état du matériel (`en_stock`, `sorti`, `maintenance`, `hors_service`) est mis à
jour à chaque mouvement ; `mouvements` conserve l'historique complet. Une sortie
reste « en cours » (`rendu_le` NULL) jusqu'à sa restitution.

## Initialisation

Prérequis : Python 3 (aucune dépendance externe).

```bash
# base vide
python3 scripts/init_db.py

# base avec données d'exemple
python3 scripts/init_db.py --seed

# autre emplacement
python3 scripts/init_db.py -f /chemin/vers/base.db --seed
```

La base est créée dans `data/inventaire.db` par défaut (SQLite, fichier unique).
Le schéma est en SQL standard : une migration vers PostgreSQL ou MySQL ne demande
que d'adapter les `AUTOINCREMENT` et les valeurs par défaut `datetime('now')`.

## Interface web

Une interface Flask permet de consulter l'inventaire et d'ajouter du matériel.

```bash
pip install -r requirements.txt
python3 app.py
```

Puis ouvrir http://127.0.0.1:5000 :

- `/` : inventaire complet (matériel, catégories, états, quantités)
- `/materiel/ajouter` : formulaire d'ajout de matériel (validation côté serveur)
- `/mouvements` : déclaration des sorties (qui, quand, quantité, commentaire) et
  des entrées ; les emprunts en cours restent listés jusqu'à leur restitution
  (bouton « Restituer »)
- création d'une nouvelle catégorie depuis la page d'ajout

Variables d'environnement : `INVENTAIRE_DB` (chemin de la base,
`data/inventaire.db` par défaut), `INVENTAIRE_SECRET` (clé de session — à
définir en production).

## Déploiement sur Raspberry Pi

### Installation

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/demdem69/suivi-matos.git
cd suivi-matos
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/init_db.py --seed
```

### Service systemd

Le service sert l'application en production via gunicorn sur
`127.0.0.1:8000` (voir `deploy/suivi-matos.service`) :

```bash
sudo cp deploy/suivi-matos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now suivi-matos
systemctl status suivi-matos
```

Adapter `User=` et `WorkingDirectory=` si le dépôt n'est pas dans
`/home/pi/suivi-matos`, et définir `INVENTAIRE_SECRET` avec une vraie clé
(`python3 -c "import secrets; print(secrets.token_hex(32))"`).

En développement local seulement :

```bash
python3 app.py                     # 127.0.0.1:5000
INVENTAIRE_HOST=0.0.0.0 python3 app.py   # accessible depuis le réseau local
```

Variables : `INVENTAIRE_HOST`, `INVENTAIRE_PORT`, `INVENTAIRE_DEBUG`,
`INVENTAIRE_DB`, `INVENTAIRE_SECRET`.

### Accès depuis internet

Trois options détaillées dans `deploy/ACCES-INTERNET.md` :

1. **Cloudflare Tunnel** (recommandé) : aucun port ouvert sur la box, HTTPS
   automatique, néanmoins le site reste public sans authentification.
2. **Tailscale** : réseau privé, seuls vos appareils y accèdent.
3. **Ouverture de ports + nginx** (`deploy/nginx-suivi-matos.conf`) : à éviter
   tant que l'authentification n'est pas en place.

## Interroger la base

```bash
python3 -c "import sqlite3; [print(*r, sep=' | ') for r in sqlite3.connect('data/inventaire.db').execute('SELECT m.nom, c.nom FROM materiel m JOIN categories c ON c.id = m.categorie_id')]"
```

## Étapes suivantes envisagées

- API (lecture/écriture du catalogue et des mouvements)
- Interface web d'inventaire et d'emprunt
- Authentification des utilisateurs
- Hébergement accessible depuis internet (bureau, local, etc.)
