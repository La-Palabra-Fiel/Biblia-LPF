# Cuaderno público de traducción

Este directorio conserva decisiones, cuestiones abiertas y explicaciones de
la traducción de La Biblia Fiel. Es documentación pública y versionada junto
con el proyecto, pero no es otra copia del texto bíblico ni una fuente
autorizada para redactar, auditar o alinear. La evidencia permitida sigue
definida exclusivamente por [`SOURCE_POLICY.md`](../SOURCE_POLICY.md) y por el
paquete canónico de cada versículo.

## Notas actuales

- [Génesis 12:9 — hacia el sur y el Neguev](ot/genesis/12-9.md)
- [Éxodo 14:19 — el mensajero de Dios](ot/exodo/14-19.md)
- [Salmos 119:147–148 — la luz entre el día y la noche](ot/salmos/119-147.md)
- [Habacuc 3:4 — dos rayos y la imagen de los cuernos](ot/habacuc/3-4.md)
- [Marcos 16 — límites de Scrivener y MACULA 16:99](nt/marcos/16-20.md)
- [Hechos 15:29 — terminal textual sin árbol proyectable](nt/hechos/15-29.md)
- [Arrepentimiento, cambio de mente, pesar y regreso](topics/arrepentimiento.md)
- [Los nefilim](topics/nefilim.md)

## Cómo guardar una nota

Durante la revisión basta con decir una de estas frases:

- **Guarda esto como nota**: crea una nota con estado `decided`.
- **Guarda esto como cuestión abierta**: crea una nota con estado `open`.
- **Actualiza la nota de [referencia o tema]**: modifica la nota existente en
  vez de duplicarla.

Una decisión ligada a un versículo se guarda en:

```text
notes/{ot|nt}/{libro}/{capítulo}-{versículo}.md
```

Una decisión que gobierna muchas apariciones se guarda en:

```text
notes/topics/{tema}.md
```

Si una conversación produce ambas cosas, la nota del versículo resume la
adjudicación local y enlaza la nota temática. La nota temática no reemplaza la
justificación que cada versículo debe recibir de su propio paquete.

## Estados

- `open`: la cuestión todavía no está resuelta.
- `decided`: una persona tomó la decisión que documenta la nota.
- `superseded`: una decisión posterior reemplazó la nota; debe enlazarse la
  nota nueva y conservarse el historial.

Estos estados documentales no son los estados canónicos `none`, `draft`,
`ready` y `done` de [`STATUS.md`](../STATUS.md), y nunca los modifican.

## Contenido mínimo

Cada nota lleva metadatos breves y las secciones que sean pertinentes:

```markdown
---
title: Título breve
reference: Éxodo 14:19
status: decided
date: 2026-10-30
topics:
  - tema
---

## Decisión

## Razón textual

## Alcance y límites

## Pasajes relacionados
```

Las notas no reproducen razonamiento interno de modelos ni importan otras
Biblias o comentarios como evidencia. Registran de manera concisa qué se
decidió, qué dato canónico gobernó la decisión y qué cuestión quedó abierta.

