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
**Nuevo Testamento continúa bloqueado** hasta construir sus capas equivalentes.

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
- Archivo de trabajo: `source/greek/TR1894/robinson-parsed/*.UTR`.
- `source/greek/TR1894/scrivener-textonly/*.SCV` se permite solamente para
  comprobar la transcripción de la misma edición de Scrivener 1894.

Evidencia auxiliar permitida en el paquete:

- forma griega de TR1894;
- variantes de transcripción que el mismo archivo TR1894 marque;
- análisis morfológico Robinson;
- número de Strong como identificador, no como definición.

La morfología y el identificador nunca pueden cambiar, reemplazar ni ampliar
la lectura griega de TR1894.

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
- **TBESG** — aprobado como candidato para ingestión automática, sujeto a
  fijación de commit, checksum y validación de cobertura;
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
- texto crítico griego, SBLGNT, NA/UBS, Majority Text, LXX y otros testigos;
- Macula Greek, cualquier campo MACULA Hebrew no permitido arriba y cualquier
  otro árbol sintáctico no enumerado arriba;
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
