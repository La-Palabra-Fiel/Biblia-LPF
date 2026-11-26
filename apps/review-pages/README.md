# Revisión privada de libros en Cloudflare

Esta aplicación publica la lectura y firma de libros en Cloudflare Pages. El
texto se genera desde los archivos canónicos de `translation/`; no mantiene
otra copia editable. Los enlaces privados y las firmas viven en Cloudflare D1,
nunca en GitHub.

## Construir y comprobar

```bash
cd apps/review-pages
npm install
npm run build
npm run check
```

## Crear un enlace privado

Después de desplegar y aplicar la migración de D1:

```bash
python3 manage_review_links.py romanos "Ana Pérez"
```

El comando reemplaza cualquier enlace anterior de esa misma persona para ese
libro y muestra el enlace nuevo. Solo se comparte el enlace impreso.

## Subdominio sin cambiar los nameservers

En Cloudflare Pages, se añade `revision.lapalabrafiel.org` como dominio
personalizado. Después, en one.com se crea este registro:

```text
Tipo: CNAME
Nombre: revision
Destino: lpf-peer-review.pages.dev
```

Cloudflare debe asociar primero el dominio personalizado al proyecto; crear el
CNAME antes de ese paso puede producir un error 522.
