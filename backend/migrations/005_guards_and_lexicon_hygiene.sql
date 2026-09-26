-- Additive, idempotent guards. Safe on existing databases and on fresh 001→005 runs.

-- Skip noisy unit expansions in the text lexicon (unit conversion belongs in spec parsers).
DELETE FROM lexicon_entries
WHERE status = 'active'
  AND raw_term IN ('mm', 'cm', 'm', 'in', 'qty', 'wt', 'temp', 'sq');

-- Prevent duplicate master rows for the same CPSE code (no-op if duplicates already exist).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM cpse_materials
        GROUP BY cpse_name, original_code
        HAVING COUNT(*) > 1
    ) THEN
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cpse_material_code
            ON cpse_materials (cpse_name, original_code);
    END IF;
END $$;

-- One evaluated pair per unordered material pair.
CREATE UNIQUE INDEX IF NOT EXISTS uq_material_match_pair
    ON material_matches (
        LEAST(material_a_id, material_b_id),
        GREATEST(material_a_id, material_b_id)
    );
