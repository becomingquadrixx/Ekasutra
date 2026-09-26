import os
import re
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
from rapidfuzz import fuzz

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None

MATCH_THRESHOLDS = {
    'exact': 0.90,
    'functional_equivalent': 0.70,
    'similar_substitute': 0.50
}

@app.on_event("startup")
def startup_event():
    global model
    print("Loading embedding model BAAI/bge-large-en-v1.5 (this may take a moment)...")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    print("Model loaded successfully.")

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "ekasutra_db"),
        user=os.environ.get("DB_USER", "ekasutra_user"),
        password=os.environ.get("DB_PASSWORD", "ekasutra_password")
    )
    # Register pgvector type so Python lists are automatically cast to VECTOR
    register_vector(conn)
    return conn

def normalize_description(raw_desc: str, lexicon: list) -> str:
    """
    Replaces raw terms with canonical terms based on the lexicon.
    Expects lexicon to be sorted by length descending to match longest phrases first.
    """
    desc = raw_desc
    for raw_term, canonical_term in lexicon:
        # Use word boundaries safely: if the raw term ends with a non-word
        # character (like '.' in 'M.S.'), a trailing \b would fail, so use a
        # lookahead for whitespace/word-end instead.
        escaped = re.escape(raw_term)
        if raw_term and not raw_term[-1].isalnum():
            pattern = r'\b' + escaped + r'(?=\s|$|[^\w])'
        else:
            pattern = r'\b' + escaped + r'\b'
        desc = re.sub(pattern, canonical_term, desc, flags=re.IGNORECASE)
    return desc

def classify_category(desc: str) -> str:
    """
    Keyword-based category classifier.
    """
    desc_lower = desc.lower()
    if any(kw in desc_lower for kw in ["pipe", "tube"]):
        return "Pipes"
    elif any(kw in desc_lower for kw in ["bolt", "nut", "screw", "fastener"]):
        return "Fasteners"
    elif any(kw in desc_lower for kw in ["cable", "wire", "conductor", "xlpe", "mm2", "kv", "volt", "1100v", "650v"]):
        return "Electrical_Cable"
    return "Unknown"

def parse_dimension(val_str: str) -> float:
    if not val_str: return None
    val_str = str(val_str).lower().strip()
    match = re.search(r'([\d\.]+)', val_str)
    if not match: return None
    num = float(match.group(1))
    if 'in' in val_str or 'inch' in val_str or '"' in val_str:
        num *= 25.4
    return num


def _parse_voltage(val_str: str) -> float:
    """Normalize voltage to Volts."""
    if not val_str: return None
    val_str = str(val_str).lower().strip()
    match = re.search(r'([\d\.]+)', val_str)
    if not match: return None
    num = float(match.group(1))
    if 'kv' in val_str:
        num *= 1000
    return num


def _parse_pressure(val_str: str) -> float:
    """Normalize pressure to psi."""
    if not val_str: return None
    val_str = str(val_str).lower().strip()
    match = re.search(r'([\d\.]+)', val_str)
    if not match: return None
    num = float(match.group(1))
    if 'bar' in val_str:
        num *= 14.5038
    return num


def _parse_thread_size_pitch(val_str: str) -> tuple[float, float]:
    """Extract bolt size (mm) and pitch (mm) from strings like 'M12 1.75mm' or 'M12x1.75'."""
    if not val_str: return None, None
    val_str = str(val_str).lower().strip()
    nums = re.findall(r'[\d\.]+', val_str)
    if len(nums) < 1: return None, None
    # First number is the nominal diameter, second (if present) is pitch
    size = float(nums[0])
    pitch = float(nums[1]) if len(nums) >= 2 else None
    return size, pitch


def _normalize_spec_string(val: str) -> str:
    """Lowercase, remove spaces/dashes/slashes for fuzzy comparison."""
    val = str(val).lower().strip()
    val = re.sub(r'[\s\-_/]+', '', val)
    return val


def _compare_spec_values(spec_name: str, val_a, val_b) -> tuple[bool, str, str]:
    """
    Compare two spec values. Returns (match, formatted_a, formatted_b).
    Critical specs get numeric/unit-aware parsing; everything else uses RapidFuzz.
    """
    fa, fb = str(val_a).strip(), str(val_b).strip()

    if spec_name in ['diameter', 'length']:
        num_a, num_b = parse_dimension(val_a), parse_dimension(val_b)
        if num_a is not None and num_b is not None:
            match = abs(num_a - num_b) < 1.0
            return match, f"{num_a}mm", f"{num_b}mm"

    if spec_name == 'voltage_rating':
        v_a, v_b = _parse_voltage(val_a), _parse_voltage(val_b)
        if v_a is not None and v_b is not None:
            match = abs(v_a - v_b) < 10.0  # allow small rounding
            return match, f"{v_a:.0f}V", f"{v_b:.0f}V"

    if spec_name == 'pressure_rating':
        p_a, p_b = _parse_pressure(val_a), _parse_pressure(val_b)
        if p_a is not None and p_b is not None:
            # 1% relative tolerance; avoids treating 10bar (~145psi) and 150psi as equal
            match = abs(p_a - p_b) < max(1.0, 0.01 * max(p_a, p_b))
            return match, f"{p_a:.1f}psi", f"{p_b:.1f}psi"

    if spec_name == 'thread_size_pitch':
        s_a, p_a = _parse_thread_size_pitch(val_a)
        s_b, p_b = _parse_thread_size_pitch(val_b)
        if s_a is not None and s_b is not None:
            size_match = abs(s_a - s_b) < 0.5
            pitch_match = (p_a is None or p_b is None or abs(p_a - p_b) < 0.05)
            return size_match and pitch_match, fa, fb

    norm_a = _normalize_spec_string(val_a)
    norm_b = _normalize_spec_string(val_b)
    ratio = fuzz.ratio(norm_a, norm_b)
    match = ratio >= 90
    return match, fa, fb


def _compare_specs_internal(specs_a: dict, specs_b: dict, cat_specs: list) -> dict:
    specs_a = specs_a or {}
    specs_b = specs_b or {}
    result = {
        "critical_pass": True,
        "critical_missing": False,
        "spec_agreement": {},
        "override_triggered": False,
        "override_reason": None
    }
    for spec_name, spec_type in cat_specs:
        # Irrelevant specs are ignored entirely per the spec
        if spec_type == 'irrelevant':
            continue

        key = f"spec_{spec_name}"
        val_a = specs_a.get(key) or specs_a.get(spec_name)
        val_b = specs_b.get(key) or specs_b.get(spec_name)
        if val_a is None or val_b is None or str(val_a).strip() == '' or str(val_b).strip() == '':
            result["spec_agreement"][spec_name] = "missing_data"
            if spec_type == 'critical':
                result["critical_missing"] = True
            continue
        match, formatted_a, formatted_b = _compare_spec_values(spec_name, val_a, val_b)

        result["spec_agreement"][spec_name] = "agree" if match else "disagree"
        if spec_type == 'critical' and not match:
            result["critical_pass"] = False
            result["override_triggered"] = True
            result["override_reason"] = f"{spec_name} mismatch: {formatted_a} vs {formatted_b}"
            break
    return result

def decide_match(semantic_score: float, spec_result: dict) -> str:
    if spec_result.get("override_triggered", False):
        return "rejected"
    has_soft_disagree = any(v == "disagree" for v in spec_result.get("spec_agreement", {}).values())
    critical_missing = spec_result.get("critical_missing", False)
    # Missing critical specs are unknown — never inferred as exact identity.
    if semantic_score >= MATCH_THRESHOLDS['exact']:
        if critical_missing or has_soft_disagree:
            return "functional_equivalent" if has_soft_disagree and not critical_missing else "similar_substitute"
        return "exact"
    elif semantic_score >= MATCH_THRESHOLDS['functional_equivalent']:
        return "similar_substitute" if critical_missing else "functional_equivalent"
    elif semantic_score >= MATCH_THRESHOLDS['similar_substitute']:
        return "similar_substitute"
    return "rejected"

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/materials/{material_id}")
def get_material(material_id: int):
    """Return a raw CPSE record (never mutated after ingest)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, cpse_name, original_code, raw_description, raw_specs,
                   normalized_description, category, ingested_at
            FROM cpse_materials WHERE id = %s
            """,
            (material_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Material not found")
        return {
            "id": row[0],
            "cpse_name": row[1],
            "original_code": row[2],
            "raw_description": row[3],
            "raw_specs": row[4],
            "normalized_description": row[5],
            "category": row[6],
            "ingested_at": row[7],
            "immutable": True,
        }
    finally:
        cursor.close()
        conn.close()

def _validate_scope(scope: str) -> str:
    scope = (scope or "all").lower().strip()
    if scope not in ("all", "cross", "intra"):
        raise HTTPException(status_code=400, detail="scope must be one of: all, cross, intra")
    return scope


@app.post("/ingest")
async def ingest_csv(
    file: UploadFile = File(...),
    scope: str = Query("all", description="Comparison pool: all | cross | intra"),
):
    scope = _validate_scope(scope)
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    try:
        df = pd.read_csv(file.file, on_bad_lines='skip')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")
    
    required_cols = {'cpse_name', 'original_code', 'description'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch active lexicon entries, order by length descending to match longest terms first
        cursor.execute("SELECT raw_term, canonical_term FROM lexicon_entries WHERE status = 'active' ORDER BY length(raw_term) DESC")
        lexicon = cursor.fetchall()
        
        inserted_count = 0
        skipped_count = 0
        new_material_ids = []
        normalization_sample = []
        for _, row in df.iterrows():
            cpse_name = str(row['cpse_name'])
            original_code = str(row['original_code'])
            raw_description = str(row['description'])

            cursor.execute(
                "SELECT id FROM cpse_materials WHERE cpse_name = %s AND original_code = %s",
                (cpse_name, original_code)
            )
            existing_row = cursor.fetchone()
            if existing_row:
                skipped_count += 1
                continue

            # Extract spec columns into a dictionary
            specs = {}
            for col in df.columns:
                if col.startswith("spec_") and pd.notna(row[col]):
                    specs[col] = str(row[col])

            # If specs are missing, try extracting from the raw description
            if not specs.get("spec_voltage_rating"):
                volt_match = re.search(r'(\d+(\.\d+)?[kK][vV]|\d+(\.\d+)?[vV])', raw_description)
                if volt_match:
                    specs["spec_voltage_rating"] = volt_match.group(1)
            
            if not specs.get("spec_conductor_size"):
                cond_match = re.search(r'(\d+(\.\d+)?[mM][mM]2)', raw_description)
                if cond_match:
                    specs["spec_conductor_size"] = cond_match.group(1)

            # Run normalization and classification
            normalized_desc = normalize_description(raw_description, lexicon)
            category = classify_category(normalized_desc)

            if len(normalization_sample) < 5 and normalized_desc != raw_description:
                normalization_sample.append({
                    "raw": raw_description,
                    "normalized": normalized_desc
                })

            # Generate embedding (list of floats)
            embedding_list = model.encode(normalized_desc).tolist()

            # Insert into cpse_materials and capture the new id
            cursor.execute("""
                INSERT INTO cpse_materials
                (cpse_name, original_code, raw_description, raw_specs, normalized_description, category, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (cpse_name, original_code, raw_description, Json(specs), normalized_desc, category, embedding_list))

            new_material_ids.append(cursor.fetchone())
            inserted_count += 1

        conn.commit()

        # Step 4: auto-trigger candidate matching for every newly inserted material.
        # We re-use the existing endpoint logic; duplicate-match prevention keeps
        # incremental ingests safe.
        new_ids = [r[0] for r in new_material_ids]
        matches_created = 0
        for mid in new_ids:
            try:
                res = find_and_evaluate_matches(mid, scope=scope)
                matches_created += sum(1 for m in res.get('matches', []) if m.get('decision') != 'existing')
            except Exception as exc:
                # Log but don't fail the whole ingest if one match evaluation errors
                print(f"Warning: match evaluation failed for material {mid}: {exc}")

        return {
            "status": "success",
            "rows_inserted": inserted_count,
            "rows_skipped_existing": skipped_count,
            "matches_evaluated": matches_created,
            "normalization_sample": normalization_sample,
            "scope": scope,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

@app.get("/materials/{material_id}/candidates")
def find_candidates(material_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch the target material
        cursor.execute("SELECT category, embedding FROM cpse_materials WHERE id = %s", (material_id,))
        res = cursor.fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Material not found")
        
        target_category, target_embedding = res
        if not target_embedding:
            raise HTTPException(status_code=400, detail="Target material has no embedding")
        
        # Query for nearest neighbors using cosine similarity
        # pgvector cosine distance is <=>, similarity is 1 - distance
        cursor.execute("""
            SELECT id, cpse_name, original_code, normalized_description, 
                   1 - (embedding <=> %s::vector) AS similarity
            FROM cpse_materials
            WHERE category = %s AND id != %s
            AND 1 - (embedding <=> %s::vector) > 0.5
            ORDER BY similarity DESC
            LIMIT 10
        """, (target_embedding, target_category, material_id, target_embedding))
        
        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                "id": row[0],
                "cpse_name": row[1],
                "original_code": row[2],
                "normalized_description": row[3],
                "similarity_score": round(row[4], 4)
            })
            
        return {"material_id": material_id, "candidates": candidates}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.post("/materials/{material_id}/find_and_evaluate_matches")
def find_and_evaluate_matches(
    material_id: int,
    scope: str = Query("all", description="Comparison pool: all | cross | intra"),
):
    scope = _validate_scope(scope)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, category, raw_specs, embedding, cpse_name FROM cpse_materials WHERE id = %s",
            (material_id,),
        )
        res = cursor.fetchone()
        if not res: raise HTTPException(status_code=404, detail="Material not found")
        t_id, t_category, t_specs, t_embedding, t_cpse = res
        if not t_embedding: raise HTTPException(status_code=400, detail="Target has no embedding")
        
        cursor.execute("SELECT spec_name, spec_type FROM category_specs WHERE category = %s", (t_category,))
        cat_specs = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, raw_specs, 1 - (embedding <=> %s::vector) AS similarity
            FROM cpse_materials
            WHERE category = %s AND id != %s
            AND 1 - (embedding <=> %s::vector) >= %s
            AND (
                %s = 'all'
                OR (%s = 'cross' AND cpse_name <> %s)
                OR (%s = 'intra' AND cpse_name = %s)
            )
            ORDER BY similarity DESC LIMIT 10
        """, (
            t_embedding, t_category, material_id, t_embedding, MATCH_THRESHOLDS['similar_substitute'],
            scope, scope, t_cpse, scope, t_cpse,
        ))
        
        candidates = cursor.fetchall()
        results = []
        for c_id, c_specs, sim_score in candidates:
            # Avoid duplicate match rows for the same unordered pair
            cursor.execute("""
                SELECT id, status FROM material_matches
                WHERE (material_a_id = %s AND material_b_id = %s)
                   OR (material_a_id = %s AND material_b_id = %s)
                LIMIT 1
            """, (t_id, c_id, c_id, t_id))
            existing = cursor.fetchone()
            if existing:
                results.append({"match_id": existing[0], "candidate_id": c_id, "semantic_score": sim_score, "decision": "existing", "status": existing[1]})
                continue

            spec_result = _compare_specs_internal(t_specs, c_specs, cat_specs)
            decision = decide_match(sim_score, spec_result)

            # Persist ALL evaluated pairs, including rejects, so benchmarks can count true negatives
            status = 'pending_review' if decision != 'rejected' else 'rejected'
            cursor.execute("""
                INSERT INTO material_matches
                (material_a_id, material_b_id, semantic_score, spec_agreement, override_triggered, override_reason, decision_level, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (t_id, c_id, sim_score, Json(spec_result["spec_agreement"]), spec_result["override_triggered"], spec_result["override_reason"], decision, status))
            match_id = cursor.fetchone()[0]
            results.append({"match_id": match_id, "candidate_id": c_id, "semantic_score": sim_score, "decision": decision, "spec_result": spec_result})
        conn.commit()
        return {"material_id": material_id, "evaluated": len(candidates), "matches": results}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

from routers import matches

app.include_router(matches.router)