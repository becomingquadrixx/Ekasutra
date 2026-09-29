import uuid
import datetime
import re
import difflib
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

def get_db():
    # Local import to avoid circular dependencies with main.py
    from main import get_db_connection
    return get_db_connection()


def _tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


def _extract_term_pair_suggestion(raw_a: str, raw_b: str) -> tuple | None:
    """
    Very simple heuristic: if the two raw descriptions differ by exactly one
    token pair, suggest (raw_term, canonical_term). Returns None otherwise.
    """
    tokens_a = _tokenize(raw_a)
    tokens_b = _tokenize(raw_b)
    diff = list(difflib.ndiff(tokens_a, tokens_b))
    removed = [line[2:] for line in diff if line.startswith('- ')]
    added = [line[2:] for line in diff if line.startswith('+ ')]
    if len(removed) == 1 and len(added) == 1:
        return removed[0], added[0]
    return None


def _record_lexicon_suggestion(cursor, raw_term: str, canonical_term: str):
    """Upsert a proposed lexicon suggestion, bumping its count."""
    cursor.execute(
        "SELECT id, suggestion_count FROM lexicon_entries WHERE raw_term = %s AND canonical_term = %s",
        (raw_term, canonical_term)
    )
    row = cursor.fetchone()
    if row:
        new_count = row[1] + 1
        cursor.execute(
            "UPDATE lexicon_entries SET suggestion_count = %s WHERE id = %s",
            (new_count, row[0])
        )
    else:
        cursor.execute(
            """
            INSERT INTO lexicon_entries (raw_term, canonical_term, status, suggestion_count)
            VALUES (%s, %s, 'proposed', 1)
            """,
            (raw_term, canonical_term)
        )


@router.get("/matches")
def get_matches(status: str = "pending_review"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        query = """
            SELECT m.id, m.semantic_score, m.spec_agreement, m.decision_level, m.status,
                   a.id as a_id, a.cpse_name as a_cpse, a.raw_description as a_desc,
                   a.raw_specs as a_specs, a.normalized_description as a_norm,
                   b.id as b_id, b.cpse_name as b_cpse, b.raw_description as b_desc,
                   b.raw_specs as b_specs, b.normalized_description as b_norm,
                   a.category,
                   a.original_code as a_code, b.original_code as b_code,
                   m.override_triggered, m.override_reason
            FROM material_matches m
            JOIN cpse_materials a ON m.material_a_id = a.id
            JOIN cpse_materials b ON m.material_b_id = b.id
            WHERE m.status = %s
            ORDER BY m.id DESC
            LIMIT 100
        """
        cursor.execute(query, (status,))
        results = []
        for row in cursor.fetchall():
            category = row[15]
            cursor.execute(
                "SELECT spec_name, spec_type FROM category_specs WHERE category = %s",
                (category,)
            )
            spec_types = {name: st for name, st in cursor.fetchall()}

            results.append({
                "match_id": row[0],
                "semantic_score": row[1],
                "spec_agreement": row[2],
                "decision_level": row[3],
                "status": row[4],
                "material_a": {
                    "id": row[5], "cpse_name": row[6], "description": row[7],
                    "raw_specs": row[8], "normalized_description": row[9],
                    "original_code": row[16],
                },
                "material_b": {
                    "id": row[10], "cpse_name": row[11], "description": row[12],
                    "raw_specs": row[13], "normalized_description": row[14],
                    "original_code": row[17],
                },
                "category": category,
                "spec_types": spec_types,
                "override_triggered": row[18],
                "override_reason": row[19],
            })
        return {"matches": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/matches/{id}/approve")
def approve_match(id: int, reviewed_by: str = "demo_reviewer"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT material_a_id, material_b_id, status FROM material_matches WHERE id = %s",
            (id,),
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        if match[2] != 'pending_review':
            raise HTTPException(status_code=400, detail="Match is not pending review")
            
        mat_a, mat_b = match[0], match[1]
        
        cursor.execute(
            "SELECT cpse_material_id, cnmc_id FROM code_aliases WHERE cpse_material_id IN (%s, %s)",
            (mat_a, mat_b),
        )
        existing_aliases = cursor.fetchall()
        distinct_cnmcs = {row[1] for row in existing_aliases}
        if len(distinct_cnmcs) > 1:
            raise HTTPException(
                status_code=409,
                detail="Both materials are already mapped to different CNMCs. Rollback one mapping before merging.",
            )

        if distinct_cnmcs:
            cnmc_id = next(iter(distinct_cnmcs))
        else:
            cursor.execute(
                "SELECT category, normalized_description FROM cpse_materials WHERE id = %s",
                (mat_a,),
            )
            cat_desc = cursor.fetchone()
            
            cnmc_code = f"CNMC-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
                INSERT INTO cnmc_registry (cnmc_code, canonical_description, category, status)
                VALUES (%s, %s, %s, 'confirmed') RETURNING id
            """, (cnmc_code, cat_desc[1], cat_desc[0]))
            cnmc_id = cursor.fetchone()[0]
            
        for m_id in (mat_a, mat_b):
            cursor.execute("SELECT id FROM code_aliases WHERE cpse_material_id = %s", (m_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO code_aliases (cpse_material_id, cnmc_id) VALUES (%s, %s)",
                    (m_id, cnmc_id),
                )

        cursor.execute(
            "SELECT raw_description FROM cpse_materials WHERE id IN (%s, %s)",
            (mat_a, mat_b)
        )
        raw_descs = [r[0] for r in cursor.fetchall()]
        if len(raw_descs) == 2:
            suggestion = _extract_term_pair_suggestion(raw_descs[0], raw_descs[1])
            if suggestion:
                _record_lexicon_suggestion(cursor, suggestion[0], suggestion[1])

        cursor.execute(
            "UPDATE material_matches SET status = 'approved', reviewed_by = %s, reviewed_at = now() WHERE id = %s",
            (reviewed_by, id),
        )

        cursor.execute(
            "SELECT cnmc_code, status FROM cnmc_registry WHERE id = %s",
            (cnmc_id,),
        )
        cnmc_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT m.cpse_name, m.original_code, m.raw_description, m.id
            FROM code_aliases a
            JOIN cpse_materials m ON m.id = a.cpse_material_id
            WHERE a.cnmc_id = %s
            ORDER BY m.id
            """,
            (cnmc_id,),
        )
        aliases = [
            {
                "cpse_name": r[0],
                "original_code": r[1],
                "raw_description": r[2],
                "material_id": r[3],
            }
            for r in cursor.fetchall()
        ]
        conn.commit()
        
        return {
            "status": "success",
            "cnmc_id": cnmc_id,
            "cnmc_code": cnmc_row[0],
            "cnmc_status": cnmc_row[1],
            "match_id": id,
            "aliases": aliases,
            "raw_records_unchanged": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/matches/{id}/reject")
def reject_match(id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE material_matches SET status = 'rejected', reviewed_by = %s, reviewed_at = now() WHERE id = %s", ("demo_reviewer", id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Match not found")
        conn.commit()
        return {"status": "success", "match_id": id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/cnmc")
def get_cnmc_registry():
    conn = get_db()
    cursor = conn.cursor()
    try:
        query = """
            SELECT c.id, c.cnmc_code, c.canonical_description, c.category, c.status, COUNT(a.id) as alias_count,
                   COUNT(a.id) FILTER (WHERE a.flagged_for_review) as flagged_count
            FROM cnmc_registry c
            LEFT JOIN code_aliases a ON c.id = a.cnmc_id
            GROUP BY c.id
            ORDER BY c.id DESC
        """
        cursor.execute(query)
        results = [{
            "id": r[0],
            "cnmc_code": r[1],
            "description": r[2],
            "category": r[3],
            "status": r[4],
            "alias_count": r[5],
            "flagged_count": r[6],
        } for r in cursor.fetchall()]
        return {"registry": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/cnmc/{cnmc_id}")
def get_cnmc_detail(cnmc_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, cnmc_code, canonical_description, category, status, created_at
            FROM cnmc_registry WHERE id = %s
            """,
            (cnmc_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="CNMC not found")
        cursor.execute(
            """
            SELECT m.id, m.cpse_name, m.original_code, m.raw_description,
                   m.normalized_description, a.flagged_for_review, a.mapped_at
            FROM code_aliases a
            JOIN cpse_materials m ON m.id = a.cpse_material_id
            WHERE a.cnmc_id = %s
            ORDER BY m.id
            """,
            (cnmc_id,),
        )
        aliases = [
            {
                "material_id": r[0],
                "cpse_name": r[1],
                "original_code": r[2],
                "raw_description": r[3],
                "normalized_description": r[4],
                "flagged_for_review": r[5],
                "mapped_at": r[6],
            }
            for r in cursor.fetchall()
        ]
        return {
            "id": row[0],
            "cnmc_code": row[1],
            "description": row[2],
            "category": row[3],
            "status": row[4],
            "created_at": row[5],
            "aliases": aliases,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/analytics/summary")
def get_analytics():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT m.category, COUNT(DISTINCT mm.id) as approved_matches, COUNT(DISTINCT m.id) as total_materials
            FROM cpse_materials m
            LEFT JOIN material_matches mm ON (mm.material_a_id = m.id OR mm.material_b_id = m.id) AND mm.status = 'approved'
            GROUP BY m.category
        """)
        dup_rate = {r[0]: {"approved_matches": r[1], "total_materials": r[2], "rate": round((r[1]/r[2]), 4) if r[2] > 0 else 0} for r in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(DISTINCT cpse_material_id) FROM code_aliases")
        mapped_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cpse_materials")
        total_count = cursor.fetchone()[0]
        progress = mapped_count / total_count if total_count > 0 else 0
        
        cursor.execute("""
            SELECT a.category, COUNT(*) 
            FROM material_matches m
            JOIN cpse_materials a ON m.material_a_id = a.id
            WHERE m.status = 'pending_review'
            GROUP BY a.category
        """)
        pending = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM cnmc_registry")
        cnmc_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM material_matches WHERE status = 'pending_review'")
        pending_total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM material_matches WHERE status = 'approved'")
        approved_total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM material_matches WHERE override_triggered = TRUE")
        override_total = cursor.fetchone()[0]

        benchmark = None
        results_path = Path(__file__).resolve().parents[1] / "benchmark" / "last_results.json"
        if results_path.exists():
            try:
                benchmark = json.loads(results_path.read_text())
            except Exception:
                benchmark = None

        return {
            "duplicate_rate_by_category": dup_rate,
            "overall_progress_percent": round(progress * 100, 2),
            "pending_reviews_by_category": pending,
            "mapped_count": mapped_count,
            "total_materials": total_count,
            "unmapped_count": max(total_count - mapped_count, 0),
            "cnmc_count": cnmc_count,
            "pending_total": pending_total,
            "approved_total": approved_total,
            "hard_gate_overrides": override_total,
            "benchmark": benchmark,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/rollback/{cnmc_id}")
def rollback_cnmc(cnmc_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE cnmc_registry SET status = 'unconfirmed' WHERE id = %s", (cnmc_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="CNMC not found")

        cursor.execute("UPDATE code_aliases SET flagged_for_review = TRUE WHERE cnmc_id = %s", (cnmc_id,))
        cursor.execute("SELECT COUNT(*) FROM code_aliases WHERE cnmc_id = %s", (cnmc_id,))
        flagged = cursor.fetchone()[0]
        conn.commit()
        return {
            "status": "success",
            "cnmc_id": cnmc_id,
            "cnmc_status": "unconfirmed",
            "aliases_flagged": flagged,
            "aliases_retained": True,
            "note": "Original CPSE codes were never deleted. Mapping is unconfirmed and flagged for re-review.",
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/lexicon")
def list_lexicon(status: str | None = None, min_suggestion_count: int = 0):
    """List lexicon entries, optionally filtered by status and suggestion count."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        clauses = ["COALESCE(suggestion_count, 0) >= %s"]
        params: list = [min_suggestion_count]
        if status:
            clauses.append("status = %s")
            params.append(status)
        where = " WHERE " + " AND ".join(clauses)
        cursor.execute(
            f"""
            SELECT id, raw_term, canonical_term, status, suggestion_count, created_at, proposed_by, approved_by
            FROM lexicon_entries
            {where}
            ORDER BY created_at DESC
            """,
            params,
        )
        results = [
            {
                "id": r[0],
                "raw_term": r[1],
                "canonical_term": r[2],
                "status": r[3],
                "suggestion_count": r[4],
                "created_at": r[5],
                "proposed_by": r[6],
                "approved_by": r[7],
                "ready_for_admin": (r[3] == "proposed" and (r[4] or 0) >= 3),
            }
            for r in cursor.fetchall()
        ]
        return {"lexicon": results, "activation_threshold": 3}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/lexicon/propose")
def propose_lexicon_entry(raw_term: str, canonical_term: str, proposed_by: str = "system"):
    """Manually propose a new lexicon entry (status = 'proposed')."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO lexicon_entries (raw_term, canonical_term, status, proposed_by, suggestion_count)
            VALUES (%s, %s, 'proposed', %s, 1) RETURNING id
            """,
            (raw_term.strip(), canonical_term.strip(), proposed_by)
        )
        entry_id = cursor.fetchone()[0]
        conn.commit()
        return {"status": "success", "lexicon_id": entry_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/lexicon/{id}/approve")
def approve_lexicon_entry(id: int, approved_by: str = "admin"):
    """Admin approves a proposed lexicon entry, activating it."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE lexicon_entries SET status = 'active', approved_by = %s WHERE id = %s AND status = 'proposed' RETURNING id",
            (approved_by, id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposed lexicon entry not found or already active")
        conn.commit()
        return {"status": "success", "lexicon_id": row[0]}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
