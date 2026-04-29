# ElderGuard frontend

Vite + React + TypeScript implementation of the **ElderGuard Hi-Fi** design (warm-letter aesthetic — cream paper, navy ink, brass tape, coral alert). All 19 screens across 4 flows: Onboarding, Home/Profile, Call, and Show-Me.

Hosted on **Cloudflare Pages** via Wrangler.

## Local development

```bash
cd frontend
npm install
npm run dev
```

Tap the floating **"Screens"** button (bottom-right) to jump between any of the 19 screens. The screens are also wired into a real flow — Splash advances through Onboarding to Home, Home routes to either the Call or Show-Me flow, etc.

## Deploy to Cloudflare Pages

You'll need a Cloudflare account. First time:

```bash
npx wrangler login
```

Build and deploy:

```bash
npm run build
npm run deploy
```

The first deploy creates a Pages project named `elderguard` (change in [wrangler.toml](wrangler.toml) and the `deploy` script in [package.json](package.json) if you want a different name). Subsequent deploys publish a new version of that project.

### Connecting a Git repo (alternative)

If you'd rather wire deploys to Git instead of running `wrangler` locally:

1. Push this repo to GitHub.
2. In the Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git**.
3. Build settings:
   - **Build command:** `npm run build`
   - **Build output:** `dist`
   - **Root directory:** `frontend`
4. Cloudflare auto-deploys on every push.

## Project layout

```
src/
  design-system/    Warm-letter primitives (Phone, Letterhead, BrassDial, …)
  screens/          The 19 hi-fi screens
    onboarding.tsx
    home.tsx
    call.tsx
    show.tsx
  navigator/        State-machine navigator + jump-to-screen dock
  App.tsx
  main.tsx
```

## Backend

This frontend currently stubs all backend interactions (no live calls to `../backend/main.py`). When you're ready to wire it up, hooks like the call-state transitions and the show-me verdict resolver are the natural integration points.
