# IG Repost Draft Tool

Pulls new posts from **your own** public source Instagram account (no login
needed for this step), generates a rewritten caption with Claude, and stages
each post as a draft for you to review before publishing to your destination
account.

⚠️ This is built for use across accounts **you own**. The no-login fetch step
scrapes a public profile's recent posts, which is against Instagram's Terms
of Service if used against an account that isn't yours — don't point
`SOURCE_IG_USERNAME` at someone else's account.

## Pipeline

```
[source account, no login] --instaloader--> drafts/<shortcode>/preview.jpg
                                          --> data/new_posts.json
                                          --Claude API--> data/drafts.json
[review UI, GitHub Pages] --manual approve--> data/drafts.json status="approved"
[publish_post.py] --Graph API--> destination account
```

## One-time setup

### 1. Repo secrets/variables
In your repo: **Settings → Secrets and variables → Actions**
- Secret `ANTHROPIC_API_KEY` — your Claude API key
- Variable `SOURCE_IG_USERNAME` — the username to fetch from (or pass it manually each run)

### 2. Destination account (for publishing)
The no-login scrape only works for *fetching*. Publishing requires the
official Graph API, which means the destination account needs to be an
Instagram **Business or Creator** account linked to a Facebook Page:

1. Convert the destination IG account to Business/Creator (in the IG app: Settings → Account type).
2. Link it to a Facebook Page (same menu).
3. Create an app at [developers.facebook.com](https://developers.facebook.com/apps).
4. Add yourself as an **Instagram Tester** under the app's Instagram product — no App Review needed for personal use on your own accounts.
5. Generate a long-lived access token and find your Instagram Business Account ID (Graph API Explorer is the easiest way to do this step by step).
6. Add as repo secrets: `IG_USER_ID`, `IG_ACCESS_TOKEN`.

### 3. Public media hosting for publishing
The Graph API requires a public URL for the image/video (not a local file).
Options, easiest first:
- Enable GitHub Pages on this repo and reference the raw file path.
- Or use GitHub's raw content URL (`raw.githubusercontent.com/.../drafts/<shortcode>/preview.jpg`) — works for public repos.
- Set this as the `PUBLIC_MEDIA_BASE_URL` secret, e.g. `https://raw.githubusercontent.com/yourname/yourrepo/main`.

## Running it

- **Automatically**: the GitHub Action runs every 6 hours (edit the cron in `.github/workflows/fetch-and-caption.yml` to change frequency).
- **Manually**: Actions tab → "Fetch new posts and generate captions" → Run workflow.

## Reviewing drafts

Enable GitHub Pages (Settings → Pages → serve from `/docs`), then visit your
Pages URL. You'll see each pending draft with its media, original caption
reference, and generated caption (editable).

**Important limitation**: since GitHub Pages is static, the Approve/Skip
buttons currently only update the page locally — they don't write back to
`data/drafts.json` in the repo. To actually approve a post:
1. Edit `data/drafts.json` directly (change that entry's `"status"` to `"approved"`, and edit `"generated_caption"` if you changed it in the UI).
2. Commit that change.
3. Run: `python scripts/publish_post.py --shortcode <shortcode>` (locally, or as a separate manual workflow — see below).

If you want true one-click approval from the review page, the next step
would be a small serverless function (e.g. a Cloudflare Worker or a second
GitHub Actions workflow triggered via `repository_dispatch`) that the
Approve button calls — happy to build that next if you want it.

## Publishing an approved draft

```bash
export IG_USER_ID=...
export IG_ACCESS_TOKEN=...
export PUBLIC_MEDIA_BASE_URL=https://raw.githubusercontent.com/yourname/yourrepo/main
python scripts/publish_post.py --shortcode ABC123
```

This is deliberately one-post-at-a-time and manually triggered — there's no
"publish everything" command, so you always control exactly what goes live
and when.
