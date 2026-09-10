// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
	// El sitio se publica en GitHub Pages, desde el repositorio del proyecto:
	// la URL depende del usuario y el repositorio (guides/deploy/github).
	site: 'https://efdiloreto.github.io',
	base: '/ZondaPro',
	integrations: [sitemap()],
});
