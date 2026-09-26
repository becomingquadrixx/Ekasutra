DROP TABLE IF EXISTS code_aliases CASCADE;
DROP TABLE IF EXISTS cnmc_registry CASCADE;
DROP TABLE IF EXISTS material_matches CASCADE;
DROP TABLE IF EXISTS category_specs CASCADE;
DROP TABLE IF EXISTS lexicon_entries CASCADE;
DROP TABLE IF EXISTS cpse_materials CASCADE;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE cpse_materials (
    id SERIAL PRIMARY KEY,
    cpse_name TEXT NOT NULL,
    original_code TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    raw_specs JSONB,
    normalized_description TEXT,
    category TEXT,
    embedding VECTOR(1024),
    ingested_at TIMESTAMP DEFAULT now()
);

CREATE TABLE lexicon_entries (
    id SERIAL PRIMARY KEY,
    raw_term TEXT NOT NULL,
    canonical_term TEXT NOT NULL,
    status TEXT CHECK (status IN ('active','proposed','rejected')) DEFAULT 'active',
    proposed_by TEXT,
    approved_by TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE category_specs (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    spec_name TEXT NOT NULL,
    spec_type TEXT CHECK (spec_type IN ('critical','soft','irrelevant')) NOT NULL
);

CREATE TABLE material_matches (
    id SERIAL PRIMARY KEY,
    material_a_id INT REFERENCES cpse_materials(id),
    material_b_id INT REFERENCES cpse_materials(id),
    semantic_score FLOAT,
    spec_agreement JSONB,
    override_triggered BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    decision_level TEXT CHECK (decision_level IN ('exact','functional_equivalent','similar_substitute','rejected')),
    status TEXT CHECK (status IN ('pending_review','approved','rejected')) DEFAULT 'pending_review',
    reviewed_by TEXT,
    reviewed_at TIMESTAMP
);

CREATE TABLE cnmc_registry (
    id SERIAL PRIMARY KEY,
    cnmc_code TEXT UNIQUE NOT NULL,
    canonical_description TEXT,
    category TEXT,
    status TEXT CHECK (status IN ('confirmed','unconfirmed')) DEFAULT 'unconfirmed',
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE code_aliases (
    id SERIAL PRIMARY KEY,
    cpse_material_id INT REFERENCES cpse_materials(id),
    cnmc_id INT REFERENCES cnmc_registry(id),
    mapped_at TIMESTAMP DEFAULT now(),
    flagged_for_review BOOLEAN DEFAULT FALSE
);

INSERT INTO category_specs (category, spec_name, spec_type) VALUES
    ('Pipes', 'diameter', 'critical'),
    ('Pipes', 'pressure_rating', 'critical'),
    ('Pipes', 'material_grade', 'critical'),
    ('Pipes', 'wall_thickness', 'critical'),
    ('Pipes', 'length', 'soft'),
    ('Pipes', 'surface_finish', 'soft'),
    ('Pipes', 'packaging', 'irrelevant'),
    ('Pipes', 'batch_number', 'irrelevant'),
    ('Pipes', 'color', 'irrelevant'),
    ('Fasteners', 'thread_size_pitch', 'critical'),
    ('Fasteners', 'strength_grade', 'critical'),
    ('Fasteners', 'material', 'critical'),
    ('Fasteners', 'bolt_length', 'critical'),
    ('Fasteners', 'head_type', 'soft'),
    ('Fasteners', 'coating_color', 'irrelevant'),
    ('Fasteners', 'pack_quantity', 'irrelevant'),
    ('Electrical_Cable', 'conductor_size', 'critical'),
    ('Electrical_Cable', 'voltage_rating', 'critical'),
    ('Electrical_Cable', 'core_count', 'critical'),
    ('Electrical_Cable', 'insulation_color_code', 'soft'),
    ('Electrical_Cable', 'manufacturer_brand', 'soft'),
    ('Electrical_Cable', 'reel_length', 'irrelevant'),
    ('Electrical_Cable', 'packaging', 'irrelevant');
