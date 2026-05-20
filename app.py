#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPANY PROFILE GENERATOR — Web Interface (Flask)
Serveur local : python app.py → http://localhost:8080

Place ce fichier dans le MÊME dossier que company_profile_generator.py
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file

# ── Importer ton générateur existant ──
from company_profile_generator import CompanyProfileGenerator, find_project_folder, open_file

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Initialisation du générateur au démarrage ──
generator = None
field_map = {}

def split_fields(field_str):
    """Sépare les domaines par / ; , et nettoie"""
    if not field_str or str(field_str).lower() in ("nan", "none", ""):
        return []
    import re
    parts = re.split(r'[/;,]', str(field_str))
    return [p.strip() for p in parts if p.strip()]


def cluster_fields(all_raw_fields, n_clusters=None, max_distance=0.6):
    """
    Clustering sémantique des domaines d'activité.
    Utilise TF-IDF (mots + bigrammes) + Agglomerative Clustering.

    - Regroupe "Missile systems", "Missiles", "Guided missiles" ensemble
    - Le nom canonique = le plus fréquent du cluster
    """
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_distances
    import numpy as np

    # Nettoyer et compter
    cleaned = [f.strip() for f in all_raw_fields if f.strip()]
    counts = Counter([f.lower() for f in cleaned])

    # Liste unique (en minuscules pour comparaison)
    unique_lower = list(set(counts.keys()))

    if len(unique_lower) <= 1:
        return {f.strip().title(): unique_lower[0].title() if unique_lower else f.strip().title()
                for f in cleaned}

    # TF-IDF avec mots et bigrammes de caractères pour capturer les variantes
    vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(2, 4),
        lowercase=True,
    )
    tfidf_matrix = vectorizer.fit_transform(unique_lower)

    # Aussi un TF-IDF au niveau mots pour le sens
    word_vectorizer = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        lowercase=True,
        stop_words=['and', 'the', 'of', 'for', 'in', 'de', 'et', 'des', 'les', 'du'],
    )
    word_matrix = word_vectorizer.fit_transform(unique_lower)

    # Combiner les deux matrices (caractères + mots)
    from scipy.sparse import hstack
    combined_matrix = hstack([tfidf_matrix, word_matrix * 2.0])  # Poids double pour les mots

    # Distance cosinus
    dist_matrix = cosine_distances(combined_matrix)

    # Clustering agglomératif avec seuil de distance
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=max_distance,
        metric='precomputed',
        linkage='average',
    )
    labels = clustering.fit_predict(dist_matrix)

    # Pour chaque cluster, le nom canonique = le plus fréquent, en Title Case
    cluster_groups = {}
    for idx, label in enumerate(labels):
        if label not in cluster_groups:
            cluster_groups[label] = []
        cluster_groups[label].append(unique_lower[idx])

    canonical_map = {}
    for label, members in cluster_groups.items():
        # Le plus fréquent du cluster devient le canonique
        canon = max(members, key=lambda m: counts[m])
        canon_title = canon.strip().title()
        for member in members:
            canonical_map[member] = canon_title

    # Mapper tous les fields bruts vers leur canonique
    result_map = {}
    for f in cleaned:
        key = f.strip().title()
        result_map[key] = canonical_map.get(f.lower().strip(), key)

    print(f"  📊 Clustering: {len(unique_lower)} domaines bruts → {len(set(canonical_map.values()))} clusters")
    for label, members in cluster_groups.items():
        if len(members) > 1:
            canon = max(members, key=lambda m: counts[m]).title()
            print(f"     → {canon}: {[m.title() for m in members]}")

    return result_map

# ── Fichier de sauvegarde des corrections manuelles ──
MANUAL_MERGES_FILE = Path("field_merges.json")

def load_manual_merges():
    """Charge les fusions manuelles depuis le fichier JSON"""
    if MANUAL_MERGES_FILE.exists():
        with open(MANUAL_MERGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_manual_merges(merges):
    """Sauvegarde les fusions manuelles"""
    with open(MANUAL_MERGES_FILE, "w", encoding="utf-8") as f:
        json.dump(merges, f, ensure_ascii=False, indent=2)

def apply_all_mappings(raw_field):
    """Applique clustering auto + corrections manuelles"""
    fields = split_fields(raw_field)
    manual = load_manual_merges()
    result = []
    for f in fields:
        mapped = field_map.get(f.strip().title(), f.strip().title())
        # Appliquer le mapping manuel par-dessus
        mapped = manual.get(mapped, mapped)
        result.append(mapped)
    return list(set(result))


@app.route("/admin")
def admin_page():
    """Page d'administration des clusters de fields"""
    return render_template("admin.html")


@app.route("/api/field_clusters")
def get_field_clusters():
    """Retourne tous les fields avec leur mapping actuel"""
    try:
        df = generator.db["DataBase"]
        manual = load_manual_merges()

        # Tous les fields bruts splittés
        all_raw = []
        for val in df["Field"].dropna().tolist():
            all_raw.extend(split_fields(val))

        # Compter les occurrences
        from collections import Counter
        counts = Counter([f.strip().title() for f in all_raw])

        # Construire la liste avec mapping
        fields_info = []
        seen = set()
        for f, count in counts.most_common():
            auto_mapped = field_map.get(f, f)
            final_mapped = manual.get(auto_mapped, auto_mapped)
            if f not in seen:
                fields_info.append({
                    "original": f,
                    "auto_cluster": auto_mapped,
                    "manual_cluster": final_mapped,
                    "count": count,
                })
                seen.add(f)

        # Liste des noms canoniques uniques pour le dropdown
        all_canonical = sorted(set(
            manual.get(field_map.get(f, f), field_map.get(f, f))
            for f in seen
        ))

        return jsonify({
            "fields": fields_info,
            "canonical_names": all_canonical,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/merge_fields", methods=["POST"])
def merge_fields():
    """Fusionne plusieurs fields sous un même nom canonique"""
    try:
        data = request.json
        fields_to_merge = data.get("fields", [])
        canonical_name = data.get("canonical_name", "")

        if not fields_to_merge or not canonical_name:
            return jsonify({"error": "Champs requis"}), 400

        manual = load_manual_merges()
        for f in fields_to_merge:
            manual[f] = canonical_name
        save_manual_merges(manual)

        return jsonify({
            "success": True,
            "message": f"{len(fields_to_merge)} domaines fusionnés sous '{canonical_name}'",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/unmerge_field", methods=["POST"])
def unmerge_field():
    """Annule la fusion d'un field"""
    try:
        data = request.json
        field_name = data.get("field", "")

        manual = load_manual_merges()
        if field_name in manual:
            del manual[field_name]
            save_manual_merges(manual)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def normalize_location(loc_str):
    if not loc_str or str(loc_str).lower() in ("nan", "none", ""):
        return ""
    import re
    loc = str(loc_str).strip()
    loc = re.sub(r'\s*\(.*?\)', '', loc).strip()
    loc = re.sub(r'\s+', ' ', loc)
    loc = loc.title()
    return loc

def init_generator():
    global generator, field_map
    project_folder = find_project_folder()
    if project_folder:
        generator = CompanyProfileGenerator(project_folder)
        # Construire le mapping de clustering des fields
        df = generator.db["DataBase"]
        all_raw = []
        for val in df["Field"].dropna().tolist():
            all_raw.extend(split_fields(val))
        field_map = cluster_fields(all_raw)
        print(f"✅ Générateur initialisé — {len(set(field_map.values()))} domaines uniques détectés")
    else:
        print("❌ Impossible de trouver le dossier Projet")
        sys.exit(1)


# ══════════════════════════════════════════════
#  ROUTES API
# ══════════════════════════════════════════════

@app.route("/")
def index():
    """Page principale"""
    return render_template("index.html")

@app.route("/api/companies")
def get_companies():
    """Retourne la liste de toutes les compagnies avec leurs métadonnées"""
    try:
        df = generator.db["DataBase"]
        companies = []
        for _, row in df.iterrows():
            raw_field = str(row.get("Field", ""))
            raw_location = str(row.get("Locations", ""))
            companies.append({
                "name": str(row.get("Company Name", "")),
                "country": str(row.get("Country", "")),
                "field": raw_field,
                "fields_list": apply_all_mappings(raw_field),
                "activity": str(row.get("Activity", "")),
                "locations": raw_location,
                "location_normalized": normalize_location(raw_location),
                "founded": str(row.get("Founded", "")),
                "employees": str(row.get("N° employees", "")),
                "confidence": str(row.get("Confidence Index", "")),
    })

        return jsonify({"companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/countries")
def get_countries():
    """Retourne la liste unique des pays"""
    try:
        df = generator.db["DataBase"]
        countries = sorted(df["Country"].dropna().unique().tolist())
        return jsonify({"countries": countries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fields")
def get_fields():
    try:
        df = generator.db["DataBase"]
        manual = load_manual_merges()
        all_fields = set()
        for val in df["Field"].dropna().tolist():
            for f in split_fields(val):
                mapped = field_map.get(f.strip().title(), f.strip().title())
                mapped = manual.get(mapped, mapped)
                all_fields.add(mapped)
        return jsonify({"fields": sorted(all_fields)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/api/locations")
def get_locations():
    try:
        df = generator.db["DataBase"]
        all_locations = set()
        for val in df["Locations"].dropna().tolist():
            normalized = normalize_location(val)
            if normalized:
                all_locations.add(normalized)
        return jsonify({"locations": sorted(all_locations)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_profile():
    """Génère la fiche PPTX pour une compagnie"""
    try:
        data = request.json
        company_name = data.get("company_name", "")
        country = data.get("country", None)

        if not company_name:
            return jsonify({"error": "Nom de compagnie requis"}), 400

        result = generator.generate_profile(company_name, country)

        if result:
            # Ouvrir automatiquement le fichier
            open_file(result)
            return jsonify({
                "success": True,
                "message": f"Fiche générée : {Path(result).name}",
                "path": result,
            })
        else:
            return jsonify({"error": f"Compagnie '{company_name}' non trouvée"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate_country", methods=["POST"])
def generate_country():
    """Génère un seul PPTX avec toutes les fiches d'un pays"""
    try:
        data = request.json
        country = data.get("country", "")

        if not country:
            return jsonify({"error": "Pays requis"}), 400

        df = generator.db["DataBase"]
        mask = df["Country"].str.lower() == country.lower()
        companies = df[mask]["Company Name"].tolist()

        if not companies:
            return jsonify({"error": f"Aucune compagnie pour '{country}'"}), 404

        import zipfile
        import shutil
        import tempfile
        from lxml import etree

        generated = []
        errors = []
        temp_files = []

        # Étape 1 : Générer chaque fiche individuellement
        for name in companies:
            try:
                result = generator.generate_profile(name, country)
                if result:
                    generated.append(name)
                    temp_files.append(result)
                else:
                    errors.append(name)
            except Exception as e:
                errors.append(f"{name}: {e}")

        if not temp_files:
            return jsonify({"error": "Aucune fiche générée"}), 500

        if len(temp_files) == 1:
            open_file(temp_files[0])
            return jsonify({
                "success": True,
                "message": f"1 fiche générée",
                "generated": generated,
                "errors": errors,
            })

        # Étape 2 : Fusionner au niveau ZIP
        temp_dir = tempfile.mkdtemp()
        base_dir = os.path.join(temp_dir, "base")

        # Extraire le premier PPTX
        with zipfile.ZipFile(temp_files[0], 'r') as z:
            z.extractall(base_dir)

        # Parser les XML de base
        pres_path = os.path.join(base_dir, "ppt", "presentation.xml")
        rels_path = os.path.join(base_dir, "ppt", "_rels", "presentation.xml.rels")
        ct_path = os.path.join(base_dir, "[Content_Types].xml")

        pres_tree = etree.parse(pres_path)
        rels_tree = etree.parse(rels_path)
        ct_tree = etree.parse(ct_path)

        pres_root = pres_tree.getroot()
        rels_root = rels_tree.getroot()
        ct_root = ct_tree.getroot()

        ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"
        ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        ns_ct = "http://schemas.openxmlformats.org/package/2006/content-types"
        rel_type_slide = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
        ct_slide = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

        sldIdLst = pres_root.find(f'.//{{{ns_p}}}sldIdLst')

        # Compteur global pour les médias uniques
        media_counter = 100

        for idx, pptx_path in enumerate(temp_files[1:], start=2):
            src_dir = os.path.join(temp_dir, f"src_{idx}")
            with zipfile.ZipFile(pptx_path, 'r') as z:
                z.extractall(src_dir)

            src_slide_path = os.path.join(src_dir, "ppt", "slides", "slide1.xml")
            src_rels_path = os.path.join(src_dir, "ppt", "slides", "_rels", "slide1.xml.rels")

            dst_slide_name = f"slide{idx}.xml"
            dst_slide_path = os.path.join(base_dir, "ppt", "slides", dst_slide_name)
            dst_rels_dir = os.path.join(base_dir, "ppt", "slides", "_rels")
            dst_rels_path = os.path.join(dst_rels_dir, f"slide{idx}.xml.rels")

            # Copier la slide
            shutil.copy2(src_slide_path, dst_slide_path)

            # Copier et réécrire les relations de la slide (renommer les images)
            if os.path.exists(src_rels_path):
                src_rels_tree = etree.parse(src_rels_path)
                src_rels_root = src_rels_tree.getroot()

                for rel in src_rels_root.findall("*"):
                    target = rel.get("Target", "")
                    if "../media/" in target:
                        # Renommer l'image pour éviter les conflits
                        old_media_name = os.path.basename(target)
                        ext = os.path.splitext(old_media_name)[1]
                        media_counter += 1
                        new_media_name = f"image_s{idx}_{media_counter}{ext}"

                        # Copier le fichier media avec le nouveau nom
                        src_media = os.path.join(src_dir, "ppt", "media", old_media_name)
                        dst_media_dir = os.path.join(base_dir, "ppt", "media")
                        os.makedirs(dst_media_dir, exist_ok=True)
                        dst_media = os.path.join(dst_media_dir, new_media_name)

                        if os.path.exists(src_media):
                            shutil.copy2(src_media, dst_media)

                        # Mettre à jour la cible dans le .rels
                        rel.set("Target", f"../media/{new_media_name}")

                    elif "../slideLayouts/" in target:
                        # Garder la référence au slideLayout existant dans la base
                        pass

                os.makedirs(dst_rels_dir, exist_ok=True)
                src_rels_tree.write(dst_rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)

            # Copier les notes si présentes
            src_notes_path = os.path.join(src_dir, "ppt", "notesSlides", "notesSlide1.xml")
            if os.path.exists(src_notes_path):
                dst_notes_dir = os.path.join(base_dir, "ppt", "notesSlides")
                os.makedirs(dst_notes_dir, exist_ok=True)
                dst_notes_name = f"notesSlide{idx}.xml"
                dst_notes_path = os.path.join(dst_notes_dir, dst_notes_name)
                shutil.copy2(src_notes_path, dst_notes_path)

                # Rels pour les notes
                src_notes_rels = os.path.join(src_dir, "ppt", "notesSlides", "_rels", "notesSlide1.xml.rels")
                if os.path.exists(src_notes_rels):
                    dst_notes_rels_dir = os.path.join(dst_notes_dir, "_rels")
                    os.makedirs(dst_notes_rels_dir, exist_ok=True)
                    dst_notes_rels = os.path.join(dst_notes_rels_dir, f"notesSlide{idx}.xml.rels")

                    # Lire et corriger les références dans le rels des notes
                    notes_rels_tree = etree.parse(src_notes_rels)
                    for rel in notes_rels_tree.getroot().findall("*"):
                        target = rel.get("Target", "")
                        if "../slides/slide1.xml" in target:
                            rel.set("Target", f"../slides/slide{idx}.xml")
                    notes_rels_tree.write(dst_notes_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

                # Ajouter relation notes dans le rels de la slide
                slide_rels_tree = etree.parse(dst_rels_path)
                slide_rels_root = slide_rels_tree.getroot()
                notes_rel = etree.SubElement(slide_rels_root, "Relationship")
                notes_rel.set("Id", f"rIdNotes{idx}")
                notes_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide")
                notes_rel.set("Target", f"../notesSlides/{dst_notes_name}")
                slide_rels_tree.write(dst_rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)

                # Content type pour les notes
                note_override = etree.SubElement(ct_root, f'{{{ns_ct}}}Override')
                note_override.set("PartName", f"/ppt/notesSlides/{dst_notes_name}")
                note_override.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml")

            # Ajouter relation dans presentation.xml.rels
            rId = f"rId{200 + idx}"
            new_rel = etree.SubElement(rels_root, "Relationship")
            new_rel.set("Id", rId)
            new_rel.set("Type", rel_type_slide)
            new_rel.set("Target", f"slides/{dst_slide_name}")

            # Ajouter dans sldIdLst
            new_sldId = etree.SubElement(sldIdLst, f'{{{ns_p}}}sldId')
            new_sldId.set("id", str(1000 + idx))
            new_sldId.set(f'{{{ns_r}}}id', rId)

            # Content type pour la slide
            new_override = etree.SubElement(ct_root, f'{{{ns_ct}}}Override')
            new_override.set("PartName", f"/ppt/slides/{dst_slide_name}")
            new_override.set("ContentType", ct_slide)

        # Sauvegarder les XML modifiés
        pres_tree.write(pres_path, xml_declaration=True, encoding="UTF-8", standalone=True)
        rels_tree.write(rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)
        ct_tree.write(ct_path, xml_declaration=True, encoding="UTF-8", standalone=True)

        # Repackager en PPTX
        output_filename = f"{country}_companies.pptx"
        output_path = str(generator.output_folder / output_filename)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for walk_root, dirs, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(walk_root, file)
                    arcname = os.path.relpath(file_path, base_dir)
                    zout.write(file_path, arcname)

        # Nettoyer
        shutil.rmtree(temp_dir, ignore_errors=True)

        open_file(output_path)

        return jsonify({
            "success": True,
            "message": f"{len(generated)} fiches dans {output_filename}",
            "generated": generated,
            "errors": errors,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500




@app.route("/api/download/<company_name>")
def download_profile(company_name):
    """Télécharge le PPTX généré"""
    try:
        filename = f"{company_name.replace(' ', '_')}.pptx"
        filepath = generator.output_folder / filename
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True)
        else:
            return jsonify({"error": "Fichier non trouvé. Générez d'abord la fiche."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════

if __name__ == "__main__":
    init_generator()
    print("\n" + "=" * 60)
    print("🌐 Interface web disponible sur : http://localhost:8080")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=8080, debug=True)
