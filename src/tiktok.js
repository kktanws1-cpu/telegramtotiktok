const axios   = require("axios");
const fsExtra = require("fs-extra");

const TIKTOK_API = "https://open.tiktokapis.com/v2";

async function initPhotoUpload(accessToken, imageCount, caption) {
  const { data } = await axios.post(
    `${TIKTOK_API}/post/publish/content/init/`,
    {
      media_type: "PHOTO",
      post_mode:  "DIRECT_POST",
      post_info: {
        title:           caption || process.env.DEFAULT_CAPTION || "",
        privacy_level:   process.env.TIKTOK_PRIVACY_LEVEL || "PUBLIC_TO_EVERYONE",
        disable_comment: process.env.TIKTOK_ALLOW_COMMENT !== "true",
        disable_duet:    process.env.TIKTOK_ALLOW_DUET    !== "true",
        disable_stitch:  process.env.TIKTOK_ALLOW_STITCH  !== "true",
      },
      source_info: {
        source:             "FILE_UPLOAD",
        photo_images_count: imageCount,
        photo_cover_index:  1,
      },
    },
    {
      headers: {
        Authorization:  `Bearer ${accessToken}`,
        "Content-Type": "application/json; charset=UTF-8",
      },
    }
  );

  if (data.error?.code !== "ok") throw new Error(`TikTok init failed: ${JSON.stringify(data.error)}`);
  return { publishId: data.data.publish_id, uploadUrls: data.data.upload_urls };
}

async function uploadImages(uploadUrls, imageFiles) {
  for (let i = 0; i < imageFiles.length; i++) {
    const { localPath, sizeBytes } = imageFiles[i];
    console.log(`[tiktok] Uploading image ${i + 1}/${imageFiles.length}...`);
    await axios.put(uploadUrls[i], fsExtra.createReadStream(localPath), {
      headers: {
        "Content-Type":   "image/jpeg",
        "Content-Length": sizeBytes,
      },
      maxBodyLength:    Infinity,
      maxContentLength: Infinity,
    });
  }
}

async function waitForPublish(accessToken, publishId, maxWaitMs = 60_000) {
  const deadline = Date.now() + maxWaitMs;
  while (Date.now() < deadline) {
    const { data } = await axios.post(
      `${TIKTOK_API}/post/publish/status/fetch/`,
      { publish_id: publishId },
      { headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json; charset=UTF-8" } }
    );
    const status = data.data?.status;
    console.log(`[tiktok] Status: ${status}`);
    if (status === "PUBLISH_COMPLETE") return;
    if (status === "FAILED") throw new Error(`Publish failed (publish_id: ${publishId})`);
    await new Promise(r => setTimeout(r, 5000));
  }
  throw new Error("TikTok publish timed out");
}

async function postImagesToTikTok(imageFiles, caption) {
  const accessToken = process.env.TIKTOK_ACCESS_TOKEN;
  if (!accessToken) throw new Error("TIKTOK_ACCESS_TOKEN is not set");
  if (imageFiles.length > 35) throw new Error("Max 35 images per TikTok post");

  const { publishId, uploadUrls } = await initPhotoUpload(accessToken, imageFiles.length, caption);
  console.log(`[tiktok] publish_id: ${publishId}`);

  await uploadImages(uploadUrls, imageFiles);
  await waitForPublish(accessToken, publishId);
  console.log(`[tiktok] ✅ Published! publish_id: ${publishId}`);
}

module.exports = { postImagesToTikTok };
