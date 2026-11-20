// @ts-check
import { defineConfig, passthroughImageService } from 'astro/config';
import { satteri } from '@astrojs/markdown-satteri';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const base = '/gils-gadgets';
const repo = fileURLToPath(new URL('..', import.meta.url));

// The repo's Markdown files that this site renders, and their routes.
const routes = {
  'README.md': '/',
  'typing-game/README.md': '/typing-game/',
  'musical-keyboard/README.md': '/musical-keyboard/',
  'musical-numbers/README.md': '/musical-numbers/',
  'screen-saver/README.md': '/screen-saver/',
  'story/README.md': '/story/',
  'BUILD.md': '/build/',
  'HARDWARE.md': '/hardware/',
  'CUSTOMIZE.md': '/customize/',
};

// Relative links in the Markdown point at repo files. Rendered pages go to
// their site route, everything else goes to the file on GitHub.
const repoLinks = {
  name: 'repo-links',
  link(node, ctx) {
    const url = node.url;
    if (!ctx.fileURL || URL.canParse(url) || url.startsWith('#') || url.startsWith('/')) return;
    const [file, hash] = url.split('#');
    const path = relative(repo, resolve(dirname(fileURLToPath(ctx.fileURL)), file));
    const anchor = hash ? `#${hash}` : '';
    ctx.setProperty(node, 'url', path in routes
      ? base + routes[path] + anchor
      : `https://github.com/agrathwohl/gils-gadgets/blob/HEAD/${path}${anchor}`);
  },
};

// Tables get a scroll box; runs of image-only paragraphs get a grid.
const html = (value) => ({ type: 'html', value });
const isShot = (n) => n?.type === 'paragraph'
  && n.children.every((c) => c.type === 'image' || (c.type === 'text' && !c.value.trim()));
const wrapBlocks = {
  name: 'wrap-blocks',
  after(root, ctx) {
    root.children.forEach((n, i, all) => {
      if (n.type === 'table') {
        ctx.insertBefore(n, html('<div class="scroll" tabindex="0">'));
        ctx.insertAfter(n, html('</div>'));
      }
      if (isShot(n) && !isShot(all[i - 1])) ctx.insertBefore(n, html('<div class="shots">'));
      if (isShot(n) && !isShot(all[i + 1])) ctx.insertAfter(n, html('</div>'));
    });
  },
};

export default defineConfig({
  site: 'https://agrathwohl.github.io',
  base,
  image: { service: passthroughImageService() },
  markdown: {
    processor: satteri({ mdastPlugins: [repoLinks, wrapBlocks] }),
    shikiConfig: { theme: 'github-dark-high-contrast' },
  },
  vite: { server: { fs: { allow: ['..'] } } },
});
