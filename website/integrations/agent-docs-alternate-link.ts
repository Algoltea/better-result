import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import type { AstroIntegration } from "astro";

const AGENT_DOCS_ALTERNATE_LINK =
  '<link rel="alternate" type="text/plain" title="how to use this" href="/llms.txt" />';

async function injectAgentDocsAlternateLink(directory: string): Promise<void> {
  const entries = await readdir(directory, { withFileTypes: true });

  await Promise.all(
    entries.map(async (entry) => {
      const path = join(directory, entry.name);

      if (entry.isDirectory()) {
        await injectAgentDocsAlternateLink(path);
        return;
      }

      if (!entry.isFile() || !entry.name.endsWith(".html")) {
        return;
      }

      const html = await readFile(path, "utf8");
      if (html.includes(AGENT_DOCS_ALTERNATE_LINK)) {
        return;
      }

      const updatedHtml = html.replace("</head>", `${AGENT_DOCS_ALTERNATE_LINK}</head>`);
      if (updatedHtml === html) {
        throw new Error(`Agent docs alternate link: missing </head> in ${path}`);
      }

      await writeFile(path, updatedHtml);
    }),
  );
}

/** Advertises the plain-text agent documentation index in every built HTML page. */
export function addAgentDocsAlternateLink(): AstroIntegration {
  return {
    name: "better-result-agent-docs-alternate-link",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        await injectAgentDocsAlternateLink(fileURLToPath(dir));
      },
    },
  };
}
