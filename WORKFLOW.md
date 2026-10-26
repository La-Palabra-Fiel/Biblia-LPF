# Flujo de trabajo

Lea el juramento en `README.md` antes de escribir español.
Lea también `SOURCE_POLICY.md`. Su lista de fuentes es cerrada: si el paquete
no basta, el versículo queda en `HOLD`. No se busca otra fuente.

La traducción es el procedimiento de abajo. El detalle de archivos y
comandos está en `tools/pipeline/README.md`. `STATUS.md` y
`tools/verify.py` no aceptan un versículo.

## Traducir

Un capítulo a la vez. Un versículo, un paquete de fuente. No empezar
por el español ya escrito. Numeración protestante. NT: TR1894. AT:
OSHB/WLC. Español actual de Latinoamérica (`tú` / ustedes). Nombres:
`translation/PROPER_NAMES.md`.

El modelo no navega, no recupera documentos y no recibe otra Biblia. La LBF
existente no entra al prompt de redacción. Toda unidad del candidato cita
`sourceTokenIds`; una cuestión que el paquete no resuelve se aparta para una
persona.

El nombre divino es una forma fijada y comprobada mecánicamente: todo יהוה
explícito se traduce **Yahvé**. Nunca se usa Jehová, Yavé, Yahweh, Yahveh,
YHWH ni SEÑOR como sustituto de יהוה. Esto no altera el tratamiento distinto
de אדני como **Adonai** cuando funciona como apelativo fijado.

La decisión de significado sigue esta evidencia, en este orden de trabajo:

```text
forma → morfología → sintaxis → discurso → uso en el corpus original
```

Los léxicos y la investigación Paleo-Hebrew son testigos secundarios. Pueden
describir opciones o señalar un problema, pero no eligen el sentido del
contexto. Una afirmación que la evidencia canónica no justifica queda en
`HOLD`.

Open Scriptures HebrewLexicon es el testigo léxico autorizado para el AT,
fijado por commit y checksum. El paquete llega a él desde el lema Strong
aumentado de OSHB; sus sentidos siguen siendo opciones secundarias y nunca
eligen la traducción. El cargador sigue también las remisiones internas
explícitas de BDB ligadas a una forma morfológica; no puede reducir una forma
remitida a la primera entrada del índice Strong (por ejemplo,
`לְהָטִים` remite a misterio/encantamiento, mientras el singular de Génesis
3:24 permanece llama). TBESG es el candidato griego autorizado, pendiente de
parser y validación de cobertura. El campo `Meaning` de TBESH está bloqueado
por el aviso de Online Bible; el paquete no lo lee. TFLSJ y TFLSJ extra están
presentes pero no autorizados. HALOT, DCH y BDAG tampoco entran al paquete
automático sin una licencia escrita específica para ese uso.

La sintaxis del AT procede únicamente de la capa estructural permitida de
MACULA Hebrew, fijada y comprobada contra OSHB. El cargador descarta glosas,
traducciones, equivalentes griegos, SDBH, dominios, marcos y sentidos elegidos.
Cada palabra debe coincidir en orden y superficie hebrea con OSHB; una sola
discrepancia produce `HOLD_SOURCE_MISMATCH`. El contexto inmediato se construye
del OSHB y el uso de corpus se recupera localmente del mismo OSHB, priorizando
lema, morfología y relación sintáctica de manera determinista.

### Camino GPT autorizado

Cuando el usuario autoriza explícitamente el camino pagado, GPT-5.6 Sol redacta
un versículo a la vez desde el paquete canónico. Devuelve solamente el español,
las unidades con `sourceTokenIds`, incertidumbres y conceptos añadidos (que
debe dejar vacíos). El lint local comprueba reglas mecánicas. Para contener el
costo, el auditor independiente no se ejecuta rutinariamente: compara el
candidato con el mismo paquete, sin reescribir, solamente cuando el candidato
declara incertidumbre, falla una regla local o la persona solicita la auditoría.

La mesa de equipo fija `reasoning.effort=medium` para la redacción y la
auditoría independiente de fidelidad cuando esta se requiere. Cada artefacto registra ese esfuerzo;
un artefacto de redacción o auditoría sin procedencia `gpt-5.6-sol` y `medium`
se rechaza y debe prepararse de nuevo. La comprobación mecánica del español es
local y determinista; la fluidez final la adjudica la persona que lee el
versículo y después el capítulo completo. No se paga una tercera llamada para
suplantar esa lectura humana. Las decisiones difíciles incluyen como máximo
dos explicaciones breves ligadas a `sourceTokenIds`; no se pide ni se conserva
razonamiento interno del modelo. Las llamadas fijan límites de salida que
incluyen los tokens de razonamiento para contener el costo.

Las adjudicaciones humanas aprobadas forman una memoria visible para los
revisores y deben mantener consistente la política del proyecto. Esa memoria
no entra al prompt como evidencia, no entrega al modelo el español anterior y
nunca puede elegir un sentido contra el paquete canónico. Solo las reglas
generales ya fijadas —por ejemplo, conservar imágenes concretas, usar Yahvé y
no suavizar— son precedentes vinculantes del modelo. Una decisión léxica o
sintáctica anterior puede alertar al revisor, pero el versículo presente debe
quedar justificado otra vez por su propia superficie, gramática y contexto.

El capítulo entra en `translation/` solamente con los candidatos que pasaron
la comprobación local y, cuando fue requerida, la auditoría de fidelidad; los
demás conservan el texto anterior y quedan en el informe como `HOLD`. Después una persona lee el capítulo completo para comprobar
continuidad, voz y fluidez. Ningún pase de modelo constituye aprobación humana.

La mesa nunca vuelve a preparar ni cobra por un versículo cuya aprobación
humana todavía coincide exactamente con el texto canónico. Un fallo de
auditoría se muestra con sus hallazgos y no puede aceptarse silenciosamente:
la persona corrige el texto o escribe su propia adjudicación y activa el
control explícito de anulación humana. La aplicación jamás redacta esa
adjudicación por la persona. La estimación previa distingue llamadas conocidas,
llamadas selectivas probables y el máximo posible de la ejecución.

Las unidades enlazadas que produce GPT pueden convertirse en semilla de
alineación. La persona debe abrir cada frase, comprobar cada enlace contra los
tokens visibles y pulsar **Confirmar frase completa**. Hasta entonces la
alineación sigue siendo semilla y `draft`.

No suavice. No fortalezca. No resuelva lo que el texto deja abierto.
No trabaje de memoria, de otra versión, ni desde la teología.
No simplifique una metáfora o imagen concreta convirtiéndola en su explicación.
Si el español puede decir la imagen de forma gramatical, consérvela; una nota
humana posterior puede explicarla, pero la traducción no debe borrarla.

Toda palabra o frase continua suplida en español sin una palabra ni una fuerza
gramatical correspondiente en la fuente se escribe entre asteriscos Markdown:
`*soy*`, `*son*`, `*y*`. La cursiva declara al lector que la expresión fue
suplida; nunca autoriza añadir un concepto. Una palabra que expresa persona,
definitud, tiempo, aspecto, forma verbal, sintaxis o fuerza discursiva de la fuente no
es «extra» solo porque no tenga token separado. Los mismos asteriscos deben
permanecer en el texto y en la unidad de alineación. La persona revisora
confirma explícitamente esta marcación antes de aprobar el versículo.

### Camino Cursor anterior (suspendido para el trabajo GPT)

Lo que sigue documenta el comando Cursor existente. No es el camino GPT
autorizado arriba y no debe mezclarse con él dentro de un capítulo. Se conserva
hasta que el ejecutor GPT tenga su propia prueba piloto y sustituya este tramo
de manera explícita.

#### Estaciones del camino anterior

| Orden | Quién | Cuándo |
| --- | --- | --- |
| 1 | paquete de fuente | siempre, un versículo |
| 2 | Cursor Auto redacta | siempre |
| 3 | lint local | siempre, sin modelo |
| 4 | Cursor Auto audita | si el lint pasó |
| 5 | GPT-5.6 Terra | solo si el versículo es cuestionable |
| 6 | Cursor Auto vuelve a auditar | solo el español que tocó Terra |
| 7 | Cursor Auto verifica el español | siempre; antes y después de Terra |

Pasa limpio: la auditoría de Auto no tiene fallos ni avisos, la comprobación
de español confirma gramática y fluidez, y el borrador no trae incertidumbre,
concepto añadido ni unidad descartada. Ese versículo no va a Terra.

Es cuestionable, y entonces entra Terra, cuando ocurre cualquiera de
estas cosas:

- el lint marca un fallo conocido (*vosotros*, *parir*, piedras duales
  hechas banquillo u otro anti-ejemplo del lint)
- la auditoría falla o avisa
- la comprobación de español detecta gramática, calco o fluidez deficiente
- el borrador trae incertidumbre, concepto añadido o unidad sin token

Si después de Terra el lint sigue fallando, o la segunda auditoría
tiene veredicto `fail`, el versículo queda apartado y el español
anterior permanece. Luego Auto verifica que el español sea actual y
legible. Una palabra que la auditoría de fuente deja pasar, como una
interjección arcaica, falla esa verificación. El versículo queda
apartado. La verificación no reescribe el verso: un candidato nuevo
que falla no se escribe, y una línea mala que ya está en el archivo
queda para el traductor. La nota queda en
`{libro}-{capítulo}-{versículo}.spanish-check.json`. Un `pass` de
fidelidad entra en el archivo solo si esa verificación pasa, aunque
traiga avisos; esos avisos quedan en la auditoría para la lectura
humana. Terra no se repite.

Una palabra que el hebreo no tiene, y que el español necesita para ser
oración, va en cursiva: *son*. El asterisco es la marca para el lector.
Una cópula marcada así no aparta el versículo.

Si el aviso es solo el número —un sustantivo singular y un participio
plural—, Terra elige el español gramatical. La elección queda en
`readerNote` del informe del capítulo, para la lectura humana.

Si el problema es el papel de la cláusula —quién actúa, o a qué nombre
rige una preposición—, Terra no lo toca. El versículo queda apartado
para el traductor, un versículo a la vez.

GPT y Grok no entran en este comando. El script anterior está en
`python3 tools/pipeline/run_chapter-old.py <libro> <capítulo>`.

### Cómo se corre

Un capítulo. El comando llama al CLI de Cursor: Auto audita, y Terra
repara una sola vez cuando el versículo es cuestionable. Recorre el
capítulo y escribe el español que pasó la segunda auditoría. Cuando
termina, una persona lee el capítulo y el informe, y aprueba.

```sh
python3 tools/pipeline/auto_pass.py exodo 1
python3 tools/pipeline/auto_pass.py exodo 1 --from 1 --to 5
```

Hace falta `agent` en el PATH, con sesión iniciada:

```sh
curl https://cursor.com/install -fsS | bash
agent login
agent models
```

`LBF_CURSOR_AUTO_MODEL` vale `auto` si no se define.
`LBF_CURSOR_POLISH_MODEL` vale `gpt-5.6-terra` si no se define. Si el
CLI rechaza ese id, use uno que liste `agent models`.

El español que ya está en `translation/` se audita. Un pase limpio se
queda. Un fallo, un aviso o español que no fluye va a Terra. Auto vuelve a auditar ese
español. El arreglo entra en el versículo cuando el veredicto es
`pass`. Si el veredicto es `fail`, o el lint sigue fallando, el
versículo queda en el informe y el español anterior permanece.

Para rehacer todo el texto existente del AT con Terra, incluso los versículos
que antes pasaron limpios, se usa:

```sh
python3 tools/pipeline/auto_ot.py --from-book genesis --from-chapter 1 --full
```

`--full` obliga a que cada versículo pase por Terra, pero no omite las
comprobaciones posteriores ni registra aprobación humana.

El informe queda en
`pipeline/{ot|nt}/{libro}/_logs/{libro}-{capítulo}.auto-pass.json`.
El comando no firma `STATUS.md`.

Si el versículo todavía no tiene español, Auto lo redacta y sigue el
mismo ciclo. Entra en el archivo cuando la auditoría lo acepta.

La cola de peticiones sigue disponible para contestar dentro del
editor, un JSON a la vez:

```sh
python3 tools/pipeline/run_chapter.py exodo 1
```

Ese script escribe el paquete y las peticiones en `pipeline/`. Cada
ítem de `{libro}-{capítulo}.queue.json` trae `model`, `request` y
`reply`. `cursor-auto` lo responde Cursor Auto. `sonnet` lo responde
Sonnet. El objeto JSON se escribe en `reply` y se vuelve a correr el
mismo comando. `run_book.py` hace lo mismo, capítulo por capítulo.
`finish_book_apply.py` copia los `passed` de esa cola al archivo del
libro. El comando de arriba es el que termina el capítulo solo.

Formato del archivo:

```markdown
# Tito

## Capítulo 1

### 1:1

Pablo, siervo de Dios…
```

Un versículo, un encabezado `### capítulo:versículo`. Un archivo por
libro.

### Español que ya está en translation/

```sh
python3 tools/pipeline/auto_pass.py exodo 1
```

Ese es el comando. Audita el texto del archivo, manda a Sonnet los
fallos y los avisos, vuelve a auditar, y escribe los arreglos con
veredicto `pass`.

`audit_translation.py` solo escribe las peticiones de auditoría para
contestarlas a mano dentro del editor. No repara.

## Alinear

La alineación es un mapa hecho a mano, un capítulo a la vez.

1. Trabajar desde la columna TR (NT) o OSHB (AT) declarada.
2. Mapear cada unidad española a los tokens de fuente, o dejar una razón explícita de no cubierto.
3. Guardar un solo archivo: `alignment/{nt|ot}/{libro}/{libro}-reverse-links.json`.

Prohibido:

- zip automático de un libro entero
- `gloss-match` / gloss DP presentado como alineación
- `auto-zip` presentado como terminado
- numeración masorética como etiqueta del trabajo

`method` debe ser `hand` (o una razón explícita de no cubierto).
Cero `auto-zip`. Cero `gloss-match`. Cero frases sin caminar presentadas como listas.
Además, la frase debe tener estado humano `hand`, `manual` o
`manual-realign`. `seeded-hand` sigue siendo una semilla, no una revisión
humana, aunque sus unidades lleven `method: hand`.

Tito hoy tiene 72 frases `auto-zip`. Eso no es alineación terminada.

## Registro

`STATUS.md` guarda las palabras `none`, `draft`, `ready` y `done`.
Ese archivo no es el procedimiento. `tools/verify.py` no juzga el
español: si se corre, mira si el archivo está completo.
`tools/status.py` no escribe estados.

`ready` en esa tabla solo quiere decir que `verify.py` pasó.
`done` solo lo escribe una persona, con nombre y fecha. Ningún modelo
lo infiere. El publicador, más abajo, todavía lee esa fila. Aceptar
un versículo es la auditoría de Auto, y Sonnet cuando hizo falta.

## Proceso en Translator

Translator no reemplaza `tools/pipeline/`. La secuencia de abajo es la
entrega del libro en la aplicación, no la manera de redactar el español.

Translator presenta una sola secuencia por libro:

```text
traducir → verificar → aprobación humana → alinear → verificar → aprobación humana → revisar y commit → exportar → preparar rama → push y merge del PR
```

El trabajo frase por frase permanece en la vista de traducción. **Terminar
libro** abre una vista final separada para verificación, firmas, commit,
exportación y entrega al publicador; el flujo final no ocupa el espacio de edición de frases.

Solo la acción siguiente queda habilitada. Los botones de verificación llaman
a `tools/verify.py`; no duplican sus reglas. Las aprobaciones exigen `ready`,
nombre y confirmación humana, y escriben solamente la fila canónica del libro
en `STATUS.md`. Editar el español borra las firmas de traducción y alineación;
editar los enlaces borra la firma de alineación. **Revisar y commit** muestra
la lista exacta de archivos del libro, vuelve a ejecutar `tools/status.py` y
requiere confirmación humana. Solo entonces crea un commit con la traducción,
el directorio de alineación y la fila de ese libro en `STATUS.md`; nunca incluye
filas pendientes de otros libros ni trabajo ya preparado en el índice. Exportar
llama únicamente a `tools/export.py` y conserva todas sus negativas. **Preparar
rama del publicador** requiere otra confirmación explícita y llama únicamente a
`tools/publish.py`; crea la rama local, pero nunca usa `--push` ni abre el PR.
Translator no llama a ese estado «publicado»: el paso siguiente permanece
abierto hasta que la rama se empuje y el PR se fusione en `cgv-data/main`.

En la etapa de alineación, **Continuar alineación** abre la primera frase no
confirmada. Revise cada unidad contra los tokens de fuente, corrija cualquier
enlace incorrecto y pulse **Confirmar frase completa**. Esa acción humana marca
como `hand` solamente las unidades visibles y el estado de esa frase, y avanza a la
siguiente; nunca confirma un libro entero ni ejecuta autoalineación.

## Publicar

Publicar no es marcar `done`. Publicar es posterior:

```text
Biblia-LBF → validar → revisar y commit → exportar → PR del publicador → cgv-data
```

Son dos pasos. Primero exportar:

```sh
python3 tools/export.py filipenses
```

Eso escribe el paquete en `/tmp/lbf-export/`. No copie esos archivos a un
árbol local de `cgv-data`.

`export.py` se niega si el libro no está `done` y firmado, o si el texto, la
alineación o la fila de `STATUS.md` de ese libro no están *commiteados*. Un
`sourceCommit` debe nombrar un *commit* que contenga el trabajo, así que la
negativa llega antes de escribir el paquete, no después de intentar publicarlo.

Después publicar. `tools/publish.py` es el publicador:

```sh
python3 tools/publish.py filipenses --data-repo ../cgv-data
```

Eso corta la rama `lbf-<libro>-<fecha>` desde `origin/main` y hace un solo
*commit* con dos archivos:

| Archivo | Destino en `cgv-data` |
| --- | --- |
| `<libro>.lbf.md` | `bibles/LBF/<libro>.lbf.md` |
| `<libro>.alignment.json` | `bibles/LBF/alignments/<libro>.alignment.json` |

El *commit* se hace en un `git worktree` temporal. Su copia de trabajo de
`cgv-data` no se toca: no cambia de rama y sus archivos sucios no entran.

Sin `--push` no empuja nada. Le imprime la rama, el *commit* y el enlace para
abrir el *pull request*. Revise el `--stat` antes de empujar.

`publish.py` se niega si:

- el libro no está `done` y firmado en `STATUS.md`
- el texto, la alineación o la fila de `STATUS.md` de ese libro no están
  *commiteados* — `export.py` ya lo comprueba; `publish.py` lo vuelve a comprobar
- el paquete no coincide con `HEAD` — reexporte
- la alineación cambió después de exportar — la firma ya no la ata
- `tools/status.py` falla
- la rama ya existe
- el `--data-repo` no tiene *commits*, o su `origin` no es `cgv-data`

Ese último caso importa: un `git init` vacío llamado `cgv-data` acepta
archivos y no publica nada.

Este repositorio no importa texto desde `cgv-data`.

Translator presenta este publicador como su último paso. La app no vuelve a
implementar la publicación: entrega el libro y la ruta de la copia existente de
`cgv-data` a `tools/publish.py`, muestra su salida y se detiene después del
commit local. Ese resultado se etiqueta **rama preparada**, nunca **publicado**.
La app muestra el comando de `push` y el enlace del PR como pasos humanos
pendientes, y solo presenta la publicación como completa cuando el mismo
`sourceCommit` está presente en `cgv-data/main`. La validación de estado se
limita al libro seleccionado; trabajo pendiente de otro libro no bloquea su
publicación.

## Lo que este flujo no es

No es `STATUS.md` ni `tools/verify.py`.
No es GPT ni Grok. Ese camino es `run_chapter-old.py`.
No es Sonnet en cada versículo.
No es una máquina de aprobaciones por verso.
No es un segundo corpus bajo `apps/translator/`.
No es un zip generado por un modelo.
