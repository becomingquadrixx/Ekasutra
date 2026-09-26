"""
Generates synthetic CPSE-style data for benchmarking.
Outputs CSVs for the pipeline.
"""

import csv
import random
from pathlib import Path

random.seed(2026)
OUT_DIR = Path(__file__).parent

CPSE_POOL = [
    ("ONGC", "Oil and Natural Gas Corporation"),
    ("NTPC", "National Thermal Power Corporation"),
    ("BHEL", "Bharat Heavy Electricals Limited"),
    ("IOCL", "Indian Oil Corporation Limited"),
    ("GAIL", "GAIL (India) Limited"),
    ("SAIL", "Steel Authority of India Limited"),
    ("CIL", "Coal India Limited"),
    ("BPCL", "Bharat Petroleum Corporation Limited"),
    ("HPCL", "Hindustan Petroleum Corporation Limited"),
    ("PGCIL", "Power Grid Corporation of India Limited"),
    ("NLCIL", "NLC India Limited"),
    ("NMDC", "National Mineral Development Corporation"),
    ("RINL", "Rashtriya Ispat Nigam Limited"),
    ("NALCO", "National Aluminium Company Limited"),
    ("HAL", "Hindustan Aeronautics Limited"),
]


def cpse_pair():
    a, b = random.sample(CPSE_POOL, 2)
    return a[0], b[0]


def code_for(cpse: str, seq: int) -> str:
    """Return an organisation-specific material code."""
    if cpse == "ONGC":
        return f"MM-{45000 + seq:05d}"
    if cpse == "NTPC":
        return f"MAT-{seq:06d}"
    if cpse == "BHEL":
        return f"BHE/DPW/{seq:05d}"
    if cpse == "IOCL":
        return f"IOCL/REF/{seq:05d}"
    if cpse == "GAIL":
        return f"GAIL/PIPE/{seq:05d}"
    if cpse == "SAIL":
        return f"SAIL/MSP/{seq:05d}"
    if cpse == "CIL":
        return f"CIL/SP/{seq:05d}"
    if cpse == "BPCL":
        return f"BPCL/KOCHI/{seq:05d}"
    if cpse == "HPCL":
        return f"HPCL/VZ/{seq:05d}"
    if cpse == "PGCIL":
        return f"PGCIL/TL/{seq:05d}"
    if cpse == "NLCIL":
        return f"NLC/PW/{seq:05d}"
    if cpse == "NMDC":
        return f"NMDC/ME/{seq:05d}"
    if cpse == "RINL":
        return f"RINL/VSP/{seq:05d}"
    if cpse == "NALCO":
        return f"NALCO/AL/{seq:05d}"
    return f"{cpse}/{seq:05d}"


# ── PIPES ───────────────────────────────────────────────────────────────────
PIPE_TEMPLATES = [
    "{mat} ERW Pipe NB {dia} {sch} as per {std}",
    "{mat} Seamless Pipe OD {dia} WT {wt} {std}",
    "{mat} Pipe {dia} NB {cls} Class {std}",
    "{std} {mat} Pipe {dia} Sch {sch} SMLS",
    "Pipe {mat} {dia} x {wt} {std} HSN-7304",
]
PIPE_MATS = [
    ("MS", "Mild Steel", "A106 Gr B"),
    ("CS", "Carbon Steel", "A53 Gr B"),
    ("SS", "Stainless Steel", "304"),
    ("SS316", "Stainless Steel 316", "316"),
    ("GI", "Galvanized Iron", "IS 1239"),
]
PIPE_DIAS = ["15mm", "20mm", "25mm", "32mm", "40mm", "50mm", "65mm", "80mm", "100mm", "150mm"]
PIPE_PRS = ["150 psi", "300 psi", "600 psi", "1000 psi", "1500 psi"]
PIPE_SCH = ["40", "80", "160"]
PIPE_STD = ["IS 1239", "ASTM A106", "ASTM A53", "IS 3589", "DIN 2448"]


def pipe_desc_and_specs(mat_short, mat_long, grade, dia, pr, sch, std, wt, cls):
    template = random.choice(PIPE_TEMPLATES)
    desc = template.format(
        mat=mat_short, dia=dia, sch=sch, std=std, wt=wt, cls=cls
    )
    specs = {
        "spec_diameter": dia,
        "spec_pressure_rating": pr,
        "spec_material_grade": grade,
        "spec_length": random.choice(["6m", "5.8m", "3m"]),
        "spec_surface_finish": random.choice(["Bare", "Galvanized", "Painted"]),
        "spec_wall_thickness": wt,
    }
    return desc, specs


# ── FASTENERS ────────────────────────────────────────────────────────────────
BOLT_TEMPLATES = [
    "Hex Bolt {sz}x{len} LG {mat} {grade} {std}",
    "Hex Hd Bolt {sz} x {len} {mat} {grade}",
    "Bolt {std} {sz}x{len} {mat} {grade} Full Thread",
    "{mat} Hex Bolt {sz} x {len} {grade} {std}",
]
BOLT_SIZES = ["M6", "M8", "M10", "M12", "M16", "M20", "M24"]
BOLT_PITCH = {"M6": "1.0mm", "M8": "1.25mm", "M10": "1.5mm", "M12": "1.75mm",
              "M16": "2.0mm", "M20": "2.5mm", "M24": "3.0mm"}
BOLT_LEN = ["25mm", "30mm", "40mm", "50mm", "60mm", "80mm", "100mm"]
BOLT_MATS = [
    ("MS", "Mild Steel", "8.8"),
    ("CS", "Carbon Steel", "4.6"),
    ("SS", "Stainless Steel", "A2-70"),
    ("SS316", "Stainless Steel 316", "A4-80"),
    ("GI", "Galvanized Iron", "4.6"),
]
BOLT_GRADES = ["4.6", "5.8", "8.8", "10.9", "12.9", "A2-70", "A4-80"]
BOLT_STD = ["DIN 933", "IS 1364", "ISO 4017", "ASTM A193"]


def bolt_desc_and_specs(mat_short, mat_long, grade, sz, blen, std):
    template = random.choice(BOLT_TEMPLATES)
    desc = template.format(
        sz=sz, len=blen, mat=mat_short, grade=grade, std=std
    )
    specs = {
        "spec_thread_size_pitch": f"{sz} x {BOLT_PITCH[sz]}",
        "spec_strength_grade": grade,
        "spec_material": mat_long,
        "spec_head_type": "Hex Head",
        "spec_bolt_length": blen,
    }
    return desc, specs


# ── ELECTRICAL CABLE ─────────────────────────────────────────────────────────
CABLE_TEMPLATES = [
    "{cond} {size} {core}C {volt} XLPE {std}",
    "{size} {cond} Cable {core} Core {volt} {std}",
    "HT Cable {volt} {size} {core}C XLPE {cond}",
    "{cond} Conductor Cable {size} {core} Core {volt} Armoured",
    "PVC Insulated {cond} Wire {size} {volt} {std}",
]
CABLE_SIZES = ["1.5mm2", "2.5mm2", "4mm2", "6mm2", "10mm2", "16mm2", "25mm2", "35mm2",
               "50mm2", "70mm2", "95mm2", "120mm2", "185mm2", "240mm2"]
CABLE_VOLTS = ["650V", "1100V", "3.3kV", "6.6kV", "11kV"]
CABLE_CORES = ["1", "2", "3", "3.5", "4"]
CABLE_CONDS = ["Cu", "Al", "Copper", "Aluminium"]
CABLE_STD = ["IS 7098", "IS 694", "IS 1554", "IEC 60502"]


def cable_desc_and_specs(cond, size, volt, core, std):
    template = random.choice(CABLE_TEMPLATES)
    desc = template.format(cond=cond, size=size, core=core, volt=volt, std=std)
    specs = {
        "spec_conductor_size": size,
        "spec_voltage_rating": volt,
        "spec_core_count": core,
        "spec_insulation_color_code": random.choice(["R-Y-B", "Black", "Red"]),
    }
    return desc, specs


# ── shared helpers ─────────────────────────────────────────────────────────
ALL_SPECS = [
    "spec_diameter", "spec_pressure_rating", "spec_material_grade",
    "spec_length", "spec_surface_finish", "spec_wall_thickness",
    "spec_thread_size_pitch", "spec_strength_grade", "spec_material",
    "spec_head_type", "spec_bolt_length",
    "spec_conductor_size", "spec_voltage_rating", "spec_core_count",
    "spec_insulation_color_code",
]


def make_row(cpse, code, category, description, specs):
    row = {
        "cpse_name": cpse,
        "original_code": code,
        "description": description,
    }
    for s in ALL_SPECS:
        row[s] = specs.get(s, "")
    row["category"] = category
    return row


rows = []
gt = []
seq = 1000


def add_true_dup_pair(category, desc_specs_fn, *args):
    global seq
    cpse_a, cpse_b = cpse_pair()
    code_a = code_for(cpse_a, seq)
    seq += 1
    code_b = code_for(cpse_b, seq)
    seq += 1
    desc_a, specs_a = desc_specs_fn(*args)
    # Second description: same specs, slightly different wording
    desc_b, specs_b = desc_specs_fn(*args)
    while desc_b == desc_a:
        desc_b, specs_b = desc_specs_fn(*args)
    rows.append(make_row(cpse_a, code_a, category, desc_a, specs_a))
    rows.append(make_row(cpse_b, code_b, category, desc_b, specs_b))
    gt.append((cpse_a, code_a, cpse_b, code_b, True))


def add_trap_pair(category, desc_specs_fn, args, mutate_spec):
    global seq
    cpse_a, cpse_b = cpse_pair()
    code_a = code_for(cpse_a, seq)
    seq += 1
    code_b = code_for(cpse_b, seq)
    seq += 1
    args_a = list(args)
    desc_a, specs_a = desc_specs_fn(*args_a)
    
    args_b = list(args)
    if category == "Pipes":
        if mutate_spec == "spec_diameter": args_b[3] = random.choice([x for x in PIPE_DIAS if x != args_a[3]])
        elif mutate_spec == "spec_pressure_rating": args_b[4] = random.choice([x for x in PIPE_PRS if x != args_a[4]])
        elif mutate_spec == "spec_material_grade":
            new_mat = random.choice([m for m in PIPE_MATS if m[2] != args_a[2]])
            args_b[0], args_b[1], args_b[2] = new_mat
        elif mutate_spec == "spec_wall_thickness": args_b[7] = random.choice([x for x in ["2.77mm", "3.4mm", "4.0mm", "5.5mm", "7.1mm"] if x != args_a[7]])
    elif category == "Fasteners":
        if mutate_spec == "spec_thread_size_pitch": args_b[3] = random.choice([x for x in BOLT_SIZES if x != args_a[3]])
        elif mutate_spec == "spec_strength_grade": args_b[2] = random.choice([x for x in BOLT_GRADES if x != args_a[2]])
        elif mutate_spec == "spec_material":
            new_mat = random.choice([m for m in BOLT_MATS if m[1] != args_a[1]])
            args_b[0], args_b[1], args_b[2] = new_mat
        elif mutate_spec == "spec_bolt_length": args_b[4] = random.choice([x for x in BOLT_LEN if x != args_a[4]])
    elif category == "Electrical_Cable":
        if mutate_spec == "spec_conductor_size": args_b[1] = random.choice([x for x in CABLE_SIZES if x != args_a[1]])
        elif mutate_spec == "spec_voltage_rating": args_b[2] = random.choice([x for x in CABLE_VOLTS if x != args_a[2]])
        elif mutate_spec == "spec_core_count": args_b[3] = random.choice([x for x in CABLE_CORES if x != args_a[3]])
        
    desc_b, specs_b = desc_specs_fn(*args_b)
    
    rows.append(make_row(cpse_a, code_a, category, desc_a, specs_a))
    rows.append(make_row(cpse_b, code_b, category, desc_b, specs_b))
    gt.append((cpse_a, code_a, cpse_b, code_b, False))


def add_negative(category, desc_specs_fn, *args):
    global seq
    cpse = random.choice([c[0] for c in CPSE_POOL])
    code = code_for(cpse, seq)
    seq += 1
    desc, specs = desc_specs_fn(*args)
    rows.append(make_row(cpse, code, category, desc, specs))


# ── build the dataset ────────────────────────────────────────────────────────
# 40 true duplicate pairs across categories
for _ in range(14):
    mat = random.choice(PIPE_MATS)
    add_true_dup_pair(
        "Pipes", pipe_desc_and_specs,
        mat[0], mat[1], mat[2],
        random.choice(PIPE_DIAS), random.choice(PIPE_PRS),
        random.choice(PIPE_SCH), random.choice(PIPE_STD),
        random.choice(["2.77mm", "3.4mm", "4.0mm", "5.5mm", "7.1mm"]),
        random.choice(["Light", "Medium", "Heavy"])
    )

for _ in range(13):
    mat = random.choice(BOLT_MATS)
    add_true_dup_pair(
        "Fasteners", bolt_desc_and_specs,
        mat[0], mat[1], mat[2],
        random.choice(BOLT_SIZES), random.choice(BOLT_LEN),
        random.choice(BOLT_STD)
    )

for _ in range(13):
    add_true_dup_pair(
        "Electrical_Cable", cable_desc_and_specs,
        random.choice(CABLE_CONDS), random.choice(CABLE_SIZES),
        random.choice(CABLE_VOLTS), random.choice(CABLE_CORES),
        random.choice(CABLE_STD)
    )

# 20 near-duplicate traps
for _ in range(7):
    mat = random.choice(PIPE_MATS)
    add_trap_pair(
        "Pipes", pipe_desc_and_specs,
        (mat[0], mat[1], mat[2], random.choice(PIPE_DIAS),
         random.choice(PIPE_PRS), random.choice(PIPE_SCH), random.choice(PIPE_STD),
         random.choice(["2.77mm", "3.4mm", "4.0mm", "5.5mm", "7.1mm"]),
         random.choice(["Light", "Medium", "Heavy"])),
        random.choice(["spec_diameter", "spec_pressure_rating", "spec_material_grade", "spec_wall_thickness"])
    )

for _ in range(7):
    mat = random.choice(BOLT_MATS)
    add_trap_pair(
        "Fasteners", bolt_desc_and_specs,
        (mat[0], mat[1], mat[2], random.choice(BOLT_SIZES),
         random.choice(BOLT_LEN), random.choice(BOLT_STD)),
        random.choice(["spec_thread_size_pitch", "spec_strength_grade", "spec_material", "spec_bolt_length"])
    )

for _ in range(6):
    add_trap_pair(
        "Electrical_Cable", cable_desc_and_specs,
        (random.choice(CABLE_CONDS), random.choice(CABLE_SIZES),
         random.choice(CABLE_VOLTS), random.choice(CABLE_CORES),
         random.choice(CABLE_STD)),
        random.choice(["spec_conductor_size", "spec_voltage_rating", "spec_core_count"])
    )

# 15 true negatives (unrelated materials)
for _ in range(5):
    mat = random.choice(PIPE_MATS)
    add_negative(
        "Pipes", pipe_desc_and_specs,
        mat[0], mat[1], mat[2], random.choice(PIPE_DIAS),
        random.choice(PIPE_PRS), random.choice(PIPE_SCH), random.choice(PIPE_STD),
        random.choice(["2.77mm", "3.4mm", "4.0mm", "5.5mm", "7.1mm"]),
        random.choice(["Light", "Medium", "Heavy"])
    )
for _ in range(5):
    mat = random.choice(BOLT_MATS)
    add_negative(
        "Fasteners", bolt_desc_and_specs,
        mat[0], mat[1], mat[2], random.choice(BOLT_SIZES),
        random.choice(BOLT_LEN), random.choice(BOLT_STD)
    )
for _ in range(5):
    add_negative(
        "Electrical_Cable", cable_desc_and_specs,
        random.choice(CABLE_CONDS), random.choice(CABLE_SIZES),
        random.choice(CABLE_VOLTS), random.choice(CABLE_CORES),
        random.choice(CABLE_STD)
    )

# Shuffle rows so CPSEs are mixed
random.shuffle(rows)

# Write CSV
fieldnames = ["cpse_name", "original_code", "description", "category"] + ALL_SPECS
out_csv = OUT_DIR / "synthetic_data.csv"
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Write ground truth
out_gt = OUT_DIR / "ground_truth.csv"
with open(out_gt, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["cpse_a", "code_a", "cpse_b", "code_b", "should_match"])
    for ca, coa, cb, cob, sm in gt:
        writer.writerow([ca, coa, cb, cob, str(sm).lower()])

pos = sum(1 for *_, m in gt if m)
neg = sum(1 for *_, m in gt if not m)
print(f"Wrote {len(rows)} rows -> {out_csv}")
print(f"Wrote {len(gt)} ground-truth pairs -> {out_gt}")
print(f"  True duplicates : {pos}")
print(f"  Near-dup traps  : {neg}")
