# Política canónica de fuentes de LBF

Estado: normativa

## Jerarquía obligatoria de evidencia

Esta jerarquía es oficial, normativa y cerrada. Se aplica en este orden a toda
redacción, corrección, auditoría, alineación y adjudicación de LBF:

1. **Original textual surface is authoritative.**
2. **Morphology and syntax establish grammatical relationships.**
3. **Immediate and wider original-language contexts establish usage.**
4. **Lexicons document possible senses but do not choose the contextual sense.**
5. **Paleo/AHRC may expose additional root hypotheses, never dictate meaning.**
6. **GPT proposes a Spanish rendering and cites its evidence.**
7. **A human adjudicates uncertain or disputed cases.**

Consecuencias obligatorias:

- Ningún nivel inferior puede vencer, reemplazar ni corregir silenciosamente
  un nivel superior.
- GPT no adjudica una incertidumbre ni una disputa; devuelve `HOLD` con la
  evidencia y las opciones.
- Un auditor automático no convierte una cuestión disputada en certeza.
- Solo una persona puede adjudicar un `HOLD`, y debe dejar registrada la
  evidencia que sostuvo la decisión.
- Una traducción o alineación que no pueda demostrar esta cadena de evidencia
  permanece `draft`, aunque su español parezca correcto.
- Fidelidad no significa simplificación explicativa. Cuando el español pueda
  conservar una metáfora, imagen corporal, repetición o estructura marcada del
  original sin dejar de ser gramatical, debe conservarla. El modelo no puede
  sustituirla por su interpretación (por ejemplo, convertir «salieron de los
  lomos» en «descendían») solamente para facilitar la lectura.

## Regla cerrada

La traducción y la alineación de LBF se deciden únicamente con el paquete
canónico del versículo construido por `tools/pipeline/source_packet.py`.
Si la evidencia permitida no basta para resolver una cuestión léxica,
sintáctica o textual, el versículo queda en `HOLD` para revisión humana.
Nunca se completa por conjetura, memoria, tradición o consulta externa.

La memoria lingüística del modelo no es una fuente autorizada. El significado
se investiga siguiendo la jerarquía obligatoria: **forma + morfología +
sintaxis + discurso + uso en el corpus original**. Un léxico puede describir
posibilidades o llamar la atención a un problema, pero no elige el significado
del contexto.
Si el paquete no contiene evidencia suficiente para justificar una decisión,
el único resultado permitido es `HOLD`. Toda unidad española debe citar los
`sourceTokenIds` que la autorizan y toda decisión disputable debe citar la
evidencia contextual o de corpus que la sostiene.

La evidencia de contexto y corpus puede establecer qué comunica una expresión;
eso no autoriza a borrar la manera concreta en que el original lo comunica. La
persona adjudica si una imagen necesita explicación, pero la traducción base
la conserva siempre que sea viable en español.

## Estado del paquete de evidencia

El paquete del **Antiguo Testamento** implementa la cadena de evidencia de esta
política y puede entrar al modelo solamente cuando lleve
`evidenceStatus: READY_FOR_MODEL` y pase el validador canónico. El paquete del
**Nuevo Testamento se habilita por versículo**. Cada versículo permanece
bloqueado hasta completar sus capas equivalentes; habilitar uno nunca
desbloquea otro ni el capítulo entero.

Todo paquete debe:

1. incluya la forma canónica y su identidad de token;
2. incluya la morfología autorizada y su expansión legible;
3. incluya relaciones sintácticas cuya procedencia y correspondencia exacta
   con los tokens canónicos hayan sido validadas;
4. incluya el contexto discursivo original necesario, sin traducción;
5. incluya ocurrencias pertinentes del mismo lema en el corpus canónico,
   conservando su forma, morfología, sintaxis y referencia;
6. cualquier léxico o investigación secundaria esté fijado por repositorio,
   versión, checksum, licencia y atribución;
7. las pruebas de cobertura, procedencia, correspondencia y rechazo pasen.

El contexto de corpus no es una lista de traducciones o glosas. Es evidencia
en hebreo, arameo o griego tomada de la misma base textual canónica.

## Nuevo Testamento

Autoridad textual única:

- **Textus Receptus de Scrivener de 1894**.
- Archivo de trabajo morfológico: `source/greek/TR1894/robinson-parsed/*.UTR`.
- `source/greek/TR1894/scrivener-textonly/*.SCV` es la comprobación textual
  directa de la misma edición de Scrivener 1894. Si SCV y UTR difieren en una
  correspondencia uno-a-uno, la superficie SCV permanece autoritativa y la
  morfología Robinson puede vincularse a ella. Una diferencia de cantidad,
  orden o lectura sin correspondencia uno-a-uno produce `HOLD`; nunca se
  escoge una secuencia automáticamente.

Las etiquetas y límites de versículo de SCV son igualmente autoritativos. Si
dos o más versículos adyacentes reconstruyen exactamente la misma secuencia
combinada en SCV y UTR, la morfología UTR se reasigna determinísticamente a los
límites SCV, conservando su referencia y ordinal UTR originales. Esto no es
una elección de lectura. Si la secuencia combinada no es exacta, permanece
`HOLD`.

Evidencia auxiliar permitida en el paquete:

- forma griega de TR1894;
- variantes de transcripción que el mismo archivo TR1894 marque;
- análisis morfológico Robinson;
- número de Strong como identificador, no como definición;
- **MACULA Greek**, exclusivamente como andamiaje estructural comparativo
  proyectado sobre los tokens de TR1894 conforme a la excepción cerrada de
  abajo.

La morfología y el identificador nunca pueden cambiar, reemplazar ni ampliar
la lectura griega de TR1894.

### Excepción estructural cerrada: MACULA Greek sobre TR1894

Se autoriza `Clear-Bible/macula-greek` únicamente como fuente comparativa de
estructura griega, fijada en el commit
`8423afe47b9e8f24b7772e808af45c7159a6fe7e`. Licencia CC BY 4.0;
atribución requerida: *MACULA Greek Linguistic Datasets, available at
https://github.com/Clear-Bible/macula-greek/*.

Esta autorización no convierte Nestle 1904 ni SBLGNT en testigos textuales de
LPF. La superficie, el orden y la identidad de cada terminal canónico siguen
procediendo exclusivamente de Scrivener TR1894. La morfología canónica de
trabajo sigue siendo Robinson, sujeta a validación y corrección humana
documentada; MACULA no la reemplaza.

De MACULA Greek solo pueden entrar en la capa comparativa:

- límites de oración, cláusula y frase;
- anidamiento y orden estructural;
- clase o categoría estructural, regla, función o rol gramatical, cabeza y
  tipo de cláusula;
- el identificador de nodo MACULA únicamente como referencia de procedencia;
- la forma griega únicamente durante la correspondencia mecánica con TR1894,
  nunca como terminal ni como evidencia textual dentro del paquete final.

Quedan excluidos y deben provocar rechazo: glosas, traducciones, lemas o
morfología que pretendan reemplazar a Robinson, números Strong procedentes de
MACULA, sentidos, dominios léxicos o semánticos, marcos, roles semánticos,
referentes de participantes, sinonimia, información inglesa o china, y toda
lectura de Nestle 1904 o SBLGNT que no esté presente en TR1894.

La proyección debe cumplir todas estas condiciones:

1. cada terminal canónico es un `sourceTokenId` de TR1894 y aparece exactamente
   una vez en el árbol resultante;
2. un terminal MACULA solo puede enlazarse cuando el token SCV, un único token
   Robinson y el terminal MACULA concuerdan en la misma superficie normalizada
   y en un orden no ambiguo; una diferencia ortográfica adjudicada o una unión
   de tokens puede conservar morfología Robinson, pero no constituye acuerdo de
   las tres fuentes ni autoriza estructura MACULA;
3. la correspondencia conserva el orden y reconstruye la superficie TR1894;
4. una normalización ortográfica o diferencia de tokenización solo se acepta
   cuando sea determinista, reversible y quede registrada;
5. una diferencia textual invalida la rama estructural mínima que la contiene,
   salvo la adaptación determinista cerrada definida abajo; nunca se presenta
   una adaptación como si los textos fueran idénticos ni como enlace terminal
   MACULA;
6. toda rama invalidada queda marcada como discrepancia en el árbol
   comparativo. Si ninguna adaptación estructural cerrada la resuelve, la
   capa de evidencia usa el respaldo nativo TR definido abajo, sin atribuirle
   función, categoría ni dependencia procedentes de MACULA;
7. los nodos canónicos resultantes pertenecen a una capa sintáctica nativa de
   TR1894; un token o nodo MACULA nunca es su identidad primaria;
8. el repositorio, commit, licencia, atribución, manifiesto de archivos y
   checksums de la copia local deben verificarse antes de construir un paquete;
9. las pruebas deben demostrar cobertura terminal completa, árbol acíclico,
   paternidad única, rendimiento en orden TR1894, correspondencia del índice
   de cláusulas y rechazo de todos los campos prohibidos.

Por decisión editorial humana del 11 de noviembre de 2026, rige además esta
adaptación estructural cerrada por autoridad TR:

- entre dos anclajes exactos consecutivos —incluidos los límites del
  versículo— puede adaptarse automáticamente una brecha que contenga
  exactamente un token TR1894 y exactamente un terminal MACULA;
- el token TR debe conservar una correspondencia uno-a-uno con un único token
  Robinson cuya superficie normalizada concuerde con SCV, o llevar una
  reconciliación SCV/Robinson humana ya aprobada en
  `source/greek/TR1894/ADJUDICATIONS.json`; en el segundo caso se usa la regla
  `tr-authority-approved-robinson-binding-v1` y nunca se lo llama acuerdo
  triple;
- el terminal MACULA se elimina como identidad y se coloca en su ranura
  estructural un terminal nativo TR, con superficie, identidad y morfología
  exclusivamente TR1894/Robinson;
- la categoría y el enlace estructural de esa ranura pueden conservarse, pero
  la operación se registra como `tr-authority-isolated-one-to-one-v1`; nunca se
  registra como acuerdo triple ni como adjudicación humana del versículo;
- esta regla no afirma equivalencia léxica entre las dos lecturas. Afirma
  solamente que, dentro de una ranura aislada por los mismos anclajes
  inequívocos, TR reemplaza al texto de referencia y hereda su posición
  estructural;
- una brecha de cero-a-uno, uno-a-cero, muchos-a-muchos o una transposición no
  recibe esta adaptación de ranura. Puede recibir otra adaptación cerrada de
  esta sección; de lo contrario pasa al respaldo nativo TR descrito abajo. Un
  desacuerdo SCV/Robinson sin adjudicación humana previa sí permanece `HOLD`;
  una reconciliación ya aprobada no se reabre en la capa MACULA.

La aplicación debe ser reversible y registrar el token TR, el terminal MACULA
retirado, el versículo y los anclajes delimitadores. Una prueba debe demostrar
que no cambia ningún anclaje exacto, no duplica terminales TR y no consume una
decisión humana explícita ya registrada.

Por la misma autoridad TR se permite una segunda adaptación cerrada,
`tr-authority-macula-only-promote-child-v1`, cuando una brecha entre anclajes
exactos contiene cero tokens TR y exactamente un terminal MACULA. Solo se
aplica si ese terminal es uno de exactamente dos hijos de su grupo inmediato y
el otro hijo es un único grupo estructural ya válido. Se elimina el terminal
ausente de TR y se promueve ese único grupo, conservando su estructura interna.
La operación registra el nodo reemplazado, el terminal retirado y los anclajes
delimitadores. Si quedan dos hijos, si el hijo restante no es un grupo, si la
rama contiene otro `HOLD` o si existe una adjudicación humana explícita sobre
la rama, no se aplica esta regla.

También se permite `tr-authority-flat-permutation-v1` para una brecha con dos
o más tokens cuando las superficies normalizadas de TR y MACULA forman
exactamente el mismo multiconjunto, todos los enlaces SCV/Robinson están
resueltos y el grupo mínimo afectado contiene únicamente esos terminales como
hijos directos, sin subgrupos. El grupo conserva su categoría y función, sus
terminales MACULA se retiran y se crean terminales nativos en el orden TR. Una
duplicación no impide la operación porque no se enlazan identidades terminales
MACULA individuales; se reemplaza y registra el grupo plano completo. Si hay
un subgrupo, un terminal externo, una lectura distinta o una decisión humana
explícita, la permutación no recibe esta adaptación específica y pasa al
respaldo nativo TR, salvo que exista una incertidumbre textual o morfológica
real que todavía exija `HOLD`.

Por adjudicación editorial humana del 11 de noviembre de 2026, después de
intentar todas las adaptaciones estructurales cerradas anteriores se aplica
`tr-authority-fallback-v1` a cualquier discrepancia TR/MACULA restante. El
árbol comparativo se conserva íntegro para auditoría, pero la capa de evidencia:

- retira todo terminal MACULA que no exista en Scrivener;
- incorpora, en orden canónico, todo terminal Scrivener que MACULA no pueda
  colocar inequívocamente;
- conserva todas las ramas MACULA exactas y todas las adaptaciones más
  específicas ya validadas;
- presenta los terminales restantes en una rama nativa TR separada, sin
  categoría, función, cabeza, dependencia ni equivalencia léxica inventada;
- registra por versículo los tokens TR incorporados, los terminales MACULA
  retirados y el identificador de la regla.

Un terminal MACULA situado fuera de los límites canónicos de versículo SCV no
se reasigna a otro versículo. Se registra como terminal comparativo no canónico
retirado a nivel de capítulo; SCV conserva sin excepción sus límites y etiquetas.
Si un token Scrivener tiene correspondencia textual validada pero su terminal
MACULA no pertenece a ningún árbol proyectable, se registra como token TR
estructuralmente no colocado y entra en la rama de respaldo. No se lo describe
como diferencia textual ni se inventa para él una relación ausente.

Este respaldo no afirma que MACULA y TR coincidan y no convierte la lectura
crítica en evidencia textual. Reconoce explícitamente que en esa rama solo son
autoritativos la superficie Scrivener, el orden Scrivener y la morfología
Robinson ya validada. La falta de una relación MACULA para esos terminales se
expone al modelo; si forma, morfología, contexto y uso de corpus no bastan para
traducir una construcción concreta, el modelo todavía debe devolver `HOLD`.
Una incertidumbre real SCV/Robinson tampoco puede entrar en este respaldo.

Un proyector, parser o modelo puede proponer una rama; no puede aprobar una
función sintáctica ni resolver una incertidumbre textual. Una discrepancia
puramente TR/MACULA cubierta por `tr-authority-fallback-v1` no produce `HOLD`:
el paquete declara la ausencia de relación sintáctica para esos terminales y
conserva el resto de la estructura validada. El paquete de un versículo NT solo
puede llevar `evidenceStatus: READY_FOR_MODEL` cuando además contiene contexto
discursivo TR1894, uso de corpus TR1894, evidencia TBESG fijada y cobertura
terminal TR completa. Una incertidumbre textual o morfológica real sí mantiene
bloqueado ese versículo, no los demás.

## Antiguo Testamento

Autoridad textual única:

- **Westminster Leningrad Codex**, tal como está contenido en OSHB.
- Archivo de trabajo: `source/hebrew/OSHB/morphhb/wlc/*.xml`.

Evidencia auxiliar permitida en el paquete:

- forma hebrea o aramea de WLC;
- lema y análisis morfológico de OSHB;
- número de Strong derivado del lema de OSHB como identificador, no como
  definición;
- notas explícitas `KJV:` de OSHB únicamente para convertir la etiqueta del
  versículo a numeración protestante. Esas notas no aportan palabras ni
  significados a la traducción.
- **MACULA Hebrew**, exclusivamente sus árboles sintácticos, límites
  estructurales, roles sintácticos y referencias de participantes, después de
  correspondencia exacta y ordenada con la superficie OSHB. Fuente fijada:
  `Clear-Bible/macula-hebrew` commit
  `47db250bd55d0d8577f2a94fba114ef16c35b23c`, manifiesto permitido SHA-256
  `5f5397d2be7856b9863c291f9f017ec55e9c4fddc2f2b0dcbacd658b43738e48`.
  Licencia CC BY 4.0; véase `source/hebrew/MACULA_PROVENANCE.md`.

La morfología, el lema y el identificador nunca pueden cambiar, reemplazar ni
ampliar la lectura hebrea o aramea de WLC.

De MACULA solo pueden sobrevivir al paquete los atributos estructurales
`class`, `rule`, `role`, `head` y `clausetype`, además de los enlaces a los
`sourceTokenIds` canónicos. Quedan excluidos y deben provocar rechazo:
`english`, `mandarin`, `gloss`, `greek`, `greekstrong`, `sdbh`, `lexdomain`,
`coredomain`, `contextualdomain`, `frame`, `sensenumber` y cualquier selección
de sentido o traducción. MACULA nunca aporta la superficie autoritativa.

## Datos derivados sin autoridad semántica

- La conversión a caracteres paleohebreos es solamente una representación de
  los mismos consonantes. No decide significado.
- Todo léxico autorizado es evidencia secundaria descriptiva; no decide el
  sentido contextual ni vence a la forma, morfología, sintaxis, discurso o uso
  del corpus canónico.
- AHRC/AHLB y las hipótesis pictográficas o de raíces padre del espacio
  Paleo-Hebrew son investigación secundaria. No completan una entrada ausente
  y nunca vencen a WLC, OSHB ni a la evidencia contextual. Solo podrán entrar
  al paquete si el usuario los autoriza por separado y su licencia permite el
  uso previsto; toda discrepancia no resuelta produce `HOLD`.

## Léxicos autorizados para el paquete automático

La revisión de los archivos descargados establece:

- **Open Scriptures HebrewLexicon** — autorizado para el AT en el commit
  `21c9add13bc727d3a951361778e97e3ff7afd1ce`, con los checksums registrados
  en `Lexicons/PROVENANCE.md`. `AugIndex.xml` enlaza el lema Strong aumentado
  de OSHB con `LexicalIndex.xml` y `BrownDriverBriggs.xml`. El cargador debe
  seguir las remisiones internas explícitas de BDB cuando estén ligadas a la
  forma morfológica presente, conservando tanto la procedencia del índice como
  la entrada resuelta; no puede tratar una forma remitida como si solo tuviera
  el sentido de la entrada inicial. Su licencia es
  CC BY 4.0 y la atribución requerida es *Open Scriptures Hebrew Bible
  Project*. El cargador debe rechazar cualquier archivo cuyo checksum cambie;
- **TBESG** — autorizado para el paquete del NT mediante el cargador cerrado
  `tools/pipeline/greek_lexicon.py`, fijado al commit y checksum registrados en
  `Lexicons/PROVENANCE.md`; las pruebas verifican cobertura de todos los
  identificadores léxicos Robinson. Sus entradas describen posibilidades
  secundarias y nunca eligen el sentido contextual;
- **TBESH** — su campo `Meaning` está bloqueado. Su propio encabezado dice que
  ese campo se basa en *Abridged BDB by Online Bible* y que debe obtenerse
  permiso antes de aplicarlo en un proyecto. Ningún cargador LBF puede leer,
  copiar ni enviar `Meaning` a un modelo. Los campos estructurales y `Gloss`
  solo podrán autorizarse mediante un parser de lista positiva y pruebas de
  fuga; hoy no entran al paquete;
- **TFLSJ** y **TFLSJ extra** — presentes localmente pero no aprobados para LBF.
  No entran al paquete ni al análisis hasta una decisión normativa separada.

Repositorio autorizado:
`https://github.com/STEPBible/STEPBible-Data`, directorio `Lexicons/`.
Licencia: CC BY 4.0. La copia local debe conservar licencia, atribución, commit
de origen y checksum. No se acepta una descarga flotante sin versión fijada.

Todo léxico que llegue a aprobarse es testigo del nivel 4 de la jerarquía:
documenta sentidos posibles. No elige el sentido contextual, no reemplaza el
análisis del corpus y nunca vence a los niveles 1–3.

HALOT, DCH y BDAG pueden ser consultados por una persona con acceso legítimo,
pero no se copian, extraen, almacenan ni envían automáticamente a un modelo sin
una licencia escrita que autorice expresamente ese uso. Una consulta humana no
convierte su texto protegido en parte del paquete; solo puede producir una
decisión humana documentada para un caso `HOLD`.
- `translation/PROPER_NAMES.md` fija la forma española editorial de nombres;
  no añade contenido al texto fuente.
- La numeración protestante fija la etiqueta de trabajo; no cambia los tokens.

## Fuentes prohibidas

Quedan prohibidas como evidencia para redactar, corregir, auditar o alinear:

- cualquier Biblia traducida, incluida la LBF existente, RV1909, RVR1960,
  KJV, NVI, LBLA y toda otra versión;
- texto crítico griego, SBLGNT, NA/UBS, Majority Text, LXX y otros testigos,
  salvo la forma usada transitoriamente para la correspondencia estructural
  cerrada de MACULA Greek autorizada arriba; ninguna de esas lecturas puede
  entrar como superficie o autoridad textual;
- Macula Greek fuera de la excepción estructural cerrada anterior, cualquier
  campo MACULA Hebrew no permitido arriba y cualquier otro árbol sintáctico no
  enumerado arriba;
- BLE, glosas interlineales, gloss DP y concordancias de traducciones;
- AHRC/AHLB como autoridad primaria y cualquier léxico no fijado y autorizado;
- comentarios, teología, tipología, tradición y paralelos bíblicos usados para
  resolver el versículo;
- búsquedas web, recuperación externa, herramientas conectadas y memoria de
  una redacción bíblica conocida.

La LBF existente puede mostrarse después como objeto de comparación editorial,
pero nunca como evidencia de lo que el original dice ni como entrada para
redactar el candidato nuevo.

## Regla para modelos y herramientas

El traductor y el auditor reciben solamente:

1. las instrucciones normativas de LBF;
2. el paquete canónico de un versículo;
3. `translation/PROPER_NAMES.md` cuando haya nombres propios;
4. para el auditor, el candidato español que debe comparar con ese paquete.

No tienen navegación web, búsqueda, archivos adicionales ni herramientas de
recuperación. Un paquete cuya política, base textual o lista de fuentes no
coincida exactamente con esta política debe ser rechazado antes de llamar al
modelo.

## Alineación

La alineación usa exactamente los `sourceTokenIds` del mismo paquete canónico.
El modelo puede proponer unidades y enlaces como semilla. Una persona revisa
cada frase contra los tokens visibles y la confirma. Una semilla nunca se
presenta como alineación terminada y nunca recibe estado `hand`, `manual` o
`manual-realign` sin esa acción humana.
