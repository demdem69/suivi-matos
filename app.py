import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("INVENTAIRE_DB", str(ROOT / "data" / "inventaire.db"))

ETATS = ("en_stock", "sorti", "maintenance", "hors_service")

app = Flask(__name__)
app.secret_key = os.environ.get("INVENTAIRE_SECRET", "dev-local-change-me")


def assurer_schema():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        colonnes = [r[1] for r in conn.execute("PRAGMA table_info(mouvements)")]
        if "rendu_le" not in colonnes:
            conn.execute("ALTER TABLE mouvements ADD COLUMN rendu_le TEXT")
            conn.commit()


assurer_schema()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def categories(conn):
    return conn.execute(
        "SELECT id, nom, parent_id FROM categories ORDER BY nom"
    ).fetchall()


@app.route("/")
def index():
    with get_db() as conn:
        materiel = conn.execute(
            """
            SELECT m.id, m.nom, m.reference, m.numero_serie, m.quantite,
                   m.etat, m.emplacement, c.nom AS categorie
            FROM materiel m
            JOIN categories c ON c.id = m.categorie_id
            ORDER BY c.nom, m.nom
            """
        ).fetchall()
        total = conn.execute("SELECT COALESCE(SUM(quantite), 0) AS t FROM materiel").fetchone()["t"]
    return render_template("index.html", materiel=materiel, total=total)


@app.route("/materiel/ajouter", methods=["GET", "POST"])
def ajouter_materiel():
    with get_db() as conn:
        if request.method == "POST":
            erreurs = valider_materiel(conn, request.form)
            if erreurs:
                for e in erreurs:
                    flash(e, "erreur")
            else:
                conn.execute(
                    """
                    INSERT INTO materiel
                        (nom, reference, numero_serie, categorie_id,
                         quantite, etat, emplacement, remarque)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.form["nom"].strip(),
                        champ(request.form, "reference"),
                        champ(request.form, "numero_serie"),
                        int(request.form["categorie_id"]),
                        int(request.form["quantite"]),
                        request.form["etat"],
                        champ(request.form, "emplacement"),
                        champ(request.form, "remarque"),
                    ),
                )
                conn.commit()
                flash(f"Matériel « {request.form['nom'].strip()} » ajouté.", "succes")
                return redirect(url_for("index"))
        cats = categories(conn)
    return render_template(
        "ajouter.html", categories=cats, etats=ETATS, form=request.form
    )


@app.route("/categories/ajouter", methods=["POST"])
def ajouter_categorie():
    nom = request.form.get("nom", "").strip()
    if not nom:
        flash("Le nom de la catégorie est obligatoire.", "erreur")
    else:
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO categories (nom) VALUES (?)", (nom,))
                conn.commit()
                flash(f"Catégorie « {nom} » créée.", "succes")
            except sqlite3.IntegrityError:
                flash(f"La catégorie « {nom} » existe déjà.", "erreur")
    return redirect(url_for("ajouter_materiel"))


def champ(form, cle):
    valeur = form.get(cle, "").strip()
    return valeur or None


def valider_materiel(conn, form):
    erreurs = []
    if not form.get("nom", "").strip():
        erreurs.append("Le nom est obligatoire.")
    if not form.get("categorie_id"):
        erreurs.append("La catégorie est obligatoire.")
    else:
        existe = conn.execute(
            "SELECT 1 FROM categories WHERE id = ?", (form["categorie_id"],)
        ).fetchone()
        if not existe:
            erreurs.append("Catégorie inconnue.")
    try:
        quantite = int(form.get("quantite", ""))
        if quantite < 1:
            raise ValueError
    except ValueError:
        erreurs.append("La quantité doit être un nombre entier positif.")
    if form.get("etat") not in ETATS:
        erreurs.append("État invalide.")
    return erreurs


@app.route("/mouvements", methods=["GET"])
def mouvements():
    with get_db() as conn:
        en_cours = conn.execute(
            """
            SELECT mv.id, mv.quantite, mv.date_mouvement, mv.remarque,
                   m.nom AS materiel, u.nom AS utilisateur
            FROM mouvements mv
            JOIN materiel m ON m.id = mv.materiel_id
            JOIN utilisateurs u ON u.id = mv.utilisateur_id
            WHERE mv.type = 'sortie' AND mv.rendu_le IS NULL
            ORDER BY mv.date_mouvement DESC
            """
        ).fetchall()
        historique = conn.execute(
            """
            SELECT mv.id, mv.type, mv.quantite, mv.date_mouvement, mv.rendu_le,
                   mv.remarque, m.nom AS materiel, u.nom AS utilisateur
            FROM mouvements mv
            JOIN materiel m ON m.id = mv.materiel_id
            JOIN utilisateurs u ON u.id = mv.utilisateur_id
            ORDER BY mv.date_mouvement DESC, mv.id DESC
            LIMIT 30
            """
        ).fetchall()
        materiel_dispo = conn.execute(
            """
            SELECT m.id, m.nom, m.quantite,
                   m.quantite - COALESCE(SUM(sortie.quantite), 0) AS disponible
            FROM materiel m
            LEFT JOIN mouvements sortie
                   ON sortie.materiel_id = m.id
                  AND sortie.type = 'sortie'
                  AND sortie.rendu_le IS NULL
            WHERE m.etat IN ('en_stock', 'sorti')
            GROUP BY m.id
            ORDER BY m.nom
            """
        ).fetchall()
        utilisateurs = conn.execute(
            "SELECT id, nom FROM utilisateurs WHERE actif = 1 ORDER BY nom"
        ).fetchall()
    return render_template(
        "mouvements.html",
        en_cours=en_cours,
        historique=historique,
        materiel_dispo=materiel_dispo,
        utilisateurs=utilisateurs,
        maintenant=datetime.now().strftime("%Y-%m-%dT%H:%M"),
    )


@app.route("/mouvements/sortie", methods=["POST"])
def declarer_sortie():
    materiel_id = request.form.get("materiel_id", "")
    utilisateur_id = request.form.get("utilisateur_id", "")
    date_saisie = request.form.get("date_mouvement", "").strip()
    remarque = champ(request.form, "remarque")

    with get_db() as conn:
        erreurs = valider_mouvement(conn, materiel_id, utilisateur_id)
        try:
            quantite = int(request.form.get("quantite", ""))
            if quantite < 1:
                raise ValueError
        except ValueError:
            erreurs.append("La quantité doit être un nombre entier positif.")
            quantite = None

        disponible = None
        if materiel_id.isdigit():
            ligne = conn.execute(
                """
                SELECT m.quantite - COALESCE(SUM(s.quantite), 0) AS dispo
                FROM materiel m
                LEFT JOIN mouvements s ON s.materiel_id = m.id
                       AND s.type = 'sortie' AND s.rendu_le IS NULL
                WHERE m.id = ?
                GROUP BY m.id
                """,
                (materiel_id,),
            ).fetchone()
            disponible = ligne["dispo"] if ligne else 0

        if quantite is not None and disponible is not None and quantite > disponible:
            erreurs.append(f"Quantité indisponible : {disponible} unité(s) en stock.")

        if erreurs:
            for e in erreurs:
                flash(e, "erreur")
        else:
            conn.execute(
                """
                INSERT INTO mouvements
                    (materiel_id, utilisateur_id, type, quantite,
                     date_mouvement, remarque)
                VALUES (?, ?, 'sortie', ?, ?, ?)
                """,
                (int(materiel_id), int(utilisateur_id), quantite,
                 normaliser_date(date_saisie), remarque),
            )
            conn.execute(
                "UPDATE materiel SET etat = 'sorti', maj_le = datetime('now') "
                "WHERE id = ? AND ? >= quantite",
                (int(materiel_id), quantite),
            )
            conn.commit()
            flash("Sortie enregistrée.", "succes")
    return redirect(url_for("mouvements"))


@app.route("/mouvements/entree", methods=["POST"])
def declarer_entree():
    mouvement_id = request.form.get("mouvement_id", "")
    materiel_id = request.form.get("materiel_id", "")
    utilisateur_id = request.form.get("utilisateur_id", "")
    date_saisie = request.form.get("date_mouvement", "").strip()
    remarque = champ(request.form, "remarque")

    with get_db() as conn:
        if mouvement_id:
            sortie = conn.execute(
                """
                SELECT id, materiel_id FROM mouvements
                WHERE id = ? AND type = 'sortie' AND rendu_le IS NULL
                """,
                (mouvement_id,),
            ).fetchone()
            if not sortie:
                flash("Sortie introuvable ou déjà restituée.", "erreur")
                return redirect(url_for("mouvements"))
            conn.execute(
                "UPDATE mouvements SET rendu_le = datetime('now') WHERE id = ?",
                (sortie["id"],),
            )
            conn.execute(
                "UPDATE materiel SET etat = 'en_stock', maj_le = datetime('now') "
                "WHERE id = ?",
                (sortie["materiel_id"],),
            )
            conn.commit()
            flash("Restitution enregistrée.", "succes")
            return redirect(url_for("mouvements"))

        erreurs = valider_mouvement(conn, materiel_id, utilisateur_id)
        try:
            quantite = int(request.form.get("quantite", ""))
            if quantite < 1:
                raise ValueError
        except ValueError:
            erreurs.append("La quantité doit être un nombre entier positif.")
        if erreurs:
            for e in erreurs:
                flash(e, "erreur")
        else:
            conn.execute(
                """
                INSERT INTO mouvements
                    (materiel_id, utilisateur_id, type, quantite,
                     date_mouvement, remarque)
                VALUES (?, ?, 'entree', ?, ?, ?)
                """,
                (int(materiel_id), int(utilisateur_id), quantite,
                 normaliser_date(date_saisie), remarque),
            )
            conn.execute(
                "UPDATE materiel SET etat = 'en_stock', maj_le = datetime('now') "
                "WHERE id = ? AND etat = 'sorti'",
                (int(materiel_id),),
            )
            conn.commit()
            flash("Entrée enregistrée.", "succes")
    return redirect(url_for("mouvements"))


def valider_mouvement(conn, materiel_id, utilisateur_id):
    erreurs = []
    if not materiel_id or not conn.execute(
        "SELECT 1 FROM materiel WHERE id = ?", (materiel_id,)
    ).fetchone():
        erreurs.append("Matériel inconnu.")
    if not utilisateur_id or not conn.execute(
        "SELECT 1 FROM utilisateurs WHERE id = ? AND actif = 1", (utilisateur_id,)
    ).fetchone():
        erreurs.append("Utilisateur inconnu ou inactif.")
    return erreurs


def normaliser_date(valeur):
    if not valeur:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    valeur = valeur.replace("T", " ")
    if len(valeur) == 16:
        valeur += ":00"
    return valeur


if __name__ == "__main__":
    app.run(
        host=os.environ.get("INVENTAIRE_HOST", "127.0.0.1"),
        port=int(os.environ.get("INVENTAIRE_PORT", "5000")),
        debug=os.environ.get("INVENTAIRE_DEBUG") == "1",
    )
