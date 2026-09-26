-- Support the simplified lexicon learning loop:
-- count how many times a term pair has been suggested from approved matches
-- before an admin activates it.
ALTER TABLE lexicon_entries
    ADD COLUMN IF NOT EXISTS suggestion_count INT DEFAULT 0;
