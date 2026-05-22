#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPANY PROFILE GENERATOR — Web Interface (Flask)
Serveur local : python app.py → http://localhost:8080

Place ce fichier dans le MÊME dossier que :
  - company_profile_generator.py
  - clustering.py
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file

from company_profile_generator import CompanyProfileGenerator, find_project_folder, open_file
from clustering import cluster_fields, split_fields

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── État global ──
generator  = None
field_map  = {}

# ── Fichier de sauvegarde des corrections manuelles ──
MANUAL_MERGES_FILE = Path("field_merges.json")


# ══════════════════════════════════════════════
#  CORRECTIONS MANUELLES
# ══════════════════════════════════════════════

def load_manual_merges():
    """Charge les fusions manuelles depuis le fichier JSON."""
    if MANUAL_MERGES_FILE.exists():
        with open(MANUAL_MERGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manual_merges(merges):
    """Sauvegarde les fusions manuelles."""
    with open(MANUAL_MERGES_FILE, "w", encoding="utf-8") as f:
        json.dump(merges, f, ensure_ascii=False, indent=2)


def apply_all_mappings(raw_field):
    """
    Pipeline complet de normalisation d'un field brut :
      1. Split sur / ; ,
      2. Clustering sémantique automatique  (field_map, calculé au démarrage)
      3. Corrections manuelles admin        (priorité absolue)
    """
    fields = split_fields(raw_field)
    manual = load_manual_merges()
    result = []
    for f in fields:
        mapped = field_map.get(f.strip().title(), f.strip().title())
        mapped = manual.get(mapped, mapped)
        result.append(mapped)
    return list(set(result))


# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════

def normalize_location(loc_str):
    if not loc_str or str(loc_str).lower() in ("nan", "none", ""):
        return ""
    import re
    loc = str(loc_str).strip()
    loc = re.sub(r"\s*\(.*?\)", "", loc).strip()
    loc = re.sub(r"\s+", " ", loc)
    return loc.title()


# ══════════════════════════════════════════════
#  INITIALISATION
# ══════════════════════════════════════════════

def init_generator():
    global generator, field_map

    project_folder = find_project_folder()
    if not project_folder:
        print("❌ Impossible de trouver le dossier Projet")
        sys.exit(1)

    generator = CompanyProfileGenerator(project_folder)

    df = generator.db["DataBase"]

    # Collecter tous les fields bruts
    all_raw = []
    for val in df["Field"].dropna().tolist():
        all_raw.extend(split_fields(val))

    # ── Clustering sémantique ──
    # eps : 0.20 = strict | 0.30 = équilibre | 0.45 = large
    # Ajuste eps ici selon ce que tu vois dans le terminal au démarrage.
    field_map = cluster_fields(all_raw, df=df, eps=0.30)

    # Afficher l'effet des corrections manuelles existantes
    manual = load_manual_merges()
    if manual:
        print(f"  🔧 {len(manual)} corrections manuelles chargées (priorité sur clustering)")

    print(
        f"✅ Générateur initialisé — "
        f"{len(set(field_map.values()))} domaines clustering "
        f"+ {len(manual)} corrections manuelles"
    )


# ══════════════════════════════════════════════
#  ROUTES PRINCIPALES
# ══════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/companies")
def get_companies():
    """Retourne la liste de toutes les compagnies avec leurs métadonnées."""
    try:
        df = generator.db["DataBase"]
        companies = []
        for _, row in df.iterrows():
            raw_field    = str(row.get("Field", ""))
            raw_location = str(row.get("Locations", ""))
            companies.append({
                "name":                str(row.get("Company Name", "")),
                "country":             str(row.get("Country", "")),
                "field":               raw_field,
                "fields_list":         apply_all_mappings(raw_field),
                "activity":            str(row.get("Activity", "")),
                "locations":           raw_location,
                "location_normalized": normalize_location(raw_location),
                "founded":             str(row.get("Founded", "")),
                "employees":           str(row.get("N° employees", "")),
                "confidence":          str(row.get("Confidence Index", "")),
                "data_quality":        str(row.get("Data Quality", "")),
            })
        return jsonify({"companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/countries")
def get_countries():
    try:
        df = generator.db["DataBase"]
        countries = sorted(df["Country"].dropna().unique().tolist())
        return jsonify({"countries": countries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fields")
def get_fields():
    """Retourne les domaines après clustering sémantique + corrections manuelles."""
    try:
        df     = generator.db["DataBase"]
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
    """Génère la fiche PPTX pour une compagnie."""
    try:
        data         = request.json
        company_name = data.get("company_name", "")
        country      = data.get("country", None)

        if not company_name:
            return jsonify({"error": "Nom de compagnie requis"}), 400

        result = generator.generate_profile(company_name, country)

        if result:
            open_file(result)
            return jsonify({
                "success": True,
                "message": f"Fiche générée : {Path(result).name}",
                "path":    result,
            })
        else:
            return jsonify({"error": f"Compagnie '{company_name}' non trouvée"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_country", methods=["POST"])
def generate_country():
    """Génère un seul PPTX avec toutes les fiches d'un pays."""
    try:
        data    = request.json
        country = data.get("country", "")

        if not country:
            return jsonify({"error": "Pays requis"}), 400

        df        = generator.db["DataBase"]
        mask      = df["Country"].str.lower() == country.lower()
        companies = df[mask]["Company Name"].tolist()

        if not companies:
            return jsonify({"error": f"Aucune compagnie pour '{country}'"}), 404

        import zipfile, shutil, tempfile
        from lxml import etree

        generated  = []
        errors     = []
        temp_files = []

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
                "success":   True,
                "message":   "1 fiche générée",
                "generated": generated,
                "errors":    errors,
            })

        temp_dir = tempfile.mkdtemp()
        base_dir = os.path.join(temp_dir, "base")

        with zipfile.ZipFile(temp_files[0], "r") as z:
            z.extractall(base_dir)

        pres_path = os.path.join(base_dir, "ppt", "presentation.xml")
        rels_path = os.path.join(base_dir, "ppt", "_rels", "presentation.xml.rels")
        ct_path   = os.path.join(base_dir, "[Content_Types].xml")

        pres_tree = etree.parse(pres_path)
        rels_tree = etree.parse(rels_path)
        ct_tree   = etree.parse(ct_path)

        pres_root = pres_tree.getroot()
        rels_root = rels_tree.getroot()
        ct_root   = ct_tree.getroot()

        ns_p           = "http://schemas.openxmlformats.org/presentationml/2006/main"
        ns_r           = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        ns_ct          = "http://schemas.openxmlformats.org/package/2006/content-types"
        rel_type_slide = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
        ct_slide       = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

        sldIdLst      = pres_root.find(f".//{{{ns_p}}}sldIdLst")
        media_counter = 100

        for idx, pptx_path in enumerate(temp_files[1:], start=2):
            src_dir = os.path.join(temp_dir, f"src_{idx}")
            with zipfile.ZipFile(pptx_path, "r") as z:
                z.extractall(src_dir)

            src_slide_path = os.path.join(src_dir, "ppt", "slides", "slide1.xml")
            src_rels_path  = os.path.join(src_dir, "ppt", "slides", "_rels", "slide1.xml.rels")

            dst_slide_name = f"slide{idx}.xml"
            dst_slide_path = os.path.join(base_dir, "ppt", "slides", dst_slide_name)
            dst_rels_dir   = os.path.join(base_dir, "ppt", "slides", "_rels")
            dst_rels_path  = os.path.join(dst_rels_dir, f"slide{idx}.xml.rels")

            shutil.copy2(src_slide_path, dst_slide_path)

            if os.path.exists(src_rels_path):
                src_rels_tree = etree.parse(src_rels_path)
                src_rels_root = src_rels_tree.getroot()

                for rel in src_rels_root.findall("*"):
                    target = rel.get("Target", "")
                    if "../media/" in target:
                        old_media_name = os.path.basename(target)
                        ext            = os.path.splitext(old_media_name)[1]
                        media_counter += 1
                        new_media_name = f"image_s{idx}_{media_counter}{ext}"

                        src_media     = os.path.join(src_dir, "ppt", "media", old_media_name)
                        dst_media_dir = os.path.join(base_dir, "ppt", "media")
                        os.makedirs(dst_media_dir, exist_ok=True)
                        dst_media = os.path.join(dst_media_dir, new_media_name)

                        if os.path.exists(src_media):
                            shutil.copy2(src_media, dst_media)
                        rel.set("Target", f"../media/{new_media_name}")

                os.makedirs(dst_rels_dir, exist_ok=True)
                src_rels_tree.write(dst_rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)

            src_notes_path = os.path.join(src_dir, "ppt", "notesSlides", "notesSlide1.xml")
            if os.path.exists(src_notes_path):
                dst_notes_dir  = os.path.join(base_dir, "ppt", "notesSlides")
                os.makedirs(dst_notes_dir, exist_ok=True)
                dst_notes_name = f"notesSlide{idx}.xml"
                dst_notes_path = os.path.join(dst_notes_dir, dst_notes_name)
                shutil.copy2(src_notes_path, dst_notes_path)

                src_notes_rels = os.path.join(src_dir, "ppt", "notesSlides", "_rels", "notesSlide1.xml.rels")
                if os.path.exists(src_notes_rels):
                    dst_notes_rels_dir = os.path.join(dst_notes_dir, "_rels")
                    os.makedirs(dst_notes_rels_dir, exist_ok=True)
                    dst_notes_rels = os.path.join(dst_notes_rels_dir, f"notesSlide{idx}.xml.rels")

                    notes_rels_tree = etree.parse(src_notes_rels)
                    for rel in notes_rels_tree.getroot().findall("*"):
                        if "../slides/slide1.xml" in rel.get("Target", ""):
                            rel.set("Target", f"../slides/slide{idx}.xml")
                    notes_rels_tree.write(dst_notes_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

                slide_rels_tree = etree.parse(dst_rels_path)
                notes_rel = etree.SubElement(slide_rels_tree.getroot(), "Relationship")
                notes_rel.set("Id",     f"rIdNotes{idx}")
                notes_rel.set("Type",   "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide")
                notes_rel.set("Target", f"../notesSlides/{dst_notes_name}")
                slide_rels_tree.write(dst_rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)

                note_override = etree.SubElement(ct_root, f"{{{ns_ct}}}Override")
                note_override.set("PartName",    f"/ppt/notesSlides/{dst_notes_name}")
                note_override.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml")

            rId     = f"rId{200 + idx}"
            new_rel = etree.SubElement(rels_root, "Relationship")
            new_rel.set("Id",     rId)
            new_rel.set("Type",   rel_type_slide)
            new_rel.set("Target", f"slides/{dst_slide_name}")

            new_sldId = etree.SubElement(sldIdLst, f"{{{ns_p}}}sldId")
            new_sldId.set("id",            str(1000 + idx))
            new_sldId.set(f"{{{ns_r}}}id", rId)

            new_override = etree.SubElement(ct_root, f"{{{ns_ct}}}Override")
            new_override.set("PartName",    f"/ppt/slides/{dst_slide_name}")
            new_override.set("ContentType", ct_slide)

        pres_tree.write(pres_path, xml_declaration=True, encoding="UTF-8", standalone=True)
        rels_tree.write(rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)
        ct_tree.write(ct_path,     xml_declaration=True, encoding="UTF-8", standalone=True)

        output_filename = f"{country}_companies.pptx"
        output_path     = str(generator.output_folder / output_filename)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for walk_root, dirs, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(walk_root, file)
                    arcname   = os.path.relpath(file_path, base_dir)
                    zout.write(file_path, arcname)

        shutil.rmtree(temp_dir, ignore_errors=True)
        open_file(output_path)

        return jsonify({
            "success":   True,
            "message":   f"{len(generated)} fiches dans {output_filename}",
            "generated": generated,
            "errors":    errors,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<company_name>")
def download_profile(company_name):
    try:
        filename = f"{company_name.replace(' ', '_')}.pptx"
        filepath = generator.output_folder / filename
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True)
        return jsonify({"error": "Fichier non trouvé. Générez d'abord la fiche."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════
#  ROUTES ADMIN — CORRECTIONS MANUELLES
# ══════════════════════════════════════════════

@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/api/field_clusters")
def get_field_clusters():
    """
    Retourne tous les fields avec leur mapping actuel :
      - résultat du clustering sémantique automatique
      - correction manuelle éventuelle appliquée par-dessus
    Utilisé par la page admin pour visualiser et corriger les clusters.
    """
    try:
        df     = generator.db["DataBase"]
        manual = load_manual_merges()

        all_raw = []
        for val in df["Field"].dropna().tolist():
            all_raw.extend(split_fields(val))

        from collections import Counter
        counts = Counter([f.strip().title() for f in all_raw])

        fields_info = []
        seen        = set()
        for f, count in counts.most_common():
            auto_mapped  = field_map.get(f, f)
            final_mapped = manual.get(auto_mapped, auto_mapped)
            if f not in seen:
                fields_info.append({
                    "original":               f,
                    "auto_cluster":           auto_mapped,   # résultat clustering sémantique
                    "manual_cluster":         final_mapped,  # après correction manuelle
                    "count":                  count,
                    "is_manually_overridden": auto_mapped in manual,
                })
                seen.add(f)

        all_canonical = sorted(set(
            manual.get(field_map.get(f, f), field_map.get(f, f))
            for f in seen
        ))

        return jsonify({
            "fields":           fields_info,
            "canonical_names":  all_canonical,
            "auto_clusters":    len(set(field_map.values())),
            "manual_overrides": len(manual),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/merge_fields", methods=["POST"])
def merge_fields():
    """
    Fusionne plusieurs fields sous un même nom canonique (correction manuelle).
    Ces corrections ont la priorité absolue sur le clustering automatique.
    """
    try:
        data            = request.json
        fields_to_merge = data.get("fields", [])
        canonical_name  = data.get("canonical_name", "")

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
    """
    Supprime la correction manuelle d'un field.
    Le field revient au résultat du clustering sémantique automatique.
    """
    try:
        data       = request.json
        field_name = data.get("field", "")

        manual = load_manual_merges()
        if field_name in manual:
            del manual[field_name]
            save_manual_merges(manual)
            return jsonify({
                "success": True,
                "message": f"Correction supprimée pour '{field_name}' — clustering automatique restauré",
            })

        return jsonify({"success": True, "message": "Aucune correction manuelle à supprimer"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clustering_info")
def clustering_info():
    """Infos sur l'état du clustering — utile pour debug et monitoring."""
    try:
        manual = load_manual_merges()
        return jsonify({
            "method":           "sentence-transformers + DBSCAN",
            "model":            "all-MiniLM-L6-v2",
            "eps":              0.30,
            "auto_clusters":    len(set(field_map.values())),
            "manual_overrides": len(manual),
            "total_canonical":  len(set(
                manual.get(v, v) for v in field_map.values()
            )),
        })
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
