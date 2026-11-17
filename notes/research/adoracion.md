---
title: Expediente de adorar, postrarse, servir y rendir culto
status: decided
opened: 2026-11-12
editorial_decision: approved-contextual-options
scope: Antiguo y Nuevo Testamento
---

# Expediente de **adorar / adoración**

## Pregunta neutral

¿Cuándo **adorar/adoración** comunica con precisión las acciones y relaciones
expresadas por las familias hebreas y griegas, y cuándo el español debe
conservar una acción más concreta como inclinarse, postrarse, servir,
reverenciar o rendir culto?

El expediente no presupone que **adorar** sea incorrecto. Investiga si su uso
automático fusionaría acciones que el texto fuente mantiene separadas.

## Familias que deben permanecer separadas

### Hebreo y arameo

- H7812 `שָׁחָה`: inclinación o postración ante Dios, seres humanos u otros
  referentes, según la construcción;
- H5647 `עָבַד`: trabajar o servir, incluido el servicio debido a una autoridad
  o a una deidad;
- H5456 `סְגִד`: postrarse en los pasajes arameos;
- H6915 `קָדַד`: inclinarse, como control de una acción corporal cercana.

### Griego

- G4352 `προσκυνέω`: gesto o acto de postrarse, rendir homenaje o adorar;
- G3000 `λατρεύω`: prestar servicio, especialmente servicio cultual;
- G4576 `σέβομαι`: reverenciar o mostrar devoción;
- G2151 `εὐσεβέω`, G2356 `θρησκεία` y G1479 `ἐθελοθρησκεία`: controles de
  piedad, práctica religiosa y culto autoimpuesto;
- G1392 `δοξάζω`: glorificar, conservado como control para no convertir toda
  honra dirigida a Dios en la misma acción léxica.

Los números Strong solo localizan superficies. La morfología, la construcción,
los participantes y el discurso decidirán qué distinciones son reales.

## Inventario canónico inicial

| Familia | Apariciones | Función de investigación |
| --- | ---: | --- |
| H7812 `שָׁחָה` | 172 | familia central de inclinación o postración |
| H5647 `עָבַד` | 288 | familia central de trabajo o servicio |
| H5456 `סְגִד` | 5 | familia aramea de postración |
| H6915 `קָדַד` | 15 | control corporal de inclinarse |
| G4352 `προσκυνέω` | 60 | familia central de postración u homenaje |
| G3000 `λατρεύω` | 21 | familia central de servicio cultual |
| G4576 `σέβομαι` | 10 | familia central de reverencia o devoción |
| G2151 `εὐσεβέω` | 2 | control de piedad o deber religioso |
| G2356 `θρησκεία` | 4 | control de práctica religiosa |
| G1479 `ἐθελοθρησκεία` | 1 | control de culto autoimpuesto |
| G1392 `δοξάζω` | 62 | control de glorificar |

El inventario reproducible está en
[`worship-terms.json`](inventories/worship-terms.json) y se genera con
[`worship_term_inventory.py`](../../tools/research/worship_term_inventory.py).
Usa numeración protestante y no asigna glosas.

## Contrastes canónicos iniciales

1. H7812 no puede equivaler automáticamente a **adorar**: Abraham se postra
   ante visitantes (Génesis 18:2), Lot ante los ángeles (19:1), Abraham ante
   el pueblo de la tierra (23:7, 12) y Jacob ante Esaú (33:3).
2. La misma familia sí describe actos dirigidos a Jehová y a dioses falsos.
   El referente y el contexto deciden si el español debe decir **postrarse**,
   **inclinarse**, **rendir homenaje** o **adorar**.
3. H5647 incluye trabajo ordinario, servicio bajo autoridad y servicio
   religioso. Traducir toda la familia como **adorar** borraría el componente
   de servicio y produciría numerosos falsos positivos.
4. Mateo 2 usa G4352 para la acción que los magos proyectan y realizan ante
   Jesús, mientras que Mateo 18:26 lo usa para un siervo postrado ante un rey
   humano. La forma por sí sola no determina «adoración divina».
5. Mateo 4:10 distingue G4352 de G3000 en la misma frase: el primero expresa
   el acto dirigido al Señor; el segundo, el servicio que se le debe. La
   traducción y la alineación no deben fusionar ambos tokens.
6. Hechos presenta G4576 aplicado a personas devotas o reverentes y G3000 a
   servicio cultual. G1392 expresa glorificar y debe conservar su propia
   acción aun cuando Dios sea el objeto.

## Griego documental: DDbDP

Se consultaron las 67.981 transcripciones XML del repositorio DDbDP fijado en
el commit `56f68ee627b3602acd3ec9e0eee411d5912a9e3a`. La búsqueda se limitó a las
50 formas flexionadas exactas que aparecen en Scrivener/Robinson.

El inventario contiene 196 superficies: 28 fechadas entre 100 a. C. y 200
d. C. y cuatro cuyos intervalos atraviesan ese período. Los documentos usan
`προσκυνέω` al presentarse reverentemente ante familiares, superiores,
personas honradas, emperadores, clérigos y deidades. Algunas cartas desean
«postrarse» ante el rostro o los pies de otra persona como fórmula de afecto,
respeto o súplica. `θρησκεία` designa observancias, prácticas y sacrificios
religiosos.

Por tanto, `προσκυνέω` no significa por sí solo «reconocer como Dios»; el
referente y la situación aportan esa relación cuando está presente. Véanse el
[`inventario DDbDP`](../../source/greek/documentary-koine/inventories/worship-families.json)
y el registro explícito de la consulta.

## Controles literarios cercanos

| Autor | Superficies | Contrastes comprobados |
| --- | ---: | --- |
| Filón | 36 | homenaje a un gobernante; culto a Dios o imágenes; servicio; conducta piadosa |
| Josefo | 107 | Jacob se postra ante Esaú; actos dirigidos a Dios; devoción y observancia religiosa |
| Plutarco | 96 | reverencia a dioses, animales sagrados, tradiciones, gobernantes y objetos honrados; servicio humano degradante |
| Dión Crisóstomo | 6 | servicio a amos, placeres o poderes; culto a dioses; honra de la belleza |
| Epicteto | 2 | culto a Dios y trato de figuras humanas como dioses |

Estos controles confirman tres ejes distintos:

1. `προσκυνέω` describe un acto de postración u homenaje cuyo valor depende
   del destinatario y del contexto;
2. `λατρεύω` conserva el componente de servicio, sea humano, figurado o
   cultual;
3. `σέβομαι`, `εὐσεβέω` y `θρησκεία` expresan reverencia, piedad o práctica
   religiosa sin ser equivalentes automáticos de las otras dos familias.

Los cinco inventarios reproducibles están registrados en
[`CONSULTATIONS.json`](../../source/greek/literary-koine/CONSULTATIONS.json).

## Recepción latina

La Clementina fijada contiene 566 candidatos en 506 versículos: 281
superficies `ador-` y 285 formas verbales exactas de `servire`. La recepción
latina conserva una distinción especialmente clara en Mateo 4:10 y Lucas 4:8:
`adorabis` traduce la primera acción y `servies` la segunda. No las fusiona en
un solo verbo religioso.

Este dato ayuda a explicar cómo **adorar** entró en la tradición española,
pero no convierte el latín en autoridad para LPF. Véanse el
[`manifiesto`](../../source/latin/clementine-vulgate/CLEMENTINE_WORSHIP_MANIFEST.json)
y el
[`inventario`](../../source/latin/clementine-vulgate/inventories/clementine-worship-families.json).

## Español contemporáneo

El DLE define **adorar** primariamente como reverenciar o rendir culto a quien
o lo que se considera divino o relacionado con lo divino. Ese significado es
apto cuando el pasaje expresa realmente esa relación, pero añade demasiado
cuando el original describe una postración ante un ser humano.

- **postrarse** conserva el gesto de ponerse a los pies en señal de respeto,
  veneración o ruego;
- **reverenciar** expresa respetar o venerar y puede dirigirse también a una
  persona;
- **culto** puede designar homenaje religioso o el conjunto de ritos;
- **servir** conserva el estar al servicio de alguien y posee además un uso
  específicamente cultual.

Fuentes: [DLE: adorar](https://dle.rae.es/adorar),
[adoración](https://dle.rae.es/adoraci%C3%B3n),
[postrar](https://dle.rae.es/postrar),
[reverenciar](https://dle.rae.es/reverenciar),
[culto](https://dle.rae.es/culto) y [servir](https://dle.rae.es/servir).

## Conclusión factual

1. **Adorar/adoración** es español legítimo, pero no define automáticamente
   ninguna de las familias inventariadas.
2. H7812, H5456 y G4352 pueden describir el gesto ante Dios, ídolos o seres
   humanos. El destinatario y la situación deciden entre **adorar**,
   **postrarse**, **inclinarse** y **rendir homenaje**.
3. H5647 y G3000 conservan una relación de trabajo o servicio. Cuando el
   servicio es cultual pueden expresarse como **servir**, **rendir servicio** o
   **rendir culto**, pero no deben desaparecer dentro de otro token traducido
   «adorar».
4. G4576 requiere opciones de reverencia o devoción; las familias de práctica
   religiosa, piedad y glorificación deben conservar sus propias acciones.
5. Cuando dos familias aparecen juntas, como G4352 y G3000 en Mateo 4:10, cada
   token necesita su propia unidad de traducción y alineación.

## Regla aprobada

- H7812, H5456 y G4352:
  - **adorar** cuando el referente divino o idolátrico y el contexto expresan
    genuinamente culto o reconocimiento religioso;
  - **postrarse / inclinarse** cuando el gesto corporal está en primer plano;
  - **rendir homenaje / rendir reverencia** cuando la acción se dirige a una
    autoridad o persona honrada sin presentarla como divina;
- H5647 y G3000:
  - **trabajar / servir** en relaciones laborales, políticas o personales;
  - **servir / rendir servicio / rendir culto** cuando el servicio cultual está
    explícito;
  - no sustituir el token por **adorar** cuando eso borre la relación de
    servicio;
- G4576: considerar **reverenciar**, **venerar**, **respetar** o una
  construcción con **devoto**, según el referente y la sintaxis;
- G2356 y G1479: conservar las nociones de **práctica religiosa**, **culto** o
  **religión**, incluido el carácter autoimpuesto cuando se exprese;
- G1392: conservar **glorificar / dar gloria**, no convertirlo automáticamente
  en **adorar**;
- nunca deducir únicamente del verbo que el destinatario es divino, ni
  rebajar automáticamente a mero gesto un acto que el contexto presenta como
  culto;
- mantener unidades de alineación separadas para gesto, servicio, reverencia,
  práctica religiosa y glorificación.

La regla fue aprobada por el editor humano el 12 de noviembre de 2026 e
inyectada en `translation/LEXICAL_POLICY.json`. La evidencia externa permanece
fuera de los paquetes canónicos; el traductor recibe solo las opciones y
restricciones editoriales aprobadas.

## Método

1. producir un inventario canónico con numeración protestante;
2. clasificar referentes humanos, divinos e idolátricos y distinguir gesto,
   servicio, reverencia y práctica religiosa;
3. consultar uso documental y literario cercano de las formas griegas que
   realmente aparecen en Scrivener/Robinson;
4. estudiar la recepción latina y el español contemporáneo;
5. presentar opciones para decisión humana antes de modificar el traductor.

No se ha adoptado todavía ninguna regla léxica.
