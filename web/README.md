# Zonda · Sitio web

El sitio del proyecto, hecho con [Astro](https://astro.build) y publicado en
[GitHub Pages](https://efdiloreto.github.io/ZondaPro/).

## Desarrollo

```bash
npm install
npm run dev        # Servidor de desarrollo
npm run build      # Compilar a dist/
npm run preview    # Servir dist/ (bajo /ZondaPro/)
```

## Deploy

`.github/workflows/deploy-web.yml` compila y publica el sitio en GitHub Pages
cada vez que un push a `master` toca `web/**`.
