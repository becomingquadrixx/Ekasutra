"""
EKASUTRA — Exceptional Realistic Benchmark Dataset

Produces 150 rows that look like genuine CPSE procurement master data:
  - Real Indian CPSE names
  - Realistic material codes (CPSE-specific prefixes + running numbers)
  - Authentic procurement descriptions with common abbreviations and variants
  - 45 true duplicate pairs (same material, different wording)
  - 15 near-duplicate traps (almost identical text, one critical spec differs)
  - 30 unrelated negatives

Every record has a unique critical-spec fingerprint within its category,
so the ground truth is exhaustive and metrics are meaningful.
"""

import csv
import random
from pathlib import Path

random.seed(2026)
OUT_DIR = Path(__file__).parent

# ── REAL CPSEs ──────────────────────────────────────────────────────────────
CPSE_NAMES = [
    "ONGC", "NTPC", "BHEL", "IOCL", "GAIL", "SAIL", "CIL",
    "BPCL", "HPCL", "POWERGRID", "NLC", "NHPC", "OIL", "MRPL", "CPCL"
]

# CPSE-specific material code prefixes (plausible patterns)
CPSE_PREFIX = {
    "ONGC": "ONG", "NTPC": "NTP", "BHEL": "BHL", "IOCL": "IOC",
    "GAIL": "GAL", "SAIL": "SAL", "CIL": "CIL", "BPCL": "BPC",
    "HPCL": "HPC", "POWERGRID": "PGC", "NLC": "NLC", "NHPC": "NHC",
    "OIL": "OIL", "MRPL": "MRP", "CPCL": "CPC"
}

# ── REALISTIC VALUE POOLS ─────────────────────────────────────────────────
PIPE_DIAMETERS = ["50mm", "65mm", "80mm", "100mm", "125mm", "150mm", "200mm", "250mm"]
PIPE_PRESSURES = ["16bar", "25bar", "40bar", "50psi", "150psi", "300psi"]
PIPE_GRADES = ["A106 Gr B", "A53 Gr B", "A36", "IS 1239 YST 210", "SS 304", "SS 316"]

BOLT_SIZES = ["M6", "M8", "M10", "M12", "M16", "M20", "M24"]
BOLT_PITCH = {"M6":"1.0mm","M8":"1.25mm","M10":"1.5mm","M12":"1.75mm","M16":"2.0mm","M20":"2.5mm","M24":"3.0mm"}
BOLT_STRENGTH = ["4.6", "5.8", "8.8", "10.9", "12.9"]
BOLT_MATERIAL = ["MS", "SS 304", "SS 316", "High Tensile Steel", "Galvanized Steel"]

CABLE_SIZES = ["1.5mm2", "2.5mm2", "4mm2", "6mm2", "10mm2", "16mm2", "25mm2"]
CABLE_VOLTAGES = ["650V", "1100V", "3300V"]
CABLE_CORES = ["2 Core", "3 Core", "3.5 Core", "4 Core", "12 Pair", "1 Pair"]

# ── DESCRIPTION TEMPLATES (realistic procurement wording) ───────────────────
def pipe_desc_templates(d, p, g):
    mat_short = g.split()[0]
    dn = d.replace("mm", "")
    return [
        f"Seamless {mat_short} pipe {d} NB, {p}, grade {g}, 6m length, IS certified",
        f"Pipe {g} {d} nominal bore, {p}, 6 meter, seamless finish",
        f"Carbon steel pipe {d} dia, {p}, grade {g}, length 6m, mill test certificate",
        f"M.S. pipe DN {dn}, {p}, {g}, 6m, black finish",
        f"{mat_short} pipe {d} NB, sch 40, {p}, grade {g}, 6m length",
    ]


def bolt_desc_templates(sz, pitch, st, m):
    return [
        f"Hex bolt {sz}x{pitch}x60mm, {m}, grade {st}, DIN 933, fully threaded",
        f"{m} hex head bolt {sz} pitch {pitch}, strength grade {st}, 60mm lg",
        f"High tensile bolt {sz} x {pitch}, {m}, class {st}, DIN 931",
        f"{sz} hex bolt, {st} class, {m}, 60mm length, zinc plated",
        f"DIN 933 hex bolt {sz}x60, material {m}, grade {st}, as per drawing",
    ]


def cable_desc_templates(sz, v, c):
    cond = "copper" if sz in ["1.5mm2","2.5mm2","4mm2","6mm2","10mm2"] else "aluminium"
    return [
        f"PVC insulated {cond} cable {c} x {sz}, {v}, 1km drum, IS 694",
        f"{cond} conductor cable {sz}, {c}, {v}, PVC insulated, 1000m reel",
        f"{v} grade {cond} cable {c} x {sz}, 1km length, armoured",
        f"LT power cable {c} x {sz}, {v}, {cond}, as per IS 1554",
        f"{sz} sq mm {cond} cable, {c}, {v}, PVC insulated, FRLS",
    ]


# ── MATERIAL CODE GENERATOR ───────────────────────────────────────────────
code_counters = {}

def material_code(cpse, category):
    prefix = CPSE_PREFIX.get(cpse, cpse[:3].upper())
    cat_letter = {"Pipes": "P", "Fasteners": "F", "Electrical_Cable": "C"}[category]
    key = (cpse, cat_letter)
    code_counters[key] = code_counters.get(key, 0) + 1
    return f"{prefix}-{cat_letter}{code_counters[key]:04d}"


EMPTY = {
    "spec_diameter":"", "spec_pressure_rating":"", "spec_material_grade":"",
    "spec_thread_size_pitch":"", "spec_strength_grade":"", "spec_material":"",
    "spec_conductor_size":"", "spec_voltage_rating":"", "spec_core_count":""
}


class UniqueComboPool:
    """Draw unique (a,b,c) combinations without replacement across multiple calls."""
    def __init__(self, pool_a, pool_b, pool_c):
        self.combos = [(a, b, c) for a in pool_a for b in pool_b for c in pool_c]
        random.shuffle(self.combos)
        self.used = set()

    def draw(self, n):
        drawn = []
        for combo in self.combos:
            if combo in self.used:
                continue
            self.used.add(combo)
            drawn.append(combo)
            if len(drawn) == n:
                break
        if len(drawn) < n:
            raise ValueError(f"Not enough unique combos available (needed {n}, got {len(drawn)})")
        return drawn


rows, gt = [], []

# ── TRUE DUPLICATES ─────────────────────────────────────────────────────────
# 15 pairs per category = 45 pairs total

# Pipes
pipe_pool = UniqueComboPool(PIPE_DIAMETERS, PIPE_PRESSURES, PIPE_GRADES)
pipe_combos = pipe_pool.draw(15)
for d, p, g in pipe_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Pipes")
    code_b = material_code(cpse_b, "Pipes")
    desc_a, desc_b = random.sample(pipe_desc_templates(d, p, g), 2)
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_diameter": d, "spec_pressure_rating": p, "spec_material_grade": g})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_diameter": d, "spec_pressure_rating": p, "spec_material_grade": g})
    gt.append((cpse_a, code_a, cpse_b, code_b, True))

# Fasteners
bolt_pool = UniqueComboPool(BOLT_SIZES, BOLT_STRENGTH, BOLT_MATERIAL)
bolt_combos = bolt_pool.draw(15)
for sz, st, m in bolt_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Fasteners")
    code_b = material_code(cpse_b, "Fasteners")
    desc_a, desc_b = random.sample(bolt_desc_templates(sz, BOLT_PITCH[sz], st, m), 2)
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_thread_size_pitch": f"{sz} {BOLT_PITCH[sz]}", "spec_strength_grade": st, "spec_material": m})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_thread_size_pitch": f"{sz} {BOLT_PITCH[sz]}", "spec_strength_grade": st, "spec_material": m})
    gt.append((cpse_a, code_a, cpse_b, code_b, True))

# Cables
cable_pool = UniqueComboPool(CABLE_SIZES, CABLE_VOLTAGES, CABLE_CORES)
cable_combos = cable_pool.draw(15)
for sz, v, c in cable_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Electrical_Cable")
    code_b = material_code(cpse_b, "Electrical_Cable")
    desc_a, desc_b = random.sample(cable_desc_templates(sz, v, c), 2)
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_conductor_size": sz, "spec_voltage_rating": v, "spec_core_count": c})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_conductor_size": sz, "spec_voltage_rating": v, "spec_core_count": c})
    gt.append((cpse_a, code_a, cpse_b, code_b, True))

# ── NEAR-DUPLICATE TRAPS ────────────────────────────────────────────────────
# 5 traps per category = 15 traps total

def alter_trap(pool, original, pools_by_index):
    """
    Alter one dimension of a combo, drawing the altered combo from the pool
    so uniqueness is guaranteed. Returns (new_combo, changed_index).
    """
    # Try each dimension in random order
    indices = [0, 1, 2]
    random.shuffle(indices)
    for idx in indices:
        candidates = [x for x in pools_by_index[idx] if x != original[idx]]
        random.shuffle(candidates)
        for new_val in candidates:
            new_combo = list(original)
            new_combo[idx] = new_val
            new_combo = tuple(new_combo)
            if new_combo not in pool.used:
                return new_combo, idx
    raise ValueError("Could not find a unique altered combo")

# Pipes traps
pipe_trap_combos = pipe_pool.draw(5)
for d, p, g in pipe_trap_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Pipes")
    code_b = material_code(cpse_b, "Pipes")
    d2, p2, g2 = alter_trap(pipe_pool, (d, p, g), [PIPE_DIAMETERS, PIPE_PRESSURES, PIPE_GRADES])
    pipe_pool.used.add((d2, p2, g2))
    desc_a = pipe_desc_templates(d, p, g)[0]
    desc_b = pipe_desc_templates(d2, p2, g2)[1]
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_diameter": d, "spec_pressure_rating": p, "spec_material_grade": g})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_diameter": d2, "spec_pressure_rating": p2, "spec_material_grade": g2})
    gt.append((cpse_a, code_a, cpse_b, code_b, False))

# Fasteners traps
bolt_trap_combos = bolt_pool.draw(5)
for sz, st, m in bolt_trap_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Fasteners")
    code_b = material_code(cpse_b, "Fasteners")
    sz2, st2, m2 = alter_trap(bolt_pool, (sz, st, m), [BOLT_SIZES, BOLT_STRENGTH, BOLT_MATERIAL])
    bolt_pool.used.add((sz2, st2, m2))
    desc_a = bolt_desc_templates(sz, BOLT_PITCH[sz], st, m)[0]
    desc_b = bolt_desc_templates(sz2, BOLT_PITCH[sz2], st2, m2)[1]
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_thread_size_pitch": f"{sz} {BOLT_PITCH[sz]}", "spec_strength_grade": st, "spec_material": m})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_thread_size_pitch": f"{sz2} {BOLT_PITCH[sz2]}", "spec_strength_grade": st2, "spec_material": m2})
    gt.append((cpse_a, code_a, cpse_b, code_b, False))

# Cables traps
cable_trap_combos = cable_pool.draw(5)
for sz, v, c in cable_trap_combos:
    cpse_a, cpse_b = random.sample(CPSE_NAMES, 2)
    code_a = material_code(cpse_a, "Electrical_Cable")
    code_b = material_code(cpse_b, "Electrical_Cable")
    sz2, v2, c2 = alter_trap(cable_pool, (sz, v, c), [CABLE_SIZES, CABLE_VOLTAGES, CABLE_CORES])
    cable_pool.used.add((sz2, v2, c2))
    desc_a = cable_desc_templates(sz, v, c)[0]
    desc_b = cable_desc_templates(sz2, v2, c2)[1]
    rows.append({**EMPTY, "cpse_name": cpse_a, "original_code": code_a, "description": desc_a,
                 "spec_conductor_size": sz, "spec_voltage_rating": v, "spec_core_count": c})
    rows.append({**EMPTY, "cpse_name": cpse_b, "original_code": code_b, "description": desc_b,
                 "spec_conductor_size": sz2, "spec_voltage_rating": v2, "spec_core_count": c2})
    gt.append((cpse_a, code_a, cpse_b, code_b, False))

# ── GENUINE UNRELATED NEGATIVES ─────────────────────────────────────────────
# 10 per category = 30 records

pipe_neg_combos = pipe_pool.draw(10)
for d, p, g in pipe_neg_combos:
    cpse = random.choice(CPSE_NAMES)
    code = material_code(cpse, "Pipes")
    rows.append({**EMPTY, "cpse_name": cpse, "original_code": code, "description": pipe_desc_templates(d, p, g)[0],
                 "spec_diameter": d, "spec_pressure_rating": p, "spec_material_grade": g})

bolt_neg_combos = bolt_pool.draw(10)
for sz, st, m in bolt_neg_combos:
    cpse = random.choice(CPSE_NAMES)
    code = material_code(cpse, "Fasteners")
    rows.append({**EMPTY, "cpse_name": cpse, "original_code": code, "description": bolt_desc_templates(sz, BOLT_PITCH[sz], st, m)[0],
                 "spec_thread_size_pitch": f"{sz} {BOLT_PITCH[sz]}", "spec_strength_grade": st, "spec_material": m})

cable_neg_combos = cable_pool.draw(10)
for sz, v, c in cable_neg_combos:
    cpse = random.choice(CPSE_NAMES)
    code = material_code(cpse, "Electrical_Cable")
    rows.append({**EMPTY, "cpse_name": cpse, "original_code": code, "description": cable_desc_templates(sz, v, c)[0],
                 "spec_conductor_size": sz, "spec_voltage_rating": v, "spec_core_count": c})

random.shuffle(rows)

FIELDNAMES = ["cpse_name", "original_code", "description",
              "spec_diameter", "spec_pressure_rating", "spec_material_grade",
              "spec_thread_size_pitch", "spec_strength_grade", "spec_material",
              "spec_conductor_size", "spec_voltage_rating", "spec_core_count"]

with open(OUT_DIR / "synthetic_data.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    w.writeheader()
    w.writerows(rows)

with open(OUT_DIR / "ground_truth.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["cpse_a", "code_a", "cpse_b", "code_b", "should_match"])
    for ca, coa, cb, cob, m in gt:
        w.writerow([ca, coa, cb, cob, str(m).lower()])

pos = sum(1 for *_, m in gt if m)
neg = sum(1 for *_, m in gt if not m)
print(f"Wrote {len(rows)} rows -> {OUT_DIR / 'synthetic_data.csv'}")
print(f"Wrote {len(gt)} ground-truth pairs -> {OUT_DIR / 'ground_truth.csv'}")
print(f"  True duplicates  : {pos}")
print(f"  Near-dup traps   : {neg}")
print(f"  Unrelated records: 30")
