
-- Administração global da plataforma IMBEBI
-- Executar somente no banco adegas_teste

BEGIN;

ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS is_platform_admin
BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
