/**
 * Checks if the TikTok access token is still valid.
 * If not, uses the refresh token to get a new one and updates GitHub Secrets.
 */
const axios      = require("axios");
const { execFileSync } = require("child_process");

async function run() {
  const accessToken  = process.env.TIKTOK_ACCESS_TOKEN;
  const refreshToken = process.env.TIKTOK_REFRESH_TOKEN;
  const clientKey    = process.env.TIKTOK_CLIENT_KEY;
  const clientSecret = process.env.TIKTOK_CLIENT_SECRET;
  const ghToken      = process.env.GH_PAT;
  const repo         = process.env.GITHUB_REPOSITORY;

  if (!accessToken) {
    console.log("[refresh] No access token configured — skipping.");
    return;
  }

  // Check if the current token is valid
  try {
    await axios.get("https://open.tiktokapis.com/v2/user/info/?fields=open_id", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    console.log("[refresh] Access token is valid.");
    return;
  } catch (err) {
    if (err.response?.status !== 401) {
      console.log("[refresh] Token check returned non-auth error — continuing.");
      return;
    }
  }

  console.log("[refresh] Token expired. Refreshing...");
  if (!refreshToken) throw new Error("TIKTOK_REFRESH_TOKEN not set — re-run OAuth setup");

  const params = new URLSearchParams({
    client_key:    clientKey,
    client_secret: clientSecret,
    grant_type:    "refresh_token",
    refresh_token: refreshToken,
  });

  const { data } = await axios.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    params.toString(),
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );

  if (data.error) throw new Error(`Refresh failed: ${data.error_description || data.error}`);

  console.log("[refresh] New tokens obtained. Updating GitHub Secrets...");

  if (ghToken && repo) {
    // Use stdin to avoid exposing tokens in process list
    const ghEnv = { ...process.env, GH_TOKEN: ghToken };
    execFileSync("gh", ["secret", "set", "TIKTOK_ACCESS_TOKEN", "--repo", repo], {
      input: data.access_token, env: ghEnv, stdio: ["pipe", "inherit", "inherit"],
    });
    execFileSync("gh", ["secret", "set", "TIKTOK_REFRESH_TOKEN", "--repo", repo], {
      input: data.refresh_token, env: ghEnv, stdio: ["pipe", "inherit", "inherit"],
    });
    console.log("[refresh] GitHub Secrets updated.");
  } else {
    console.log("[refresh] GH_PAT or GITHUB_REPOSITORY not set — secrets not updated remotely.");
  }

  // Make new token available to the current workflow run
  process.env.TIKTOK_ACCESS_TOKEN  = data.access_token;
  process.env.TIKTOK_REFRESH_TOKEN = data.refresh_token;
}

run().catch(err => {
  // Non-fatal: log and continue — bot will fail naturally if token is bad
  console.error("[refresh] Warning:", err.message);
});
