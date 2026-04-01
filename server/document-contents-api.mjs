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

if (!mongoUrl || !dbName) {
  console.error("DOCUMENT API: set MONGO_URL and DATABASE_NAME in .env");
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

await client.connect();
const collection = client.db(dbName).collection(collName);
console.log(`Document API listening on http://127.0.0.1:${PORT}  (${dbName}.${collName})`);

http
  .createServer(async (req, res) => {
    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      });
      res.end();
      return;
    }

    const m = req.url?.match(/^\/document\/([a-f0-9]{24})$/i);
    if (req.method !== "GET" || !m) {
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
  })
  .listen(PORT);
