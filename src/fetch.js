const axios = require("axios");

async function getNewUpdates(botToken, offset) {
  const { data } = await axios.get(
    `https://api.telegram.org/bot${botToken}/getUpdates`,
    { params: { offset: offset || 0, limit: 100, timeout: 0 } }
  );
  if (!data.ok) throw new Error(`getUpdates failed: ${data.description}`);
  return data.result;
}

// Groups photo updates by album (media_group_id) or treats singles individually
function groupPhotosByAlbum(photoUpdates) {
  const albums = new Map();
  const singles = [];

  for (const u of photoUpdates) {
    const msg    = u.message;
    const best   = msg.photo[msg.photo.length - 1]; // highest resolution
    const caption  = msg.caption || "";
    const albumId  = msg.media_group_id;

    if (albumId) {
      if (!albums.has(albumId)) albums.set(albumId, { photos: [], caption });
      albums.get(albumId).photos.push(best);
      if (caption && !albums.get(albumId).caption) albums.get(albumId).caption = caption;
    } else {
      singles.push({ photos: [best], caption });
    }
  }

  return [...singles, ...albums.values()];
}

module.exports = { getNewUpdates, groupPhotosByAlbum };
