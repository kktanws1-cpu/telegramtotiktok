const axios = require("axios");
const fs    = require("fs-extra");
const path  = require("path");

const DOWNLOADS_DIR = path.join(__dirname, "../downloads");

async function downloadTelegramFile(fileId, botToken) {
  const { data: info } = await axios.get(
    `https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`
  );
  if (!info.ok) throw new Error(`getFile failed: ${info.description}`);

  const filePath   = info.result.file_path;
  const ext        = path.extname(filePath) || ".jpg";
  const localName  = `${Date.now()}_${path.basename(filePath, ext)}${ext}`;
  const localPath  = path.join(DOWNLOADS_DIR, localName);

  await fs.ensureDir(DOWNLOADS_DIR);

  const response = await axios.get(
    `https://api.telegram.org/file/bot${botToken}/${filePath}`,
    { responseType: "stream" }
  );

  await new Promise((resolve, reject) => {
    const writer = fs.createWriteStream(localPath);
    response.data.pipe(writer);
    writer.on("finish", resolve);
    writer.on("error", reject);
  });

  const { size } = await fs.stat(localPath);
  console.log(`[downloader] ${localName} (${(size / 1024).toFixed(1)} KB)`);
  return { localPath, sizeBytes: size };
}

async function cleanup(paths) {
  for (const p of (Array.isArray(paths) ? paths : [paths])) {
    await fs.remove(p).catch(() => {});
  }
}

module.exports = { downloadTelegramFile, cleanup };
