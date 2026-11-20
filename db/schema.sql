-- Base de données de suivi du matériel entreposé
-- Schéma compatible SQLite / PostgreSQL (types standards)

PRAGMA foreign_keys = ON;

-- Catégories de matériel (arborescence possible via parent_id)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL UNIQUE,
    description TEXT,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    cree_le     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Utilisateurs habilités à emprunter / rendre du matériel
CREATE TABLE IF NOT EXISTS utilisateurs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    email     TEXT UNIQUE,
    role      TEXT NOT NULL DEFAULT 'utilisateur'
              CHECK (role IN ('admin', 'gestionnaire', 'utilisateur')),
    actif     INTEGER NOT NULL DEFAULT 1,
    cree_le   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Matériel recensé dans le local
CREATE TABLE IF NOT EXISTS materiel (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nom            TEXT    NOT NULL,
    reference      TEXT,
    numero_serie   TEXT UNIQUE,
    categorie_id   INTEGER NOT NULL REFERENCES categories(id),
    quantite       INTEGER NOT NULL DEFAULT 1 CHECK (quantite > 0),
    etat           TEXT    NOT NULL DEFAULT 'en_stock'
                   CHECK (etat IN ('en_stock', 'sorti', 'maintenance', 'hors_service')),
    emplacement    TEXT,
    remarque       TEXT,
    cree_le        TEXT    NOT NULL DEFAULT (datetime('now')),
    maj_le         TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Historique des entrées / sorties de matériel
-- Une sortie reste « en cours » (rendu_le NULL) jusqu'à sa restitution.
CREATE TABLE IF NOT EXISTS mouvements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    materiel_id    INTEGER NOT NULL REFERENCES materiel(id),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    type           TEXT    NOT NULL CHECK (type IN ('entree', 'sortie')),
    quantite       INTEGER NOT NULL CHECK (quantite > 0),
    date_mouvement TEXT    NOT NULL DEFAULT (datetime('now')),
    date_retour_prevue TEXT,
    rendu_le       TEXT,
    remarque       TEXT
);

CREATE INDEX IF NOT EXISTS idx_materiel_categorie ON materiel(categorie_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_materiel ON mouvements(materiel_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_utilisateur ON mouvements(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_date ON mouvements(date_mouvement);
