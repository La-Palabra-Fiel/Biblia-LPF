---
title: Expediente de pacto y testamento
status: ready-for-human-decision
opened: 2026-11-11
editorial_decision: none
scope: Antiguo y Nuevo Testamento
families:
  - H1285 בְּרִית
  - G1242 διαθήκη
  - G1303 διατίθεμαι
---

# Expediente de **pacto / testamento**

## Pregunta neutral

¿Cuándo `בְּרִית` y `διαθήκη` designan un pacto, disposición u otra relación,
y existe alguna construcción que requiera el concepto español de un
**testamento** que entra en vigor por la muerte de quien lo otorga?

La pregunta no permite que Hebreos 9:16–17 decida anticipadamente las otras
apariciones ni permite que la traducción habitual de las otras apariciones
decida esos dos versículos sin examinarlos.

## Inventario canónico inicial

| Familia | Apariciones | Función formal inicial |
| --- | ---: | --- |
| H1285 `בְּרִית` | 284 | sustantivo hebreo |
| G1242 `διαθήκη` | 33 | sustantivo griego |
| G1303 `διατίθεμαι` | 7 | verbo relacionado |

El inventario completo está en
[`covenant-terms.json`](inventories/covenant-terms.json) y se reproduce con
[`covenant_term_inventory.py`](../../tools/research/covenant_term_inventory.py).
No contiene glosas españolas ni una decisión semántica.

## Hechos internos iniciales

1. En el NT, `διαθήκη` relaciona explícitamente la historia de Israel, las
   promesas, el pacto de circuncisión, la sangre de Jesús, el pacto nuevo, el
   pacto anterior, el arca y las tablas. Traducir una aparición como
   **testamento** no puede romper silenciosamente esas relaciones.
2. Hebreos 9:15 usa `διαθήκη` dos veces antes de 9:16–17, y 9:20 vuelve a usar
   la misma palabra en la fórmula «la sangre de la `διαθήκη`». La posibilidad
   de un cambio de sentido en 9:16–17 debe demostrarse; no puede suponerse por
   una tradición española.
3. El supuesto **testador** de Hebreos 9:16–17 no corresponde a un sustantivo
   griego diferente. Las formas proceden del verbo `διατίθεμαι`, que también
   aparece al establecer pactos en Lucas 22:29, Hechos 3:25, Hebreos 8:10 y
   10:16. Convertir el participio en un título jurídico español es ya una
   interpretación que debe justificarse.
4. Gálatas 3:15 habla de una `διαθήκη` humana ratificada que nadie invalida ni
   altera. Este uso jurídico humano es relevante, pero no decide por sí solo si
   se trata de pacto, disposición o testamento.
5. `בְּרִית` no se limita a una relación religiosa: aparece también en pactos
   entre personas, pueblos y reyes. La construcción hebrea tradicionalmente
   descrita como «cortar un pacto» debe estudiarse como construcción completa,
   no sustituirse por la historia del término latino.

## Problema visible en el borrador actual

El borrador de Hebreos conserva **pacto** en 9:15 y 9:20, pero cambia a
**testamento** y **testador** en 9:16–17. Esa variación puede resultar correcta
o incorrecta; por ahora queda señalada como una decisión semántica no
demostrada. No se modificará automáticamente.

## Uso literario del siglo I y próximo

Se consultaron las ediciones griegas fijadas de Filón, Josefo, Plutarco, Dión
Crisóstomo y Epicteto/Arriano. La búsqueda formal recuperó únicamente
superficies `διαθηκ-`; no importó lemas, traducciones ni glosas.

| Autor/registro | Superficies | Resultado contextual |
| --- | ---: | --- |
| Filón, filosófico/exegético judío | 23 | principalmente pacto divino; también lo explica mediante donaciones y disposiciones |
| Josefo, histórico judío | 34 | testamentos, herederos y disposiciones sucesorias |
| Plutarco, biográfico/moral grecorromano | 16 | testamentos, herencias, legados y leyes testamentarias |
| Dión Crisóstomo, oratorio | 1 | testamento escrito que Sócrates no dejó |
| Epicteto/Arriano, filosófico dialogal | 1 | testamento escrito y sellado con asistencia jurídica |

Los inventarios completos están en
`source/greek/literary-koine/inventories/*-diatheke-family.json`. Las cinco
consultas del 12 de noviembre de 2026 están registradas por separado en
`source/greek/literary-koine/CONSULTATIONS.json`. El asistente revisó los
contextos primarios; no se insertaron en Team Desk ni en un paquete del modelo
de traducción.

### Hechos observables

1. El sentido testamentario es inequívoco en autores próximos al NT. Josefo
   describe las sucesivas `διαθῆκαι` de Herodes, sus herederos, legados,
   revisiones y ratificación por César. Plutarco narra testamentos abiertos
   después de la muerte, herederos inscritos y bienes legados.
2. Dión `Or. 54.4` coordina `σύγγραμμα` y `διαθήκας` entre los documentos que
   Sócrates no dejó. Epicteto `Diatr. 2.13.7` habla de escribir una `διαθήκη`
   con ayuda de quien sabe hacerlo y de sellarla junto con una garantía y otro
   documento. No son pactos religiosos.
3. Filón conserva el uso de pacto divino y a la vez conoce la analogía
   testamentaria. En `Mut. 52` afirma que las `διαθῆκαι` se escriben en
   beneficio de quienes merecen una donación y toma la `διαθήκη` como símbolo
   de gracia entre Dios que da y el ser humano que recibe.
4. Por tanto, **testamento** no es simplemente un sentido latino impuesto a
   una palabra griega que solo significaba pacto. La polisemia ya existe en el
   griego contemporáneo. Esto tampoco demuestra automáticamente que Hebreos
   9:16–17 cambie de sentido: esa decisión depende de su propia sintaxis y de
   la continuidad del argumento.

## Hebreos 9:15–20: controles inmediatos

- 9:15 llama a Jesús mediador de una `διαθήκη` nueva y menciona las
  transgresiones bajo la primera `διαθήκη`, la promesa y la herencia.
- 9:16 afirma que donde hay `διαθήκη` es necesario que se presente la muerte
  del `διαθέμενος`.
- 9:17 dice que una `διαθήκη` es firme `ἐπὶ νεκροῖς` y pregunta si tiene fuerza
  mientras vive el `διαθέμενος`.
- 9:18 introduce la conclusión con `ὅθεν` —«por lo cual»— y vuelve a la primera
  realidad inaugurada con sangre.
- 9:20 cita la fórmula «esta es la sangre de la `διαθήκη` que Dios les mandó».

La terminología de muerte, vigencia y el que dispone coincide fuertemente con
el uso testamentario documentado. La transición de 9:18–20, sin embargo,
reintegra el argumento de sangre y pacto. Las hipótesis que deben probarse son:

1. cambio temporal al sentido jurídico **testamento**;
2. sentido **pacto** continuo, con una formulación jurídica acerca de su
   ratificación;
3. explotación deliberada de ambos sentidos.

La tercera posibilidad merece consideración porque explicaría tanto la
evidencia testamentaria de 9:16–17 como la continuidad pactual de 9:15 y
9:18–20. Todavía es una hipótesis, no una decisión de traducción.

## Testigo léxico autorizado

TBESG confirma que la cuestión es disputada. Para G1242 registra tanto
«disposición, testamento, voluntad» como «convención, arreglo, pacto», y cita
Hebreos 9:16–17 bajo ambas posibilidades. Para G1303 distingue disponer por
testamento de hacer un pacto. El léxico documenta posibilidades; no resuelve
la construcción contra el discurso ni contra los usos primarios ahora
recuperados.

## Control de recepción latina

Se autorizó y consultó la edición electrónica fijada de la Vulgata Clementina
únicamente como testigo de **recepción histórica**. El inventario reproducible
está en
`source/latin/clementine-vulgate/inventories/clementine-covenant-families.json`.
La consulta recuperó 103 superficies `testament-`, 109 `pact-`, 83 nominativos
`foedus` y 137 superficies `foeder-`. Son candidatos formales, no lemas ni
sentidos adjudicados.

El dato decisivo para esta etapa es que el NT clementino tiene exactamente 33
superficies `testament-`, frente a las 33 apariciones de `διαθήκη` en TR1894.
No limita *testamentum* a Hebreos 9:16–17: lo usa también para el pacto de la
circuncisión, los dos pactos de Gálatas, el arca y las tablas del pacto, el
pacto nuevo, la sangre del pacto y el pacto eterno. En Hebreos mantiene la
misma familia latina en 9:15, 9:16, 9:17 y 9:20; solo 9:16 introduce además
`testatoris` y 9:17 `testatus est`.

Esto demuestra una mediación latina amplia: *testamentum* podía cubrir el
campo pactual y el testamentario sin el contraste moderno español entre
**pacto** y **testamento**. Por ello, una traducción española que cambie solo
9:16–17 a **testamento/testador** no puede justificarse simplemente diciendo
«así lo traduce el latín». La Clementina no efectuó ese cambio local; mantuvo
su término latino tradicional en toda la cadena. Este hecho tampoco decide el
griego: la Clementina es tardía y no es autoridad para LPF.

### Resultado provisional combinado

1. El uso testamentario ya existe en el griego contemporáneo; no nació en
   latín.
2. La tradición latina extendió *testamentum* también a contextos inequívocos
   de pacto.
3. El español moderno ya no conserva necesariamente esa amplitud. Por eso la
   decisión de Hebreos 9:16–17 debe descansar en la sintaxis griega y en el
   argumento, no en la semejanza formal con *testamentum*.

## Control documental DDbDP

La búsqueda controlada `διαθηκ-` recuperó 45 superficies en 12 documentos
candidatos: 17 pertenecen al intervalo próximo 130–198 d. C. o al siglo II en
general, y 28 son posteriores. No apareció un documento fechado íntegramente
en el siglo I. Tampoco apareció la frase exacta `ἐπὶ νεκροῖς` ni un candidato
literal `θανατον`; por tanto, DDbDP no suministra un paralelo exacto a la
redacción de Hebreos 9:16–17.

El control sí ofrece un paralelo jurídico muy cercano. El testamento de
Thatres de Oxirrinco, fechado el 22 de febrero de 130, afirma que puede
modificar o anular «esta `διαθήκη`»; después formula la condición «si muero
con esta `διαθήκη`», deja herederos «después de mi muerte», declara que «la
`διαθήκη` [es] válida» y añade las declaraciones y sellos de los testigos.
Esto prueba documentalmente que, poco después del NT, la familia podía nombrar
un testamento revocable durante la vida que determina herederos al morir.

La consulta está registrada como
`ddbdp-2026-11-12-diatheke-family-v1`. Fue una lista controlada de candidatos,
no una concordancia completa de los 67.981 papiros. El modelo de traducción no
recibió la evidencia y el paquete canónico no cambió.

## Recomendación para decisión humana

La evidencia reunida no justifica prohibir **testamento** como si fuera una
distorsión puramente latina. El sentido testamentario pertenece al griego y
está documentado tanto en autores contemporáneos como en un testamento
jurídico próximo. Tampoco justifica usar **testamento** como glosa general de
`διαθήκη`: el propio discurso bíblico la vincula repetidamente con Israel,
sangre, mandatos, arca, tablas y pactos divinos.

La recomendación es:

1. mantener **pacto** como realización normal cuando el texto habla de la
   relación pactual;
2. permitir **testamento** en Hebreos 9:16–17, donde muerte, vigencia y la
   vida del disponente activan inequívocamente el escenario testamentario;
3. añadir una nota que diga que el griego conserva la misma palabra que se
   traduce **pacto** en 9:15 y 9:20 y explota aquí su sentido jurídico;
4. preferir **quien lo hizo** o **quien lo dispuso** a **testador** si el
   título jurídico oculta la relación formal con `διατίθεμαι`;
5. no cambiar automáticamente ninguna otra aparición ni ninguna aprobación.

Una formulación de trabajo, aún no adoptada como traducción, sería:

> Porque donde hay testamento, es necesario que conste la muerte de quien lo
> hizo. Pues un testamento queda firme tras la muerte, ya que nunca tiene
> vigencia mientras vive quien lo hizo.

**Constar** conserva la idea de que la muerte debe presentarse o quedar
establecida (`φέρεσθαι`) sin añadir que alguien la causa. Debe revisarse como
español final junto con la nota antes de cualquier cambio canónico.

## Controles posteriores no bloqueantes

- clasificar las 33 apariciones de `διαθήκη` por participantes, modificadores,
  verbos y función discursiva;
- analizar la sintaxis exacta de Hebreos 9:15–20, especialmente `ἐπὶ νεκροῖς`,
  `θάνατον ἀνάγκη φέρεσθαι` y las formas de `διατίθεμαι`;
- ampliar la búsqueda formal al verbo `διατίθεμαι`, con patrones de flexión
  auditados que no confundan la familia con `διάθεσις`;
- clasificar los 75 usos literarios de `διαθήκη` y registrar cualquier caso
  que no sea claramente pactual ni testamentario;
- comparar, cuando exista una fuente abierta y fijable, el testimonio latino
  más antiguo con la recepción clementina tardía;
- documentar qué entienden hoy los lectores por **pacto**, **alianza**,
  **disposición** y **testamento**;
- adjudicar las construcciones una por una y determinar las consecuencias para
  alineación, notas y cualquier borrador previamente aprobado.

