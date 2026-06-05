const fs   = require("fs-extra");
const path = require("path");
const { getNewUpdates, groupPhotosByAlbum } = require("./src/fetch");
const { downloadTelegramFile, cleanup }     = require("./src/downloader");
const { postImagesToTikTok }                = require("./src/tiktok");

const STATE_FILE = path.join(__dirname, "state.json");

async function main() {
  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  const groupId  = process.env.TELEGRAM_GROUP_ID;

  if (!botToken || !groupId) {
    console.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_ID");
    process.exit(1);
  }

  // Load last processed update offset
  const state = await fs.readJson(STATE_FILE).catch(() => ({ offset: 0 }));
  console.log(`[bot] Checking from offset ${state.offset}`);

  const updates = await getNewUpdates(botToken, state.offset);

  if (!updates.length) {
    console.log("[bot] No new updates.");
    return;
  }

  // Advance offset immediately so reruns don't reprocess the same messages
  state.offset = updates[updates.length - 1].update_id + 1;

  // Keep only photo messages from the configured group
  const photoUpdates = updates.filter(u => {
    const msg = u.message;
    return msg && String(msg.chat.id) === String(groupId) && msg.photo;
  });

  console.log(`[bot] ${updates.length} total updates, ${photoUpdates.length} photo(s) in group`);

  const albums = groupPhotosByAlbum(photoUpdates);

  for (const album of albums) {
    const localFiles = [];
    try {
      for (const photo of album.photos) {
        const dl = await downloadTelegramFile(photo.file_id, botToken);
        localFiles.push(dl);
      }
      await postImagesToTikTok(localFiles, album.caption);
      console.log(`[bot] ✅ Posted ${album.photos.length} photo(s) to TikTok`);
    } catch (err) {
      console.error(`[bot] ❌ ${err.message}`);
    } finally {
      await cleanup(localFiles.map(f => f.localPath));
    }
  }

  // Persist offset for the next run
  await fs.writeJson(STATE_FILE, state, { spaces: 2 });
  console.log(`[bot] State saved. Next offset: ${state.offset}`);
}

main().catch(err => {
  console.error("[fatal]", err.message);
  process.exit(1);
});
