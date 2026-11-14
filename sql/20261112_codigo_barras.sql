-- Executar ANTES de iniciar/deployar a API atualizada. Pode executar novamente.
BEGIN;
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS codigo_barras VARCHAR(64);
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'produtos_adega_codigo_barras_key' AND conrelid = 'produtos'::regclass) THEN
        ALTER TABLE produtos ADD CONSTRAINT produtos_adega_codigo_barras_key UNIQUE (adega_id, codigo_barras);
    END IF;
END $$;
COMMIT;
