-- Données d'exemple pour démarrer
INSERT INTO categories (nom, description) VALUES
    ('Outillage', 'Outils à main et électroportatifs'),
    ('Électronique', 'Multimètres, oscilloscopes, soudures'),
    ('Consommables', 'Visserie, câbles, colliers'),
    ('Sécurité', 'EPI : gants, lunettes, casques');

INSERT INTO utilisateurs (nom, email, role) VALUES
    ('Admin', 'admin@exemple.fr', 'admin'),
    ('Alice Martin', 'alice@exemple.fr', 'gestionnaire'),
    ('Bob Dubois', 'bob@exemple.fr', 'utilisateur');

INSERT INTO materiel (nom, reference, numero_serie, categorie_id, quantite, emplacement) VALUES
    ('Perceuse visseuse', 'PERC-001', 'SN-0001', 1, 1, 'Étagère A1'),
    ('Multimètre', 'MULTI-001', 'SN-0002', 2, 2, 'Étagère B2'),
    ('Boîte de vis M6', 'VIS-M6-050', NULL, 3, 50, 'Casier C3'),
    ('Paire de gants', 'EPI-GANT-L', NULL, 4, 10, 'Casier D1');
