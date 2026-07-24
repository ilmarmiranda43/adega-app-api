import express from 'express';
import pino from 'pino';
import QRCodeImage from 'qrcode';
import QRCodeTerminal from 'qrcode-terminal';
import pg from 'pg';
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import { usePostgresAuthState } from './auth_postgres.js';

const { Pool } = pg;
const app = express();
app.use(express.json({ limit: '1mb' }));

const PORT = Number(process.env.PORT || 3001);
const API_KEY = process.env.BAILEYS_API_KEY;
const DATABASE_URL = process.env.DATABASE_URL;
const QR_WAIT_TIMEOUT_MS = Number(process.env.QR_WAIT_TIMEOUT_MS || 12000);
const RECONNECT_DELAY_MS = Number(process.env.RECONNECT_DELAY_MS || 5000);

if (!API_KEY) throw new Error('BAILEYS_API_KEY não configurada.');
if (!DATABASE_URL) throw new Error('DATABASE_URL não configurada.');

const pool = new Pool({
  connectionString: DATABASE_URL,
  ssl: DATABASE_URL.includes('localhost')
    ? false
    : { rejectUnauthorized: false }
});

const sessoes = new Map();
const conexoesEmAndamento = new Map();
const timersReconexao = new Map();

let servidor;
let encerrando = false;

function autenticar(req, res, next) {
  if (req.get('X-API-Key') !== API_KEY) {
    return res.status(401).json({
      ok: false,
      erro: 'API key inválida.'
    });
  }

  next();
}

function validarAdegaId(valor) {
  const adegaId = Number(valor);
  return Number.isInteger(adegaId) && adegaId > 0 ? adegaId : null;
}

function normalizarTelefone(valor) {
  let telefone = String(valor || '').replace(/\D/g, '');

  if (telefone.length === 10 || telefone.length === 11) {
    telefone = `55${telefone}`;
  }

  return telefone;
}

async function adegaExiste(adegaId) {
  const resultado = await pool.query(
    'SELECT 1 FROM adegas WHERE id = $1',
    [adegaId]
  );

  return resultado.rowCount > 0;
}

async function atualizarStatus(adegaId, status, telefone = null) {
  await pool.query(
    `INSERT INTO whatsapp_sessoes (adega_id, telefone, status)
     VALUES ($1, $2, $3)
     ON CONFLICT (adega_id) DO UPDATE SET
       telefone = COALESCE(EXCLUDED.telefone, whatsapp_sessoes.telefone),
       status = EXCLUDED.status,
       conectado_em = CASE
         WHEN EXCLUDED.status = 'conectado' THEN NOW()
         ELSE whatsapp_sessoes.conectado_em
       END,
       desconectado_em = CASE
         WHEN EXCLUDED.status = 'desconectado' THEN NOW()
         ELSE whatsapp_sessoes.desconectado_em
       END,
       atualizado_em = NOW()`,
    [adegaId, telefone, status]
  );
}

async function atualizarStatusSeguro(adegaId, status, telefone = null) {
  try {
    await atualizarStatus(adegaId, status, telefone);
  } catch (erro) {
    console.error(
      `Não foi possível atualizar o status da adega ${adegaId}:`,
      erro
    );
  }
}

async function limparCredenciais(adegaId) {
  await pool.query(
    'DELETE FROM whatsapp_chaves WHERE adega_id = $1',
    [adegaId]
  );
}

function cancelarReconexao(adegaId) {
  const timer = timersReconexao.get(adegaId);

  if (timer) {
    clearTimeout(timer);
    timersReconexao.delete(adegaId);
  }
}

function agendarReconexao(adegaId) {
  if (encerrando || timersReconexao.has(adegaId)) {
    return;
  }

  const timer = setTimeout(async () => {
    timersReconexao.delete(adegaId);

    try {
      await conectarAdega(adegaId);
    } catch (erro) {
      await atualizarStatusSeguro(adegaId, 'erro');
      console.error(`Erro ao reconectar a adega ${adegaId}:`, erro);
    }
  }, RECONNECT_DELAY_MS);

  timersReconexao.set(adegaId, timer);
}

function codigoDesconexao(lastDisconnect) {
  const erro = lastDisconnect?.error;

  if (!erro) {
    return DisconnectReason.connectionClosed;
  }

  return erro?.output?.statusCode ?? new Boom(erro).output.statusCode;
}

function respostaQr(sessao) {
  const conectado = Boolean(sessao?.conectado && sessao?.sock);
  const qrCode = sessao?.qrDataUrl || null;

  let status = sessao?.status || 'desconectado';

  if (conectado) {
    status = 'conectado';
  } else if (qrCode) {
    status = 'aguardando_qr';
  }

  return {
    ok: true,
    conectado,
    status,
    qr_code: qrCode,
    // Mantém compatibilidade com frontends que usam camelCase.
    qrCode
  };
}

async function processarAtualizacaoConexao(
  adegaId,
  sessao,
  sock,
  { connection, lastDisconnect, qr }
) {
  if (qr) {
    sessao.conectado = false;
    sessao.status = 'aguardando_qr';
    sessao.qrDisponivel = true;
    sessao.qrDataUrl = await QRCodeImage.toDataURL(qr, {
      width: 350,
      margin: 2,
      errorCorrectionLevel: 'M'
    });

    await atualizarStatusSeguro(adegaId, 'aguardando_qr');

    console.log(`\nQR Code da adega ${adegaId}:`);
    QRCodeTerminal.generate(qr, { small: true });
  }

  if (connection === 'open') {
    cancelarReconexao(adegaId);

    sessao.conectado = true;
    sessao.status = 'conectado';
    sessao.qrDisponivel = false;
    sessao.qrDataUrl = null;

    const telefone =
      sock.user?.id?.split(':')[0]?.split('@')[0] || null;

    await atualizarStatusSeguro(adegaId, 'conectado', telefone);
    console.log(`Adega ${adegaId}: WhatsApp conectado.`);
  }

  if (connection !== 'close') {
    return;
  }

  const codigo = codigoDesconexao(lastDisconnect);

  sessao.conectado = false;
  sessao.status = 'desconectado';
  sessao.qrDisponivel = false;
  sessao.qrDataUrl = null;

  await atualizarStatusSeguro(adegaId, 'desconectado');

  const credenciaisInvalidas = [
    DisconnectReason.loggedOut,
    DisconnectReason.badSession,
    DisconnectReason.multideviceMismatch,
    DisconnectReason.forbidden
  ].includes(codigo);

  if (credenciaisInvalidas) {
    cancelarReconexao(adegaId);
    sessao.status = 'conectando';
    sessao.descartada = true;
    let credenciaisRemovidas = false;

    try {
      await limparCredenciais(adegaId);
      credenciaisRemovidas = true;
    } catch (erro) {
      console.error(
        `Não foi possível remover as credenciais inválidas da adega ${adegaId}:`,
        erro
      );
    }

    if (sessoes.get(adegaId) === sessao) {
      sessoes.delete(adegaId);
    }

    console.log(
      `Adega ${adegaId}: sessão inválida ou desconectada; um novo QR Code será necessário.`
    );

    if (credenciaisRemovidas) {
      agendarReconexao(adegaId);
    } else {
      await atualizarStatusSeguro(adegaId, 'erro');
    }

    return;
  }

  if (sessoes.get(adegaId) === sessao) {
    sessoes.delete(adegaId);
  }

  if (codigo === DisconnectReason.connectionReplaced) {
    cancelarReconexao(adegaId);
    console.log(
      `Adega ${adegaId}: conexão substituída por outra instância.`
    );
    return;
  }

  console.log(
    `Adega ${adegaId}: conexão encerrada (código ${codigo}); reconectando.`
  );
  agendarReconexao(adegaId);
}

async function conectarAdega(adegaId) {
  const atual = sessoes.get(adegaId);

  if (
    atual?.sock &&
    ['conectando', 'aguardando_qr', 'conectado'].includes(atual.status)
  ) {
    return atual;
  }

  if (conexoesEmAndamento.has(adegaId)) {
    return conexoesEmAndamento.get(adegaId);
  }

  cancelarReconexao(adegaId);

  const promessa = (async () => {
    await atualizarStatus(adegaId, 'conectando');

    const { state, saveCreds } = await usePostgresAuthState(pool, adegaId);
    const { version, isLatest } = await fetchLatestBaileysVersion();

    if (!isLatest) {
      console.warn(
        'Não foi possível consultar a versão mais recente do WhatsApp; usando a versão incluída no Baileys.'
      );
    }

    const sessao = {
      sock: null,
      conectado: false,
      status: 'conectando',
      qrDisponivel: false,
      qrDataUrl: null,
      descartada: false
    };

    const sock = makeWASocket({
      version,
      auth: state,
      logger: pino({ level: 'silent' }),
      browser: [`Adega ${adegaId}`, 'Chrome', '1.0.0'],
      markOnlineOnConnect: false,
      syncFullHistory: false
    });

    sessao.sock = sock;
    sessoes.set(adegaId, sessao);

    sock.ev.on('creds.update', () => {
      if (sessao.descartada) {
        return;
      }

      void saveCreds().catch((erro) => {
        console.error(
          `Não foi possível salvar as credenciais da adega ${adegaId}:`,
          erro
        );
      });
    });

    sock.ev.on('connection.update', (atualizacao) => {
      void processarAtualizacaoConexao(
        adegaId,
        sessao,
        sock,
        atualizacao
      ).catch(async (erro) => {
        sessao.status = 'erro';
        await atualizarStatusSeguro(adegaId, 'erro');
        console.error(
          `Erro ao processar a conexão da adega ${adegaId}:`,
          erro
        );
      });
    });

    return sessao;
  })().catch(async (erro) => {
    sessoes.delete(adegaId);
    await atualizarStatusSeguro(adegaId, 'erro');
    throw erro;
  }).finally(() => {
    conexoesEmAndamento.delete(adegaId);
  });

  conexoesEmAndamento.set(adegaId, promessa);
  return promessa;
}

async function aguardarQrOuConexao(adegaId, timeoutMs = QR_WAIT_TIMEOUT_MS) {
  const inicio = Date.now();

  while (Date.now() - inicio < timeoutMs) {
    const sessao = sessoes.get(adegaId);

    if (
      sessao?.conectado ||
      sessao?.qrDataUrl ||
      sessao?.status === 'erro'
    ) {
      return sessao;
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  return sessoes.get(adegaId) || null;
}

async function aguardarConexao(adegaId, timeoutMs = 20000) {
  const inicio = Date.now();

  while (Date.now() - inicio < timeoutMs) {
    const sessao = sessoes.get(adegaId);

    if (sessao?.conectado && sessao?.sock) {
      return sessao;
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  return null;
}

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.get('/sessions/:adega_id/status', autenticar, async (req, res) => {
  const adegaId = validarAdegaId(req.params.adega_id);

  if (!adegaId) {
    return res.status(400).json({
      ok: false,
      erro: 'adega_id inválido.'
    });
  }

  const resultado = await pool.query(
    `SELECT adega_id, telefone, status, atualizado_em
       FROM whatsapp_sessoes
      WHERE adega_id = $1`,
    [adegaId]
  );

  const banco = resultado.rows[0] || null;
  const runtime = respostaQr(sessoes.get(adegaId));

  return res.json({
    ...runtime,
    status_banco: banco?.status || null,
    sessao: banco
      ? {
          ...banco,
          status: runtime.status
        }
      : null
  });
});

app.post('/sessions/:adega_id/connect', autenticar, async (req, res) => {
  const adegaId = validarAdegaId(req.params.adega_id);

  if (!adegaId) {
    return res.status(400).json({
      ok: false,
      erro: 'adega_id inválido.'
    });
  }

  if (!(await adegaExiste(adegaId))) {
    return res.status(404).json({
      ok: false,
      erro: 'Adega não encontrada.'
    });
  }

  await conectarAdega(adegaId);
  const sessao = await aguardarQrOuConexao(adegaId);
  const resposta = respostaQr(sessao);
  const pronto = resposta.conectado || Boolean(resposta.qr_code);

  return res.status(pronto ? 200 : 202).json({
    ...resposta,
    mensagem: resposta.conectado
      ? `WhatsApp da adega ${adegaId} conectado.`
      : resposta.qr_code
        ? 'QR Code gerado. Leia-o no WhatsApp para conectar.'
        : 'Conexão iniciada; o QR Code ainda está sendo gerado.'
  });
});

app.get('/sessions/:adega_id/qr', autenticar, async (req, res) => {
  const adegaId = validarAdegaId(req.params.adega_id);

  if (!adegaId) {
    return res.status(400).json({
      ok: false,
      erro: 'adega_id inválido.'
    });
  }

  if (!(await adegaExiste(adegaId))) {
    return res.status(404).json({
      ok: false,
      erro: 'Adega não encontrada.'
    });
  }

  // O endpoint também inicia a sessão. Assim, o frontend não fica preso em
  // "desconectado" caso a chamada POST /connect não tenha sido feita.
  await conectarAdega(adegaId);

  const sessao = await aguardarQrOuConexao(adegaId);
  const resposta = respostaQr(sessao);
  const pronto = resposta.conectado || Boolean(resposta.qr_code);

  return res.status(pronto ? 200 : 202).json(resposta);
});

app.post('/send', autenticar, async (req, res) => {
  try {
    const adegaId = validarAdegaId(req.body.adega_id);
    const telefone = normalizarTelefone(req.body.telefone);
    const mensagem = String(req.body.mensagem || '').trim();

    if (!adegaId || !telefone || !mensagem) {
      return res.status(400).json({
        ok: false,
        erro: 'adega_id, telefone e mensagem são obrigatórios.'
      });
    }

    let sessao = sessoes.get(adegaId);

    if (!sessao?.conectado || !sessao?.sock) {
      await conectarAdega(adegaId);
      sessao = await aguardarConexao(adegaId);
    }

    if (!sessao?.conectado || !sessao?.sock) {
      return res.status(503).json({
        ok: false,
        erro:
          `Não foi possível conectar o WhatsApp da adega ${adegaId}. ` +
          'Abra a área de conexão e leia o QR Code, se solicitado.'
      });
    }

    const consultado = `${telefone}@s.whatsapp.net`;
    const contas = await sessao.sock.onWhatsApp(consultado);
    const conta = contas?.find((item) => item.exists);

    if (!conta) {
      return res.status(404).json({
        ok: false,
        erro: 'Número não encontrado no WhatsApp.'
      });
    }

    const envio = await sessao.sock.sendMessage(conta.jid, {
      text: mensagem
    });

    return res.json({
      ok: true,
      adega_id: adegaId,
      telefone,
      jid: conta.jid,
      message_id: envio?.key?.id || null
    });
  } catch (erro) {
    console.error(erro);
    return res.status(500).json({
      ok: false,
      erro: erro.message || 'Erro ao enviar mensagem.'
    });
  }
});

app.use((erro, _req, res, next) => {
  console.error('Erro no serviço Baileys:', erro);

  if (res.headersSent) {
    return next(erro);
  }

  res.status(500).json({
    ok: false,
    erro: erro.message || 'Erro interno no serviço Baileys.'
  });
});

async function iniciarServico() {
  try {
    await pool.query(
      `UPDATE whatsapp_sessoes
          SET status = 'desconectado',
              atualizado_em = NOW()
        WHERE status IN ('conectado', 'conectando', 'aguardando_qr')`
    );

    const resultado = await pool.query(
      `SELECT DISTINCT adega_id
         FROM whatsapp_chaves
        WHERE key_type = 'creds'
          AND key_id = 'creds'
        ORDER BY adega_id`
    );

    servidor = app.listen(PORT, '0.0.0.0', () => {
      console.log(`Serviço Baileys disponível na porta ${PORT}.`);
    });

    for (const row of resultado.rows) {
      const adegaId = Number(row.adega_id);

      console.log(`Restaurando sessão da adega ${adegaId}...`);

      try {
        await conectarAdega(adegaId);
      } catch (erro) {
        await atualizarStatusSeguro(adegaId, 'erro');
        console.error(`Erro ao restaurar a adega ${adegaId}:`, erro);
      }
    }
  } catch (erro) {
    console.error('Erro ao iniciar serviço Baileys:', erro);
    process.exitCode = 1;
  }
}

async function encerrarServico(sinal) {
  if (encerrando) {
    return;
  }

  encerrando = true;
  console.log(`Encerrando serviço Baileys (${sinal})...`);

  for (const adegaId of timersReconexao.keys()) {
    cancelarReconexao(adegaId);
  }

  const finalizar = async () => {
    try {
      await pool.end();
    } finally {
      process.exit(0);
    }
  };

  if (servidor) {
    servidor.close(() => {
      void finalizar();
    });
  } else {
    await finalizar();
  }
}

process.once('SIGTERM', () => {
  void encerrarServico('SIGTERM');
});

process.once('SIGINT', () => {
  void encerrarServico('SIGINT');
});

void iniciarServico();
