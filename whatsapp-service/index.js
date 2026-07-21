import express from 'express';
import pino from 'pino';
import QRCodeImage from "qrcode";
import QRCode from 'qrcode-terminal';
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

if (!API_KEY) throw new Error('BAILEYS_API_KEY não configurada.');
if (!DATABASE_URL) throw new Error('DATABASE_URL não configurada.');

const pool = new Pool({
  connectionString: DATABASE_URL,
  ssl: DATABASE_URL.includes('localhost') ? false : { rejectUnauthorized: false }
});

const sessoes = new Map();
const conexoesEmAndamento = new Map();
const timersReconexao = new Map();

function autenticar(req, res, next) {
  if (req.get('X-API-Key') !== API_KEY) {
    return res.status(401).json({ ok: false, erro: 'API key inválida.' });
  }
  next();
}

function validarAdegaId(valor) {
  const adegaId = Number(valor);
  return Number.isInteger(adegaId) && adegaId > 0 ? adegaId : null;
}

function normalizarTelefone(valor) {
  let telefone = String(valor || '').replace(/\D/g, '');
  if (telefone.length === 10 || telefone.length === 11) telefone = `55${telefone}`;
  return telefone;
}

async function atualizarStatus(adegaId, status, telefone = null) {
  await pool.query(
    `INSERT INTO whatsapp_sessoes (adega_id, telefone, status)
     VALUES ($1, $2, $3)
     ON CONFLICT (adega_id) DO UPDATE SET
       telefone = COALESCE(EXCLUDED.telefone, whatsapp_sessoes.telefone),
       status = EXCLUDED.status,
       conectado_em = CASE WHEN EXCLUDED.status = 'conectado' THEN NOW() ELSE whatsapp_sessoes.conectado_em END,
       desconectado_em = CASE WHEN EXCLUDED.status = 'desconectado' THEN NOW() ELSE whatsapp_sessoes.desconectado_em END,
       atualizado_em = NOW()`,
    [adegaId, telefone, status]
  );
}

async function conectarAdega(adegaId) {

  const atual = sessoes.get(adegaId);

  if (
    atual &&
    ["conectando", "aguardando_qr", "conectado"].includes(
      atual.status
    )
  ) {
    return atual;
  }

  if (sessoes.get(adegaId)?.conectado) return sessoes.get(adegaId);
  if (conexoesEmAndamento.has(adegaId)) return conexoesEmAndamento.get(adegaId);

  const promessa = (async () => {
    await atualizarStatus(adegaId, 'conectando');
    const { state, saveCreds } = await usePostgresAuthState(pool, adegaId);
    const { version } = await fetchLatestBaileysVersion();

    const sessao = { sock: null, conectado: false, status: "conectando", qrDisponivel: false, qrDataUrl: null };
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
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
      if (qr) {
          sessao.qrDisponivel = true;

          sessao.qrDataUrl = await QRCodeImage.toDataURL(qr, {
            width: 350,
            margin: 2,
            errorCorrectionLevel: "M"
          });

          await atualizarStatus(adegaId, "aguardando_qr");

          console.log(`\nQR Code da adega ${adegaId}:`);
          QRCode.generate(qr, { small: true });
        }

      if (connection === 'open') {
        sessao.conectado = true;
        sessao.qrDisponivel = false;
        sessao.qrDataUrl = null;

        const telefone = sock.user?.id?.split(':')[0]?.split('@')[0] || null;

        await atualizarStatus(adegaId, 'conectado', telefone);

        console.log(`Adega ${adegaId}: WhatsApp conectado.`);
      }

      if (connection === 'close') {
        sessao.conectado = false;
        const codigo = new Boom(lastDisconnect?.error)?.output?.statusCode;
        await atualizarStatus(adegaId, 'desconectado');
        sessoes.delete(adegaId);
        if (codigo !== DisconnectReason.loggedOut) {
          // setTimeout(() => conectarAdega(adegaId).catch(console.error), 3000);
          if (!timersReconexao.has(adegaId)) {
            const timer = setTimeout(async () => {
              timersReconexao.delete(adegaId);

              try {
                await conectarAdega(adegaId);
              } catch (erro) {
                console.error(
                  `Erro ao reconectar a adega ${adegaId}:`,
                  erro
                );
              }
            }, 5000);

            timersReconexao.set(adegaId, timer);
          }
        } else {
          console.log(`Adega ${adegaId}: sessão removida pelo WhatsApp; novo QR será necessário.`);
        }
      }
    });

    return sessao;
  })().finally(() => conexoesEmAndamento.delete(adegaId));

  conexoesEmAndamento.set(adegaId, promessa);
  return promessa;
}

app.get('/health', (_req, res) => res.json({ ok: true }));

app.get('/sessions/:adega_id/status', autenticar, async (req, res) => {
  const adegaId = validarAdegaId(req.params.adega_id);
  if (!adegaId) return res.status(400).json({ ok: false, erro: 'adega_id inválido.' });
  const resultado = await pool.query(
    'SELECT adega_id, telefone, status, atualizado_em FROM whatsapp_sessoes WHERE adega_id = $1',
    [adegaId]
  );
  return res.json({ ok: true, sessao: resultado.rows[0] || null });
});

app.post('/sessions/:adega_id/connect', autenticar, async (req, res) => {
  const adegaId = validarAdegaId(req.params.adega_id);
  if (!adegaId) return res.status(400).json({ ok: false, erro: 'adega_id inválido.' });
  const existe = await pool.query('SELECT 1 FROM adegas WHERE id = $1', [adegaId]);
  if (!existe.rowCount) return res.status(404).json({ ok: false, erro: 'Adega não encontrada.' });
  await conectarAdega(adegaId);
  return res.status(202).json({
    ok: true,
    mensagem: `Conexão da adega ${adegaId} iniciada. Leia o QR Code exibido no terminal.`
  });
});

app.post('/send', autenticar, async (req, res) => {
  try {
    const adegaId = validarAdegaId(req.body.adega_id);
    const telefone = normalizarTelefone(req.body.telefone);
    const mensagem = String(req.body.mensagem || '').trim();
    if (!adegaId || !telefone || !mensagem) {
      return res.status(400).json({ ok: false, erro: 'adega_id, telefone e mensagem são obrigatórios.' });
    }

    const sessao = sessoes.get(adegaId);
    if (!sessao?.conectado) {
      await conectarAdega(adegaId);
      return res.status(503).json({
        ok: false,
        erro: `WhatsApp da adega ${adegaId} ainda não está conectado. Verifique o QR Code.`
      });
    }

    const consultado = `${telefone}@s.whatsapp.net`;
    const contas = await sessao.sock.onWhatsApp(consultado);
    const conta = contas?.find((item) => item.exists);
    if (!conta) return res.status(404).json({ ok: false, erro: 'Número não encontrado no WhatsApp.' });

    const envio = await sessao.sock.sendMessage(conta.jid, { text: mensagem });
    return res.json({
      ok: true,
      adega_id: adegaId,
      telefone,
      jid: conta.jid,
      message_id: envio?.key?.id || null
    });
  } catch (erro) {
    console.error(erro);
    return res.status(500).json({ ok: false, erro: erro.message || 'Erro ao enviar mensagem.' });
  }
});

app.get("/sessions/:adega_id/qr",autenticar,async (req, res) => {
    const adegaId = validarAdegaId(req.params.adega_id);

    if (!adegaId) {
      return res.status(400).json({
        ok: false,
        erro: "adega_id inválido."
      });
    }

    let sessao = sessoes.get(adegaId);

    // if (!sessao) {
    //   await conectarAdega(adegaId);
    //   sessao = sessoes.get(adegaId);
    // }

    if (!sessao) {
      return res.status(202).json({
        ok: true,
        status: "desconectado",
        conectado: false,
        qr_code: null
      });
    }

    if (sessao?.conectado) {
      return res.json({
        ok: true,
        status: "conectado",
        conectado: true,
        qr_code: null
      });
    }

    if (!sessao?.qrDataUrl) {
      return res.status(202).json({
        ok: true,
        status: "gerando_qr",
        conectado: false,
        qr_code: null
      });
    }

    return res.json({
      ok: true,
      status: "aguardando_qr",
      conectado: false,
      qr_code: sessao.qrDataUrl
    });
  }
);


app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serviço Baileys disponível na porta ${PORT}.`);
});
