# Registro de fuentes para investigación léxica

Este registro distingue las fuentes del paquete automático, las fuentes
autorizadas únicamente para investigación humana y las fuentes que siguen en
evaluación. La autoridad normativa pertenece a
[`SOURCE_POLICY.md`](../../SOURCE_POLICY.md).

## Fuentes actualmente autorizadas para el NT

| Capa | Fuente fijada | Función | Límite |
| --- | --- | --- | --- |
| Superficie | Scrivener TR1894, distribución SCV | Texto y límites protestantes autoritativos | Ninguna lectura externa puede sustituirla |
| Morfología | Robinson UTR, revisión `7fd4d02c3e5adebd379ebfbc824040820dde10fc` | Análisis morfológico vinculado a SCV | No decide por sí solo el sentido |
| Estructura | MACULA Greek, commit `8423afe47b9e8f24b7772e808af45c7159a6fe7e` | Capa estructural comparativa bajo lista positiva | No aporta texto, lema, glosa ni semántica |
| Corpus | TR1894 | Apariciones originales con forma, morfología y estructura | Es corpus neotestamentario, no muestra por sí solo todo el griego común |
| Léxico | TBESG, commit `ed476a8ee6e3f7b3a46fc48af6c7dabc02387b1d` | Sentidos posibles secundarios | Nunca elige el sentido contextual |

Los manifiestos vinculantes y checksums están en
[`source/greek/TR1894/MANIFEST.json`](../../source/greek/TR1894/MANIFEST.json),
[`source/greek/TR1894/MACULA_GREEK_MANIFEST.json`](../../source/greek/TR1894/MACULA_GREEK_MANIFEST.json)
y [`Lexicons/PROVENANCE.md`](../../Lexicons/PROVENANCE.md).

## Autorizado para investigación humana: griego documental

**Estado:** autorizado para expedientes léxicos humanos y adjudicación
documentada de `HOLD`; no autorizado para entrada automática al modelo.

La fuente primaria es el componente documental DDbDP de Papyri.info. Su
repositorio público `papyri/idp.data` contiene las transcripciones EpiDoc XML y
metadatos relacionados. Podría aportar ejemplos de cartas, peticiones,
recibos, contratos y administración, con búsqueda limitada por fecha.

La autorización exige siempre:

1. identificar el subconjunto exacto de DDbDP y excluir traducciones e
   imágenes ajenas al conjunto autorizado;
2. comprobar la licencia aplicable a cada componente y la atribución;
3. fijar un commit y los checksums de un manifiesto cerrado;
4. definir una ventana cronológica inicial y conservar la fecha individual de
   cada documento;
5. conservar procedencia, lugar, género documental y grado de datación;
6. documentar normalización ortográfica, abreviaturas, lagunas y restituciones
   editoriales;
7. impedir que frecuencia, procedencia egipcia o género administrativo se
   presenten como definición léxica;
8. añadir pruebas que rechacen campos no autorizados y descargas flotantes.

La concentración geográfica y documental del material es una limitación
explícita: una aparición demuestra uso posible en ese testimonio; no demuestra
que todos los autores ni todas las regiones usaran la palabra del mismo modo.

Referencia de evaluación, todavía no evidencia canónica:
<https://github.com/papyri/idp.data>

### Capa de descubrimiento recomendada

El corpus abierto `alekkeersmaekers/duke-nlp`, usado por el proyecto
Trismegistos Words, añade lema, morfología y análisis automático a un corte de
los papiros documentales de DDbDP. Declara licencia CC BY-SA 4.0 y atribuye al
texto original de DDbDP licencia CC BY 3.0. Sus autores estiman aproximadamente
99 % de precisión para lematización, 95 % para morfología y 85–90 % para
sintaxis; estas cifras no convierten una anotación individual en hecho.

Su función autorizada es únicamente descubrir candidatos flexionados. Cada
resultado debe volver a comprobarse contra la transcripción primaria fijada de
Papyri.info, su fecha, procedencia, género, lagunas y restituciones. La copia
publicada parte de una descarga de DDbDP de septiembre de 2016; por tanto no
puede reemplazar el corpus primario actual ni suministrar por sí sola una
frecuencia definitiva.

Referencia de evaluación, todavía no evidencia canónica:
<https://github.com/alekkeersmaekers/duke-nlp>

### Muestra de control manual

PapyGreek Treebanks, producido por el proyecto *Digital Grammar of Greek
Documentary Papyri* de la Universidad de Helsinki, ofrece un conjunto menor de
papiros documentales anotados lingüísticamente y publicado con DOI
`10.5281/zenodo.5074307`. Puede servir como muestra de control para evaluar el
descubrimiento automático, no como sustituto de DDbDP por su cobertura mucho
menor.

Referencia de evaluación, todavía no evidencia canónica:
<https://doi.org/10.5281/zenodo.5074307>

La procedencia técnica fijada durante la evaluación está documentada en
[`source/greek/documentary-koine/PROVENANCE.md`](../../source/greek/documentary-koine/PROVENANCE.md).

La comprobación primaria controlada valida 70 transcripciones candidatas y 85
registros HGV del commit fijado mediante hashes agregados. Después, una
concordancia normalizada recorrió los 67.981 XML del árbol DDbDP fijado y
recuperó 57 superficies de las familias investigadas, todas con metadatos HGV.
No confirmó ninguna aparición fechada exclusivamente en el siglo I d. C.; tres
documentos tienen límites cronológicos unilaterales que podrían solaparse con
él. Esta precisión impide convertir una búsqueda negativa en prueba de
ausencia. La fuente ya está autorizada para consulta humana bajo la excepción
cerrada de `SOURCE_POLICY.md`. No se ha añadido al paquete del modelo: esa
ampliación requeriría una política nueva y una migración explícita de paquetes.

La clasificación provisional muestra además que 22 de las 57 superficies son
el nombre propio de un monasterio. Este control confirma que una búsqueda o
frecuencia sin inspección humana produciría una impresión semántica falsa.

### Arquitectura autorizada para investigación humana

```text
duke-nlp descubre formas y lemas candidatos
                    ↓
Papyri.info/DDbDP confirma la transcripción primaria
                    ↓
metadatos filtran fecha, lugar y género documental
                    ↓
una persona comprueba el contexto y la restitución editorial
                    ↓
el expediente cita el documento y declara sus límites
```

Ninguna estadística, lema automático, dependencia automática o etiqueta
semántica entraría como autoridad. La evidencia sería la forma griega
comprobada en el documento primario; las anotaciones solo ayudarían a hallarla
y clasificarla.

## Autorizado para investigación humana: controles literarios

**Estado:** autorizados como controles literarios del siglo I para expedientes
léxicos humanos y adjudicación documentada de `HOLD`; no autorizados como
entrada automática al modelo.

Se fijaron exclusivamente las ediciones griegas de:

- Filón de Alejandría en Open Greek and Latin `First1KGreek`, commit
  `ed91552c52530c8f5a3ddf2dd767e899372a804c`: 31 archivos `grc`;
- Flavio Josefo en PerseusDL `canonical-greekLit`, commit
  `7fd4dae30f1d2176c3c6f64c0750f6f39cd972f3`: 4 archivos `grc`.
- Plutarco en el mismo commit PerseusDL: 143 archivos `grc`, uno por obra;
- Dión Crisóstomo en el mismo commit: 1 edición `grc` de las *Orationes*;
- Epicteto, transmitido por Arriano, en el mismo commit: 5 archivos `grc`.

Ambas colecciones declaran CC BY-SA 4.0. Los árboles, conteos y hashes de blobs
están cerrados en
[`LITERARY_KOINE_MANIFEST.json`](../../source/greek/literary-koine/LITERARY_KOINE_MANIFEST.json),
y la procedencia editorial está documentada en
[`PROVENANCE.md`](../../source/greek/literary-koine/PROVENANCE.md). Los archivos
ingleses paralelos, notas y aparato quedan excluidos de la concordancia.

La primera consulta de `μετανο-` y `μεταμελ-` recuperó, sin asignar lema ni
glosa, 59 superficies en Filón, 84 en Josefo, 96 en Plutarco, 7 en Dión y 2 en
Epicteto/Arriano. Los inventarios conservan forma, obra, CTS, ruta y contexto
griego inmediato. No se suman sus frecuencias: cada autor y registro permanece
separado. Tampoco se presentan como sustitutos del habla cotidiana. Su valor
es mostrar usos contemporáneos o cercanos en registros literarios distintos.

Las consultas `ogl-philo-2026-11-11-metano-family-v1` y
`perseus-josephus-2026-11-11-metano-family-v1` están registradas en
[`CONSULTATIONS.json`](../../source/greek/literary-koine/CONSULTATIONS.json).
Allí también constan las consultas separadas de Plutarco, Dión Crisóstomo y
Epicteto/Arriano.
Los contextos fueron revisados por el asistente de investigación, pero no se
insertaron en Team Desk ni en un paquete del modelo de traducción.

## Candidatos no aptos para importación automática actual

- **PHI Greek Inscriptions:** útil para consulta epigráfica, pero la licencia
  pública del sitio limita la copia a estudio personal y *fair use*. No se
  copiará al paquete sin permiso que cubra el uso del proyecto.
- **TLG:** útil como corpus literario amplio, pero el corpus completo requiere
  suscripción. No es una dependencia libre y reproducible del paquete.
- **Moulton y Milligan:** testigo secundario histórico basado en papiros e
  inscripciones; puede señalar ejemplos, pero no reemplaza los documentos
  primarios ni decide el contexto.

## Evidencia acerca del español receptor

El DLE, el Diccionario histórico de la lengua española y CORPES XXI pueden
documentar etimología, sentidos registrados y uso español contemporáneo. Esa
evidencia responde a «¿qué entenderá hoy el lector?», no a «¿qué significa la
forma griega o hebrea en este versículo?».

**Estado actual:** consulta humana y documentación pública; no forman parte del
paquete del modelo. Antes de automatizar cualquier consulta se necesitarían
permiso, versión reproducible, procedencia y una modificación expresa de la
política.

