# Revisión de libros

Cada revisor recibe un enlace privado distinto para cada libro. El archivo
oculto enlaza de forma explícita el libro, el nombre del revisor y su clave
privada.

## Para el lector

1. Abre el enlace privado recibido.
2. Lee el libro completo.
3. Escribe su nombre completo y pulsa **Firmar**.

La aplicación rechaza la firma si el nombre escrito no coincide con el revisor
asignado a ese enlace. Registra el nombre, la fecha y la huella exacta del
archivo de traducción. El lector no crea una cuenta ni copia ninguna
declaración adicional.

## Datos privados

- Los enlaces privados están en `apps/team/var/book-review-links.json`.
- Las firmas están en `apps/team/var/book-signatures.json`.
- `apps/team/var/` está excluido de Git y nunca se publica en GitHub.

Para crear o volver a mostrar el enlace local de un libro:

```sh
python3 apps/team/manage_review_links.py romanos "Ana Pérez"
```

Para invalidar el enlace anterior y crear otro:

```sh
python3 apps/team/manage_review_links.py romanos "Ana Pérez" --renew
```

## Límite canónico

Una firma confirma solamente que la persona leyó y aprobó la versión española
exacta del libro. No aprueba automáticamente la alineación, no modifica
`STATUS.md` y no marca el libro como `done`. El control humano separado de
`DATA_CONTRACT.md` permanece vigente.
