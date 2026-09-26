import os
import sys

# Ensure the project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import _compare_specs_internal, decide_match, get_db_connection
import pytest

@pytest.fixture(scope='module')
def cat_specs_pipes():
    """Fetch category specs for Pipes from the DB"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT spec_name, spec_type FROM category_specs WHERE category = %s", ('Pipes',))
    specs = cur.fetchall()
    cur.close()
    conn.close()
    return specs

def test_diameter_mismatch_triggers_override(cat_specs_pipes):
    # Two material spec dicts with differing diameters
    specs_a = {
        'spec_diameter': '100mm',
        'spec_pressure_rating': '150psi',
        'spec_material_grade': 'A36'
    }
    specs_b = {
        'spec_diameter': '150mm',
        'spec_pressure_rating': '150psi',
        'spec_material_grade': 'A36'
    }
    result = _compare_specs_internal(specs_a, specs_b, cat_specs_pipes)
    assert result["override_triggered"] is True, "Critical spec mismatch should trigger override"
    assert "diameter mismatch" in result["override_reason"].lower()
    decision = decide_match(semantic_score=0.96, spec_result=result)
    assert decision == "rejected", "Override should cause rejection"

def test_matching_diameter_no_override(cat_specs_pipes):
    # Two material specs that match on critical specs but differ in wording
    specs_a = {
        'spec_diameter': '100mm',
        'spec_pressure_rating': '150psi',
        'spec_material_grade': 'A36'
    }
    specs_b = {
        'spec_diameter': '100mm',
        'spec_pressure_rating': '150psi',
        'spec_material_grade': 'A36'
    }
    result = _compare_specs_internal(specs_a, specs_b, cat_specs_pipes)
    assert result["override_triggered"] is False, "No critical mismatch should not trigger override"
    decision = decide_match(semantic_score=0.96, spec_result=result)
    assert decision in ("exact", "functional_equivalent"), "Matching specs should not be rejected"
