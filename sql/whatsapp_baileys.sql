-- Execute este arquivo uma única vez no PostgreSQL da aplicação.

CREATE TABLE IF NOT EXISTS whatsapp_sessoes (
    id BIGSERIAL PRIMARY KEY,
    adega_id INTEGER NOT NULL REFERENCES adegas(id) ON DELETE CASCADE,
    telefone VARCHAR(20),
    nome_dispositivo VARCHAR(100) NOT NULL DEFAULT 'Adega App - Baileys',
    status VARCHAR(30) NOT NULL DEFAULT 'desconectado',
    conectado_em TIMESTAMPTZ,
    desconectado_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_whatsapp_sessao_adega UNIQUE (adega_id),
    CONSTRAINT ck_whatsapp_sessao_status CHECK (
        status IN ('desconectado', 'aguardando_qr', 'conectando', 'conectado', 'erro')
    )
);

CREATE TABLE IF NOT EXISTS whatsapp_chaves (
    id BIGSERIAL PRIMARY KEY,
    adega_id INTEGER NOT NULL REFERENCES adegas(id) ON DELETE CASCADE,
    key_type VARCHAR(100) NOT NULL,
    key_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_whatsapp_chave_adega_tipo_id UNIQUE (adega_id, key_type, key_id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_chaves_adega
    ON whatsapp_chaves (adega_id);

CREATE INDEX IF NOT EXISTS idx_whatsapp_chaves_busca
    ON whatsapp_chaves (adega_id, key_type);

CREATE TABLE IF NOT EXISTS whatsapp_mensagens (
    id BIGSERIAL PRIMARY KEY,
    adega_id INTEGER NOT NULL REFERENCES adegas(id) ON DELETE CASCADE,
    debito_id INTEGER REFERENCES debitos_clientes(id) ON DELETE SET NULL,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    telefone VARCHAR(20) NOT NULL,
    mensagem TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pendente',
    message_id VARCHAR(255),
    detalhes_erro TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    enviado_em TIMESTAMPTZ,
    CONSTRAINT ck_whatsapp_mensagem_status
        CHECK (status IN ('pendente', 'enviando', 'enviado', 'erro'))
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_mensagens_adega
    ON whatsapp_mensagens (adega_id, criado_em DESC);

-- Registro inicial para o primeiro teste. Não são inseridas chaves fictícias:
-- a Baileys gravará as credenciais reais depois da leitura do QR Code.
INSERT INTO whatsapp_sessoes (adega_id, nome_dispositivo, status)
SELECT 1, 'Adega 1 - Baileys', 'desconectado'
WHERE EXISTS (SELECT 1 FROM adegas WHERE id = 1)
ON CONFLICT (adega_id) DO UPDATE SET
    nome_dispositivo = EXCLUDED.nome_dispositivo,
    atualizado_em = NOW();
