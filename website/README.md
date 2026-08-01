# better-result documentation site

The product documentation for [better-result](https://github.com/dmmulroy/better-result), built with [Blume](https://useblume.dev/).

## Develop

Requires Node.js 22.12 or newer.

```sh
cd website
bun install
bun run dev
```

## Validate and build

```sh
bun run check
bun run build
```

The static site is written to `website/dist/`. Blume also generates page-level Markdown, `llms.txt`, and `llms-full.txt` for coding agents. Cloudflare serves `/agents.txt` as an alias of the compact `/llms.txt` index, and each HTML page advertises that index with a plain-text `rel="alternate"` link.

## Deploy

The site is deployed as a Cloudflare Worker with static assets and serves `better-result.dev` through a Workers route:

```sh
bun run deploy
```

Wrangler must be authenticated to the `dmmulroy` Cloudflare account. Deployment configuration lives in `wrangler.jsonc`.

## Brand assets

The site serves the better-result mark in formats for documentation, social cards, browsers, and installed web apps:

- `public/logo.svg` and `public/logo.png` are the primary scalable and raster marks.
- `public/icon.svg`, `public/icon.png`, and `public/favicon.ico` provide browser icons.
- `public/apple-touch-icon.png` provides the iOS home-screen icon.

Keep generated raster assets visually identical to `public/logo.svg`, which is the canonical artwork.

## Content conventions

- Document the API shipped by the repository branch, not unreleased ideas.
- Prefer examples that show inferred `Result<Success, Error>` types.
- Use recoverable domain errors as `Err`; reserve `Panic` for defects.
- Keep headings and API names literal so humans and plain-text-searching agents can find them.
- Keep Blume-specific presentation separate from the technical contract whenever possible.
