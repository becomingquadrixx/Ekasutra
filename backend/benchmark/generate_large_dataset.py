"""
Generates a large synthetic CPSE-style dataset for demo/benchmarking.
Covers 5 categories: Pipes, Fasteners, Electrical_Cable, Valves, Instruments
Outputs large_demo_data.csv to the benchmark folder.
"""

import csv
import random
from pathlib import Path

random.seed(2026)
OUT_DIR = Path(__file__).parent

CPSE_POOL = [
    ("ONGC",), ("NTPC",), ("BHEL",), ("IOCL",), ("GAIL",),
    ("SAIL",), ("CIL",), ("BPCL",), ("HPCL",), ("PGCIL",),
    ("NLCIL",), ("NMDC",), ("RINL",), ("NALCO",), ("HAL",), ("CPCL",),
]

def code_for(cpse, seq):
    m = {"ONGC": f"MM-{45000+seq:05d}", "NTPC": f"MAT-{seq:06d}", "BHEL": f"BHE/DPW/{seq:05d}",
         "IOCL": f"IOCL/REF/{seq:05d}", "GAIL": f"GAIL/PIPE/{seq:05d}", "SAIL": f"SAIL/MSP/{seq:05d}",
         "CIL": f"CIL/SP/{seq:05d}", "BPCL": f"BPCL/KOCHI/{seq:05d}", "HPCL": f"HPCL/VZ/{seq:05d}",
         "PGCIL": f"PGCIL/TL/{seq:05d}", "NLCIL": f"NLC/PW/{seq:05d}", "NMDC": f"NMDC/ME/{seq:05d}",
         "RINL": f"RINL/VSP/{seq:05d}", "NALCO": f"NALCO/AL/{seq:05d}", "HAL": f"HAL/MRO/{seq:05d}",
         "CPCL": f"CPCL/CH/{seq:05d}"}
    return m.get(cpse, f"{cpse}/{seq:05d}")

PIPE_TEMPLATES = [
    "{mat} ERW Pipe NB {dia} {sch} as per {std}",
    "{mat} Seamless Pipe OD {dia} WT {wt} {std}",
    "{mat} Pipe {dia} NB {cls} Class {std}",
    "{std} {mat} Pipe {dia} Sch {sch} SMLS",
    "Pipe {mat} {dia} x {wt} {std} HSN-7304",
    "{mat} Pipe NB {dia} Schedule {sch} {std} Seamless",
    "ERW {mat} Line Pipe {dia} {sch} {std}",
]
PIPE_MATS = [
    ("MS","Mild Steel","A106 Gr B"),("CS","Carbon Steel","A53 Gr B"),
    ("SS","Stainless Steel","304"),("SS316","Stainless Steel 316","316"),
    ("GI","Galvanized Iron","IS 1239"),("Alloy Steel","Alloy Steel","P11"),
    ("Duplex SS","Duplex Stainless Steel","2205"),
]
PIPE_DIAS = ["15mm","20mm","25mm","32mm","40mm","50mm","65mm","80mm","100mm","150mm","200mm","250mm","300mm"]
PIPE_PRS  = ["150 psi","300 psi","600 psi","900 psi","1500 psi","2500 psi"]
PIPE_SCH  = ["10","20","40","80","120","160","XXS"]
PIPE_STD  = ["IS 1239","ASTM A106","ASTM A53","IS 3589","DIN 2448","API 5L","IS 1161"]
PIPE_WTS  = ["2.77mm","3.4mm","4.0mm","5.5mm","7.1mm","8.6mm","10.0mm"]
PIPE_CLS  = ["Light","Medium","Heavy"]

def pipe_fn(mat_short, mat_long, grade, dia, pr, sch, std, wt, cls):
    t = random.choice(PIPE_TEMPLATES)
    desc = t.format(mat=mat_short, dia=dia, sch=sch, std=std, wt=wt, cls=cls)
    return desc, {"spec_diameter": dia, "spec_pressure_rating": pr, "spec_material_grade": grade,
                  "spec_length": random.choice(["6m","5.8m","3m","12m"]),
                  "spec_surface_finish": random.choice(["Bare","Galvanized","Painted","Epoxy Coated"]),
                  "spec_wall_thickness": wt}

BOLT_TEMPLATES = [
    "Hex Bolt {sz}x{len} LG {mat} {grade} {std}",
    "Hex Hd Bolt {sz} x {len} {mat} {grade}",
    "Bolt {std} {sz}x{len} {mat} {grade} Full Thread",
    "{mat} Hex Bolt {sz} x {len} {grade} {std}",
    "Stud Bolt {sz} x {len} {grade} {std} {mat}",
]
BOLT_SIZES  = ["M6","M8","M10","M12","M16","M20","M24","M30","M36"]
BOLT_PITCH  = {"M6":"1.0mm","M8":"1.25mm","M10":"1.5mm","M12":"1.75mm",
               "M16":"2.0mm","M20":"2.5mm","M24":"3.0mm","M30":"3.5mm","M36":"4.0mm"}
BOLT_LEN    = ["25mm","30mm","40mm","50mm","60mm","80mm","100mm","120mm","150mm"]
BOLT_MATS   = [("MS","Mild Steel","8.8"),("CS","Carbon Steel","4.6"),
               ("SS","Stainless Steel","A2-70"),("SS316","Stainless Steel 316","A4-80"),
               ("GI","Galvanized Iron","4.6"),("B7","Alloy Steel","B7"),("SS304","Stainless Steel 304","A2-80")]
BOLT_GRADES = ["4.6","5.8","8.8","10.9","12.9","A2-70","A4-80","B7","A2-80"]
BOLT_STD    = ["DIN 933","IS 1364","ISO 4017","ASTM A193","ASME B18.2.1"]

def bolt_fn(mat_short, mat_long, grade, sz, blen, std):
    t = random.choice(BOLT_TEMPLATES)
    desc = t.format(sz=sz, len=blen, mat=mat_short, grade=grade, std=std)
    return desc, {"spec_thread_size_pitch": f"{sz} x {BOLT_PITCH[sz]}", "spec_strength_grade": grade,
                  "spec_material": mat_long, "spec_head_type": random.choice(["Hex Head","Socket Head","Flange Head"]),
                  "spec_bolt_length": blen}

CABLE_TEMPLATES = [
    "{cond} {size} {core}C {volt} XLPE {std}",
    "{size} {cond} Cable {core} Core {volt} {std}",
    "HT Cable {volt} {size} {core}C XLPE {cond}",
    "{cond} Conductor Cable {size} {core} Core {volt} Armoured",
    "PVC Insulated {cond} Wire {size} {volt} {std}",
    "XLPE/SWA/PVC {cond} Cable {size} {core}C {volt} {std}",
]
CABLE_SIZES = ["1.5mm2","2.5mm2","4mm2","6mm2","10mm2","16mm2","25mm2","35mm2",
               "50mm2","70mm2","95mm2","120mm2","185mm2","240mm2","300mm2"]
CABLE_VOLTS = ["650V","1100V","3.3kV","6.6kV","11kV","33kV"]
CABLE_CORES = ["1","2","3","3.5","4"]
CABLE_CONDS = ["Cu","Al","Copper","Aluminium"]
CABLE_STD   = ["IS 7098","IS 694","IS 1554","IEC 60502","IS 1554 Part 2"]

def cable_fn(cond, size, volt, core, std):
    t = random.choice(CABLE_TEMPLATES)
    desc = t.format(cond=cond, size=size, core=core, volt=volt, std=std)
    return desc, {"spec_conductor_size": size, "spec_voltage_rating": volt, "spec_core_count": core,
                  "spec_insulation_color_code": random.choice(["R-Y-B","Black","Red","Brown"])}

VALVE_TYPES     = ["Gate Valve","Ball Valve","Globe Valve","Check Valve","Butterfly Valve","Needle Valve","Control Valve"]
VALVE_TEMPLATES = [
    "{vtype} {dia} {cls} {mat} {end} {std}",
    "{mat} {vtype} {dia} Class {cls} {end} {std}",
    "{vtype} NB {dia} {cls} Lb {mat} flanged {std}",
    "{std} {mat} {vtype} {dia} {cls} {end}",
    "{mat} {vtype} {cls}# {dia} RF ends {std}",
]
VALVE_DIAS  = ["15mm","25mm","40mm","50mm","80mm","100mm","150mm","200mm","250mm","300mm"]
VALVE_MATS  = [("CS","Carbon Steel","A216 WCB"),("SS316","Stainless Steel 316","CF8M"),
               ("CI","Cast Iron","IS 210 Gr FG200"),("Alloy Steel","Alloy Steel","WC6"),
               ("Duplex SS","Duplex Stainless Steel","CD4MCu")]
VALVE_CLASS = ["150","300","600","900","1500"]
VALVE_ENDS  = ["Flanged RF","Butt Weld","Socket Weld","Screwed NPT","Wafer"]
VALVE_STD   = ["API 600","API 6D","BS 1414","IS 778","ASME B16.34"]

def valve_fn(vtype, mat_short, mat_long, grade, dia, cls, end, std):
    t = random.choice(VALVE_TEMPLATES)
    desc = t.format(vtype=vtype, mat=mat_short, dia=dia, cls=cls, end=end, std=std)
    return desc, {"spec_diameter": dia, "spec_pressure_rating": f"Class {cls}", "spec_material_grade": grade,
                  "spec_end_connection": end, "spec_valve_class": cls,
                  "spec_surface_finish": random.choice(["Bare","Epoxy Coated","Galvanized"])}

INSTR_TEMPLATES = [
    "Pressure Gauge {range} {dial} {conn} {mat} {std}",
    "{dial} Pressure Gauge {range} {conn} {mat}",
    "Bourdon Tube Pressure Gauge {range} {dial} {conn} {std}",
    "Glycerin Filled Pressure Gauge {range} {dial} {conn} {mat}",
    "Pressure Transmitter {range} {accuracy} {conn} {std}",
]
INSTR_RANGES    = ["0-10 bar","0-25 bar","0-40 bar","0-60 bar","0-100 bar","0-160 bar","0-250 bar","-1 to 0 bar","0-6 bar"]
INSTR_DIALS     = ["100mm","150mm","63mm","250mm"]
INSTR_CONNS     = ["1/2\" NPT","1/4\" NPT","3/8\" NPT","1/2\" BSP"]
INSTR_MATS      = ["SS304","SS316","CS","Bronze"]
INSTR_ACCURACY  = ["Class 1.0","Class 1.6","Class 0.5","Class 2.5"]
INSTR_STD       = ["IS 3624","EN 837-1","ASME B40.100"]

def instr_fn(range_, dial, conn, mat, accuracy, std):
    t = random.choice(INSTR_TEMPLATES)
    desc = t.format(range=range_, dial=dial, conn=conn, mat=mat, accuracy=accuracy, std=std)
    return desc, {"spec_pressure_range": range_, "spec_accuracy_class": accuracy,
                  "spec_dial_size": dial, "spec_connection_type": conn, "spec_material_grade": mat}

ALL_SPECS = [
    "spec_diameter","spec_pressure_rating","spec_material_grade","spec_length","spec_surface_finish",
    "spec_wall_thickness","spec_thread_size_pitch","spec_strength_grade","spec_material","spec_head_type",
    "spec_bolt_length","spec_conductor_size","spec_voltage_rating","spec_core_count","spec_insulation_color_code",
    "spec_end_connection","spec_valve_class","spec_pressure_range","spec_accuracy_class","spec_dial_size","spec_connection_type",
]

rows = []
seq  = 5000

def next_pair():
    global seq
    a, b = random.sample(CPSE_POOL, 2)
    ca, cb = a[0], b[0]
    coa = code_for(ca, seq); seq += 1
    cob = code_for(cb, seq); seq += 1
    return ca, coa, cb, cob

def make_row(cpse, code, category, description, specs):
    row = {"cpse_name": cpse, "original_code": code, "description": description}
    for s in ALL_SPECS:
        row[s] = specs.get(s, "")
    row["category"] = category
    return row

def add_dup(category, fn, *args):
    ca, coa, cb, cob = next_pair()
    da, sa = fn(*args)
    db, sb = fn(*args)
    while db == da:
        db, sb = fn(*args)
    rows.append(make_row(ca, coa, category, da, sa))
    rows.append(make_row(cb, cob, category, db, sb))

def add_single(category, fn, *args):
    global seq
    cpse = random.choice(CPSE_POOL)[0]
    code = code_for(cpse, seq); seq += 1
    d, s = fn(*args)
    rows.append(make_row(cpse, code, category, d, s))

# Pipes: 60 dup pairs + 25 singles = 145 rows
for _ in range(60):
    m = random.choice(PIPE_MATS)
    add_dup("Pipes", pipe_fn, m[0], m[1], m[2],
        random.choice(PIPE_DIAS), random.choice(PIPE_PRS), random.choice(PIPE_SCH),
        random.choice(PIPE_STD), random.choice(PIPE_WTS), random.choice(PIPE_CLS))
for _ in range(25):
    m = random.choice(PIPE_MATS)
    add_single("Pipes", pipe_fn, m[0], m[1], m[2],
        random.choice(PIPE_DIAS), random.choice(PIPE_PRS), random.choice(PIPE_SCH),
        random.choice(PIPE_STD), random.choice(PIPE_WTS), random.choice(PIPE_CLS))

# Fasteners: 50 dup pairs + 20 singles = 120 rows
for _ in range(50):
    m = random.choice(BOLT_MATS)
    add_dup("Fasteners", bolt_fn, m[0], m[1], m[2],
        random.choice(BOLT_SIZES), random.choice(BOLT_LEN), random.choice(BOLT_STD))
for _ in range(20):
    m = random.choice(BOLT_MATS)
    add_single("Fasteners", bolt_fn, m[0], m[1], m[2],
        random.choice(BOLT_SIZES), random.choice(BOLT_LEN), random.choice(BOLT_STD))

# Electrical Cable: 50 dup pairs + 20 singles = 120 rows
for _ in range(50):
    add_dup("Electrical_Cable", cable_fn,
        random.choice(CABLE_CONDS), random.choice(CABLE_SIZES),
        random.choice(CABLE_VOLTS), random.choice(CABLE_CORES), random.choice(CABLE_STD))
for _ in range(20):
    add_single("Electrical_Cable", cable_fn,
        random.choice(CABLE_CONDS), random.choice(CABLE_SIZES),
        random.choice(CABLE_VOLTS), random.choice(CABLE_CORES), random.choice(CABLE_STD))

# Valves: 40 dup pairs + 15 singles = 95 rows
for _ in range(40):
    m = random.choice(VALVE_MATS)
    add_dup("Valves", valve_fn, random.choice(VALVE_TYPES), m[0], m[1], m[2],
        random.choice(VALVE_DIAS), random.choice(VALVE_CLASS),
        random.choice(VALVE_ENDS), random.choice(VALVE_STD))
for _ in range(15):
    m = random.choice(VALVE_MATS)
    add_single("Valves", valve_fn, random.choice(VALVE_TYPES), m[0], m[1], m[2],
        random.choice(VALVE_DIAS), random.choice(VALVE_CLASS),
        random.choice(VALVE_ENDS), random.choice(VALVE_STD))

# Instruments: 30 dup pairs + 15 singles = 75 rows
for _ in range(30):
    add_dup("Instruments", instr_fn,
        random.choice(INSTR_RANGES), random.choice(INSTR_DIALS), random.choice(INSTR_CONNS),
        random.choice(INSTR_MATS), random.choice(INSTR_ACCURACY), random.choice(INSTR_STD))
for _ in range(15):
    add_single("Instruments", instr_fn,
        random.choice(INSTR_RANGES), random.choice(INSTR_DIALS), random.choice(INSTR_CONNS),
        random.choice(INSTR_MATS), random.choice(INSTR_ACCURACY), random.choice(INSTR_STD))

random.shuffle(rows)

fieldnames = ["cpse_name","original_code","description","category"] + ALL_SPECS
out_csv = OUT_DIR / "large_demo_data.csv"
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

cats = {}
for r in rows:
    cats[r["category"]] = cats.get(r["category"], 0) + 1

print(f"Wrote {len(rows)} rows -> {out_csv}")
print("Breakdown by category:")
for cat, count in sorted(cats.items()):
    print(f"  {cat}: {count} materials")
