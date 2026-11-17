---
title: Expediente de infierno y los términos de destino de los muertos
status: decided
opened: 2026-11-11
decided: 2026-11-12
editorial_decision: preserve-seol-hades-gehenna-and-verbal-tartaroo; prohibit-infierno-as-aligned-equivalent
scope: Antiguo y Nuevo Testamento
families:
  - H7585 שְׁאוֹל
  - G86 ᾅδης
  - G1067 γέεννα
  - G5020 ταρταρόω
---

# Expediente de **infierno**

## Pregunta neutral

¿La palabra española heredada **infierno** representa con suficiente precisión
las distintas palabras y construcciones bíblicas a las que tradicionalmente
se ha aplicado, o reúne referentes que el texto distingue?

Este expediente comenzó sin presuponer que todos los términos debían
transliterarse ni que **infierno** debía prohibirse. La decisión editorial
humana del 12 de noviembre de 2026 se registra más abajo. No autoriza cambios
masivos ni modifica por sí sola traducción, alineación o estado existentes.

## Inventario canónico inicial

El inventario reproducible usa exclusivamente WLC/OSHB para el AT y la
reconciliación Scrivener TR1894/Robinson para el NT:

| Familia | Apariciones | Descripción formal inicial |
| --- | ---: | --- |
| H7585 `שְׁאוֹל` | 66 | nombre propio o designación hebrea, según OSHB |
| G86 `ᾅδης` | 11 | sustantivo |
| G1067 `γέεννα` | 12 | sustantivo |
| G5020 `ταρταρόω` | 1 | verbo, participio en 2 Pedro 2:4 |

Los datos completos están en
[`destination-terms.json`](inventories/destination-terms.json) y se regeneran
con
[`destination_term_inventory.py`](../../tools/research/destination_term_inventory.py).
Los números Strong recuperan el inventario; no definen el sentido.

### G86 `ᾅδης`

`MAT.11.23`, `MAT.16.18`, `LUK.10.15`, `LUK.16.23`, `ACT.2.27`,
`ACT.2.31`, `1CO.15.55`, `REV.1.18`, `REV.6.8`, `REV.20.13`,
`REV.20.14`.

### G1067 `γέεννα`

`MAT.5.22`, `MAT.5.29`, `MAT.5.30`, `MAT.10.28`, `MAT.18.9`,
`MAT.23.15`, `MAT.23.33`, `MRK.9.43`, `MRK.9.45`, `MRK.9.47`,
`LUK.12.5`, `JAS.3.6`.

### G5020 `ταρταρόω`

`2PE.2.4`.

## Hechos internos que impiden una equivalencia prematura

1. Apocalipsis 20:13 presenta a la muerte y al `ᾅδης` entregando a los muertos
   que estaban en ellos. El versículo siguiente arroja a la muerte y al
   `ᾅδης` al lago de fuego. Por tanto, en ese discurso `ᾅδης` y el lago de
   fuego no son el mismo referente.
2. Hechos 2:27 y 2:31 emplean `ᾅδης` al citar y explicar el Salmo 16:10, donde
   el hebreo tiene `שְׁאוֹל`. Esta relación intertextual debe conservarse en el
   estudio; no autoriza a identificar automáticamente todos sus usos.
3. `γέεννα` forma sus propias construcciones con fuego, juicio, cuerpo y
   destrucción. El texto no la sustituye por `ᾅδης` en esos pasajes.
4. `ταρταρόω` no es otro sustantivo de lugar: es un verbo usado una sola vez,
   respecto de ángeles que pecaron. Traducirlo con el mismo sustantivo español
   ocultaría su forma y construcción.
5. `שְׁאוֹל` aparece en contextos que no pueden limitarse al castigo final de
   los impíos: Jacob espera descender allí en duelo (`Gen.37.35`), Jehová hace
   bajar y hace subir (`1Sam.2.6`), y Job pide ser escondido allí hasta que
   pase la ira (`Job.14.13`).

Estos hechos bastan para rechazar de momento la ecuación automática
**todos estos términos = infierno**. Todavía no bastan para decidir la mejor
realización española de cada aparición.

## Uso actual en los borradores LPF

Los borradores ya muestran una tendencia a distinguir **Hades**, **Gehenna** y
**Sheol/Seol**, pero el uso no es uniforme: algunas apariciones de `γέεννα` en
Mateo todavía dicen **infierno**, mientras otras dicen **Gehenna**. Esta
observación no autoriza una sustitución masiva. Cada texto se revisará desde su
paquete canónico y cualquier estado `done` afectado deberá dejar de conservarse
antes de modificar la traducción vinculada.

## Uso griego extrabíblico cercano

Se hizo una concordancia de superficie en las ediciones griegas fijadas de
Filón, Josefo, Plutarco, Dión Crisóstomo y Epicteto. Para `ᾅδης` se buscaron
formas flexionadas exactas, conservando espíritu e iota, en vez de aceptar un
prefijo amplio como si fuera lema. Aun así, una forma impresa puede ser
homógrafa: Dión contiene un `ᾅδῃ` cuyo contexto exige «cante». Por eso los
inventarios guardan la forma impresa y el contexto inmediato, y no convierten
automáticamente cada coincidencia en dato semántico.

| Corpus | Hades | Tártaro | Gehena |
| --- | ---: | ---: | ---: |
| Filón | 9 | 3 | 0 |
| Josefo | 5 | 1 | 0 |
| Plutarco | 67 | 12 | 0 |
| Dión Crisóstomo | 5 verificables + 1 homógrafo verbal | 0 | 0 |
| Epicteto | 3 | 0 | 0 |

Los contextos no permiten convertir **Hades** en una definición doctrinal
única: designa el ámbito de los muertos, aparece personificado o dentro del
lenguaje mitológico y también se usa figuradamente. **Tártaro** permanece
distinto y puede designar una profundidad punitiva; Plutarco llega a situarlo
en relación interna con Hades, no como simple sustituto del mismo nombre.
Ninguno de estos cinco controles usa **Gehena**, resultado compatible con el
origen judío palestino del término, pero un cero en estos autores no define por
sí solo su sentido bíblico.

La consulta completa de 67.981 transcripciones documentales DDbDP no recuperó
ninguna de las formas exactas de Hades ni superficies `γεενν-` o `ταρταρ-`.
Este cero es un límite de evidencia: confirma que esos nombres no aparecen en
el corpus documental fijado, no que fueran desconocidos en todo el griego
cotidiano. DDbDP se consultó solo para investigación humana y no se expuso al
paquete del traductor.

## Recepción latina comprobada

La concordancia completa de los 73 archivos de la Vulgata Clementina recuperó
69 superficies `infern-` en 68 versículos. La evidencia refuta una explicación
demasiado sencilla según la cual el latín habría fundido todos los términos:

- `ᾅδης` se recibe como formas de *infernus*; Hechos 2 conserva así la relación
  con el Salmo citado, y Apocalipsis 20 distingue todavía *infernus* del lago
  de fuego al decir que el primero es arrojado al segundo;
- las doce apariciones neotestamentarias de `γέεννα` se conservan como formas
  de *gehenna*, no como *infernus*;
- 2 Pedro 2:4 conserva el verbo mediante la construcción *in tartarum
  tradidit*, aunque en el mismo versículo añade una construcción con
  *inferni*.

Por tanto, el español **infierno** sí procede de *infernum*, pero la propia
tradición latina ofrece antecedentes para conservar **Gehena** y **Tártaro**
como designaciones distintas.

## Español receptor contemporáneo

El DLE 24.ª ed. deriva **infierno** del latín *infernum*. Su primera acepción
cristiana es el lugar de castigo eterno de los condenados; también registra el
estado de privación definitiva de Dios y, por separado, el ámbito de los
muertos en otras religiones y mitologías. Esta polisemia existe, pero la
acepción cristiana principal hace que el lector pueda entender castigo final
aun donde `שְׁאוֹל` o `ᾅδης` no lo dicen. Véase
[DLE: infierno](https://dle.rae.es/infierno), consultado el 12 de noviembre de
2026.

El mismo diccionario reconoce **gehena** y la deriva del hebreo *gē hinnōm*,
aunque la define por remisión a la acepción punitiva de **infierno**. Reconoce
también **Tártaro** como nombre literario procedente del griego y el latín. No
ofrece entrada para **Hades**. Estas ausencias o remisiones describen la
recepción española; no deciden qué distinciones debe conservar LPF. Véanse
[DLE: gehena](https://dle.rae.es/gehena) y
[DLE: tártaro](https://dle.rae.es/t%C3%A1rtaro), consultados el 12 de noviembre de
2026.

## Decisión editorial aprobada

Por aprobación humana del 12 de noviembre de 2026, LPF adopta esta política:

1. prohibir **infierno** como traducción alineada de H7585, G86, G1067 y
   G5020;
2. usar **Seol** para `שְׁאוֹל` y **Hades** para `ᾅδης`, dejando que el contexto
   y las notas expliquen la relación entre ambos sin convertirlos
   anticipadamente en el castigo final;
3. usar **Gehena** para `γέεννα`, forma española reconocible que conserva el
   nombre del texto;
4. conservar la forma verbal singular de `ταρταρόω` en 2 Pedro 2:4, por
   ejemplo **habiéndolos confinado en el Tártaro**, en vez de reemplazarla por
   un sustantivo genérico;
5. reservar **infierno** para documentación o notas explicativas; no se alinea
   con ninguno de esos cuatro términos.

La regla entra en el registro que recibe el traductor. Su aplicación a texto
ya existente exige revisión versículo por versículo y la invalidación normal
de cualquier estado que deje de estar ligado a la traducción o alineación
modificada.

## Evidencia pendiente

- clasificar las 66 apariciones de `שְׁאוֹל` por participantes, paralelismo y
  función discursiva;
- clasificar por separado las construcciones de `ᾅδης` y `γέεννα`;
- examinar las expresiones **lago de fuego**, **abismo**, **muerte segunda** y
  otras relacionadas sin convertirlas anticipadamente en sinónimos;
- revisar versículo por versículo las apariciones ya redactadas cuando una
  persona abra esa tarea; no se autoriza una sustitución masiva.

