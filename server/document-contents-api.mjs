import http from "http";
import { config } from "dotenv";
import { MongoClient, ObjectId } from "mongodb";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.resolve(__dirname, "..", ".env") });

const PORT = Number(process.env.DOCUMENTS_API_PORT || 3001);
const mongoUrl = process.env.MONGO_URL;
const dbName = process.env.DATABASE_NAME;
const collName = process.env.DOCUMENT_CONTENTS_COLLECTION || "document_contents";
const openaiKey = process.env.OPENAI_API_KEY;
const openaiModel = process.env.OPENAI_CHAT_MODEL || "gpt-4o-mini";

const INSUFFICIENT =
  "I don't have enough document content in the database to answer this question for the selected paper(s). " +
  "The full text may not have been ingested into MongoDB yet, or the document ID may be missing.";

if (!mongoUrl || !dbName) {
  console.error("API: set MONGO_URL and DATABASE_NAME in .env");
  process.exit(1);
}

const client = new MongoClient(mongoUrl);

function sendJson(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let b = "";
    req.on("data", (c) => (b += c));
    req.on("end", () => resolve(b));
    req.on("error", reject);
  });
}

function tokenize(s) {
  return s
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2);
}

function scoreChunk(text, qTokens) {
  const t = text.toLowerCase();
  let sc = 0;
  for (const w of qTokens) {
    if (t.includes(w)) sc += 1;
  }
  return sc;
}

function buildContextFromDoc(doc, question, maxChars = 14000) {
  const chunks = doc.chunks;
  if (!Array.isArray(chunks) || chunks.length === 0) return "";
  const qTokens = tokenize(question);
  const scored = chunks
    .map((ch, i) => ({
      i,
      text: String(ch.text || "").trim(),
      s: scoreChunk(String(ch.text || ""), qTokens),
    }))
    .filter((x) => x.text.length > 0)
    .sort((a, b) => b.s - a.s);

  const parts = [];
  let total = 0;
  for (const x of scored) {
    const line = `[chunk ${x.i}] ${x.text}`;
    if (total + line.length + 1 > maxChars) break;
    parts.push(line);
    total += line.length + 1;
  }
  return parts.join("\n");
}

async function openaiComplete(systemPrompt, userPrompt) {
  if (!openaiKey) {
    throw new Error("OPENAI_API_KEY is not set");
  }
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${openaiKey}`,
    },
    body: JSON.stringify({
      model: openaiModel,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.25,
      max_tokens: 1200,
    }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`OpenAI error ${r.status}: ${t.slice(0, 500)}`);
  }
  const data = await r.json();
  return String(data.choices?.[0]?.message?.content || "").trim();
}

await client.connect();
const collection = client.db(dbName).collection(collName);
console.log(
  `ScholarHub API http://127.0.0.1:${PORT}  (${dbName}.${collName})  OpenAI: ${openaiKey ? "on" : "off"}`
);

http
  .createServer(async (req, res) => {
    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      });
      res.end();
      return;
    }

    const url = new URL(req.url || "/", "http://127.0.0.1");

    if (req.method === "GET") {
      const m = url.pathname.match(/^\/document\/([a-f0-9]{24})$/i);
      if (!m) {
        sendJson(res, 404, { error: "Not found" });
        return;
      }
      try {
        const doc = await collection.findOne({ _id: new ObjectId(m[1]) });
        if (!doc) {
          sendJson(res, 404, { error: "Document not found" });
          return;
        }
        const { _id, ...rest } = doc;
        sendJson(res, 200, { ...rest, _id: String(_id) });
      } catch (e) {
        console.error(e);
        sendJson(res, 500, { error: "Server error" });
      }
      return;
    }

    if (req.method === "POST" && url.pathname === "/chat/rag") {
      let payload;
      try {
        const raw = await readBody(req);
        payload = JSON.parse(raw || "{}");
      } catch {
        sendJson(res, 400, { ok: false, error: "Invalid JSON" });
        return;
      }

      const question = String(payload.question || "").trim();
      const mongoDocIds = Array.isArray(payload.mongoDocIds)
        ? payload.mongoDocIds.map((x) => String(x || "").trim()).filter((x) => /^[a-f0-9]{24}$/i.test(x))
        : [];
      const paperTitles = Array.isArray(payload.paperTitles)
        ? payload.paperTitles.map((x) => String(x || ""))
        : [];

      if (!question) {
        sendJson(res, 400, { ok: false, error: "question is required" });
        return;
      }

      if (mongoDocIds.length === 0) {
        sendJson(res, 200, {
          ok: false,
          code: "INSUFFICIENT_DATA",
          message: INSUFFICIENT,
        });
        return;
      }

      if (!openaiKey) {
        sendJson(res, 503, {
          ok: false,
          code: "LLM_DISABLED",
          message:
            "The Ask AI service is not configured. Set OPENAI_API_KEY in the API server environment (.env) and restart npm run api:documents.",
        });
        return;
      }

      try {
        const contexts = [];
        for (let i = 0; i < mongoDocIds.length; i++) {
          const oid = mongoDocIds[i];
          const doc = await collection.findOne({ _id: new ObjectId(oid) });
          const title = paperTitles[i] || doc?.paper_id || oid;
          const body = doc ? buildContextFromDoc(doc, question, 12000) : "";
          if (body.length > 0) {
            contexts.push(`### Paper context (${title})\n${body}`);
          }
        }

        const contextBlock = contexts.join("\n\n---\n\n");
        if (!contextBlock.trim()) {
          sendJson(res, 200, {
            ok: false,
            code: "INSUFFICIENT_DATA",
            message: INSUFFICIENT,
          });
          return;
        }

        const systemPrompt = `You are a research assistant. Answer ONLY using the CONTEXT below (retrieved excerpts from academic papers). 
If the context does not contain enough information, say clearly that you cannot answer from the provided excerpts.
Use clear English. When citing, mention which chunk or paper the idea comes from when possible.
Do not fabricate citations or unseen results.`;

        const userPrompt = `CONTEXT:\n${contextBlock}\n\nQUESTION:\n${question}`;

        const answer = await openaiComplete(systemPrompt, userPrompt);
        const citations = paperTitles.length ? paperTitles.filter(Boolean).slice(0, mongoDocIds.length) : mongoDocIds;

        sendJson(res, 200, {
          ok: true,
          answer,
          citations,
        });
      } catch (e) {
        console.error(e);
        sendJson(res, 500, {
          ok: false,
          error: e instanceof Error ? e.message : "Server error",
        });
      }
      return;
    }

    sendJson(res, 404, { error: "Not found" });
  })
  .listen(PORT);
