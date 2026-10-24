# Sitio web — La Palabra Fiel

Sitio estático en [Hugo](https://gohugo.io) para el proyecto **La Palabra Fiel (LPF)**.
El texto bíblico no se escribe aquí: se genera a partir de `../translation/`.

## Requisitos

- Hugo **extended** ≥ 0.128 (probado con 0.148.2)
- Python 3.10+

En macOS: `brew install hugo`

## Uso diario

```bash
cd site
python3 tools/build-content.py   # regenera el texto desde ../translation/
hugo server                      # http://localhost:1313
```

Para compilar el sitio de producción:

```bash
python3 tools/build-content.py && hugo --gc --minify
# resultado en site/public/
```

## Cómo funciona

`tools/build-content.py` lee los archivos de traducción y produce:

| Salida | Qué es |
| --- | --- |
| `content/biblia/<libro>/_index.md` | Página de cada libro |
| `content/biblia/<libro>/<n>.md` | Página de cada capítulo (versículos en HTML) |
| `data/libros.json` | Índice del canon, estado y estadísticas |
| `data/versiones.json` | Estado leído de `../STATUS.md` |
| `static/indice.json` | Índice de búsqueda del lado del cliente |

Todo eso está en `.gitignore`: **es contenido derivado**. Se regenera en cada
compilación, también en CI. No lo edites a mano — los cambios se pierden.

El formato que espera el script es el que ya usa `translation/`:

```markdown
# Nombre del libro

> Nota de fuente opcional (aparece al pie del capítulo).

## Capítulo 1

### 1:1

Texto del versículo.

> Nota: explicación opcional de una decisión de traducción.
```

Las notas de traducción aparecen ocultas hasta que el lector abre «Nota».

Cuando se añade un libro nuevo del Antiguo Testamento, basta con dejar el
archivo en `translation/ot/` con el nombre del *slug* canónico
(`isaias.md`, `salmos.md`, …). El script lo reconoce, lo ordena en el canon y
actualiza el progreso solo. Si el nombre de archivo no coincide con el slug,
se añade una entrada a `ALIAS_ARCHIVO` en el script (así se maneja hoy
`titus.md` → `tito`).

## Estructura

```
site/
├── hugo.toml              configuración
├── assets/
│   ├── css/main.css       hoja de estilo única (sin dependencias)
│   └── js/sitio.js        tema, tamaño de letra, modo párrafo, buscador
├── layouts/
│   ├── _default/          baseof, single, list, buscar, progreso, versiones
│   ├── biblia/list.html   índice de libros
│   ├── libro/list.html    página de libro
│   ├── capitulo/single.html  el lector
│   └── partials/
├── content/               páginas escritas a mano (proyecto, progreso, …)
└── tools/build-content.py generador
```

## Contenido editable a mano

- `content/_index.md` — portada
- `content/proyecto/` — el proyecto, el juramento, metodología, base textual
- `content/progreso/_index.md` — texto introductorio (las cifras son automáticas)
- `content/versiones/_index.md` — texto introductorio del estado (la tabla es automática)
- `content/buscar/_index.md` — texto introductorio del buscador

## El lector

- Enlace permanente por versículo: `/biblia/juan/3/#v16`
- Dos modos de lectura: versículo por línea o párrafo continuo
- Cinco tamaños de letra, modo claro/oscuro (se recuerdan en el navegador)
- `←` y `→` navegan entre capítulos
- «Copiar capítulo» copia el texto con su referencia
- Búsqueda en todos los textos de trabajo disponibles, sin acentos ni mayúsculas

## Publicación

`.github/workflows/pages.yml` (en la raíz del repositorio) compila y publica en
GitHub Pages con cada `push` que toque `site/`, `translation/` o `STATUS.md`.
En el repositorio: **Settings → Pages → Source: GitHub Actions**.

El `baseURL` lo inyecta el propio flujo de trabajo, así que el sitio funciona
tanto en `usuario.github.io/repositorio/` como en un dominio propio.
