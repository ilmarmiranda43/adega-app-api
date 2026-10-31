-- Executar SOMENTE no banco de homologação, com backup prévio.
-- Não modifica as tabelas adequas/usuarios existentes.
CREATE TABLE IF NOT EXISTS adega_trials (
    adega_id INTEGER PRIMARY KEY REFERENCES adegas(id) ON DELETE CASCADE,
    ativo BOOLEAN NOT NULL DEFAULT FALSE,
    dias INTEGER NOT NULL DEFAULT 7 CHECK (dias BETWEEN 1 AND 365),
    iniciado_em TIMESTAMPTZ NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
