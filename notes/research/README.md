# Expedientes de investigación léxica

Este directorio conserva la pista de evidencia que precede o comprueba una
decisión léxica de la LPF. Un expediente no es otra fuente de traducción, no
reemplaza el paquete canónico de un versículo y no autoriza por sí mismo un
léxico, corpus o diccionario. La autorización normativa sigue perteneciendo a
[`SOURCE_POLICY.md`](../../SOURCE_POLICY.md).

## Principio

La investigación no comienza con una palabra tradicional que haya que defender
ni con una palabra novedosa que haya que introducir. Formula una pregunta
neutral, reúne la evidencia permitida y registra por separado:

1. **hechos** reproducibles;
2. **inferencias** que explican esos hechos;
3. **decisiones** editoriales humanas;
4. **cuestiones pendientes** que todavía no permiten una conclusión.

La conclusión debe resultar reconocible a partir de los hechos. Si dos
explicaciones siguen siendo razonables, el expediente no fabrica certeza: la
cuestión permanece abierta y el versículo afectado queda en `HOLD`.

## Estados del expediente

- `collecting`: se está reuniendo o clasificando evidencia;
- `review-ready`: el expediente afirma que ya contiene la evidencia necesaria
  y espera adjudicación humana;
- `decided`: la decisión humana, su alcance y su evidencia están documentados;
- `superseded`: otro expediente conserva una decisión posterior y está
  enlazado explícitamente.

El estado del expediente es independiente de `STATUS.md`, de la aprobación de
un capítulo y del estado de una nota pública. Una política puede estar ya
decidida mientras su expediente histórico permanece `collecting`; en ese caso
el expediente no suspende silenciosamente la política, sino que declara con
precisión qué comprobación documental falta.

## Contenido mínimo

Cada expediente debe incluir:

- la pregunta formulada sin presuponer la respuesta;
- las familias originales y formas examinadas;
- la edición textual, morfología, sintaxis y corpus autorizados;
- un inventario reproducible de todas las apariciones canónicas pertinentes;
- agrupación por construcción, participantes y función discursiva;
- la entrada completa de cada testigo léxico autorizado, incluidas las
  observaciones que contradigan una hipótesis de trabajo;
- evidencia acerca de lo que las opciones españolas comunican hoy;
- alternativas consideradas y razones para aceptarlas o rechazarlas;
- hechos, inferencias y decisión en secciones separadas;
- alcance, excepciones, responsable humano y fecha de la decisión;
- consecuencias para traducción, alineación, lint y revisión histórica;
- fuentes pendientes o limitaciones del conjunto de datos.

No se copian otras Biblias ni se usan como evidencia. Tampoco se conserva
razonamiento interno de un modelo.

## Registro de una fuente externa

Antes de que una fuente externa entre en un paquete automático deben quedar
registrados:

- responsable y repositorio o editor;
- conjunto de datos y archivos exactos;
- versión o commit inmutable;
- checksums;
- licencia y atribución;
- fecha y procedimiento de adquisición;
- cobertura cronológica, geográfica y de género;
- normalizaciones realizadas;
- campos permitidos y campos rechazados;
- pruebas de procedencia, cobertura y rechazo;
- limitaciones que impidan interpretar una frecuencia como sentido.

Una fuente puede aparecer como **candidata** mientras se estudian esos datos.
Una autorización debe declarar por separado si permite consulta humana,
adjudicación documentada o entrada automática al paquete. Autorizar la primera
no autoriza silenciosamente las otras dos.

Las búsquedas primarias documentales se reproducen con
[`tools/research/ddbdp_primary_inventory.py`](../../tools/research/ddbdp_primary_inventory.py),
que valida primero el conjunto controlado contra su manifiesto y conserva las
restituciones y dataciones abiertas en vez de convertirlas en certezas.

El expediente inicial de los términos tradicionalmente reunidos bajo
**infierno** está en [`infierno.md`](infierno.md). Su inventario canónico se
regenera con
[`destination_term_inventory.py`](../../tools/research/destination_term_inventory.py).

El expediente de las formas españolas **convertirse / conversión** y las
familias originales de giro y regreso está en
[`conversion.md`](conversion.md). Su inventario canónico se regenera con
[`turning_term_inventory.py`](../../tools/research/turning_term_inventory.py).

El expediente de `בְּרִית`, `διαθήκη` y la oposición española
**pacto / testamento** está en [`pacto-testamento.md`](pacto-testamento.md).
Su inventario canónico se regenera con
[`covenant_term_inventory.py`](../../tools/research/covenant_term_inventory.py).

## Salidas de una investigación

Una investigación termina en una de estas categorías:

- **conservar** el término español;
- **restringir** su uso a construcciones definidas;
- **distinguir** varias familias o realizaciones;
- **prohibir** el término en el texto canónico;
- **sin resolver**, con la cuestión en `HOLD`.

Una decisión general se registra en `WORKFLOW.md`, se explica en una nota
pública de `notes/topics/` y recibe un control mecánico solo cuando ese control
sea determinista. Los textos históricos se corrigen versículo por versículo;
nunca mediante una sustitución semántica masiva.

