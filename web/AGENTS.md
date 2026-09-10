## El sitio de Zonda

El sitio del proyecto, hecho con [Astro](https://docs.astro.build) y publicado en
GitHub Pages (`https://efdiloreto.github.io/ZondaPro/`). Es estático: páginas
`.astro` sin frameworks de UI ni JS de cliente.

```bash
npm install            # Instalar dependencias
npm run dev            # Servidor de desarrollo
npm run build          # Compilar a dist/
npm run preview        # Servir dist/ (bajo /ZondaPro/)
```

## Convenciones

- **Estilo:** la paleta y las piezas salen de la interfaz de la aplicación
  (`python/zonda/recursos/qss/zonda.qss`): los azules de la marca, el amarillo
  del CTA, los grises de las tarjetas y las notas del Reglamento. Las variables
  viven en `src/styles/global.css`; los títulos van en Oswald, la fuente de la
  interfaz.
- **Idioma:** todo el código, los comentarios y el contenido están en español.
- **Licencia:** cada archivo de código (`.astro`, `.css`) arranca con el
  encabezado GPLv3, igual que el resto del proyecto.
- **Rutas y assets:** con `base: '/ZondaPro'` en `astro.config.mjs`, las rutas
  internas se arman con `import.meta.env.BASE_URL` y las imágenes y fuentes van
  en `src/assets/` y `src/fuentes/` con imports ESM, para que el build les
  aplique el prefijo. Nada de rutas absolutas escritas a mano.
- **Deploy:** `.github/workflows/deploy-web.yml` publica en GitHub Pages cuando
  un push a `master` toca `web/**`. El flujo del repo es `dev` → `master`: el
  sitio se actualiza recién cuando el cambio llega a `master`.

## Documentación

- [Páginas y rutas](https://docs.astro.build/en/guides/routing/)
- [Componentes Astro](https://docs.astro.build/en/basics/astro-components/)
- [Estilos y CSS](https://docs.astro.build/en/guides/styling/)
- [Deploy a GitHub Pages](https://docs.astro.build/en/guides/deploy/github/)
