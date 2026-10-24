#!/usr/bin/env python3
"""
build-content.py — genera el contenido del sitio a partir de la traducción.

Lee  ../translation/{ot,nt}/*.md   (fuente de verdad de LBF)
     ../STATUS.md

Escribe  content/biblia/<libro>/_index.md   (una página por libro)
         content/biblia/<libro>/<n>.md      (una página por capítulo)
         data/libros.json                   (índice y estadísticas)
         data/versiones.json                (estado desde STATUS.md)
         static/indice.json                 (índice de búsqueda)

Es idempotente: borra y regenera content/biblia por completo en cada ejecución.
No se debe editar nada dentro de content/biblia a mano.

Uso:  python3 tools/build-content.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ_SITIO = Path(__file__).resolve().parent.parent
RAIZ_REPO = RAIZ_SITIO.parent
DIR_TRADUCCION = RAIZ_REPO / "translation"
ARCHIVO_ESTADO = RAIZ_REPO / "STATUS.md"

DIR_BIBLIA = RAIZ_SITIO / "content" / "biblia"
DIR_DATOS = RAIZ_SITIO / "data"
DIR_ESTATICO = RAIZ_SITIO / "static"
RE_ITALICA = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")

# --------------------------------------------------------------------------
# Canon: orden, nombre en español y número de capítulos.
# El "slug" es el nombre de archivo esperado en translation/.
# --------------------------------------------------------------------------

CANON_AT = [
    ("genesis", "Génesis", 50), ("exodo", "Éxodo", 40), ("levitico", "Levítico", 27),
    ("numeros", "Números", 36), ("deuteronomio", "Deuteronomio", 34),
    ("josue", "Josué", 24), ("jueces", "Jueces", 21), ("rut", "Rut", 4),
    ("1samuel", "1 Samuel", 31), ("2samuel", "2 Samuel", 24),
    ("1reyes", "1 Reyes", 22), ("2reyes", "2 Reyes", 25),
    ("1cronicas", "1 Crónicas", 29), ("2cronicas", "2 Crónicas", 36),
    ("esdras", "Esdras", 10), ("nehemias", "Nehemías", 13), ("ester", "Ester", 10),
    ("job", "Job", 42), ("salmos", "Salmos", 150), ("proverbios", "Proverbios", 31),
    ("eclesiastes", "Eclesiastés", 12), ("cantares", "Cantar de los Cantares", 8),
    ("isaias", "Isaías", 66), ("jeremias", "Jeremías", 52),
    ("lamentaciones", "Lamentaciones", 5), ("ezequiel", "Ezequiel", 48),
    ("daniel", "Daniel", 12), ("oseas", "Oseas", 14), ("joel", "Joel", 3),
    ("amos", "Amós", 9), ("abdias", "Abdías", 1), ("jonas", "Jonás", 4),
    ("miqueas", "Miqueas", 7), ("nahum", "Nahúm", 3), ("habacuc", "Habacuc", 3),
    ("sofonias", "Sofonías", 3), ("hageo", "Hageo", 2), ("zacarias", "Zacarías", 14),
    ("malaquias", "Malaquías", 4),
]

CANON_NT = [
    ("mateo", "Mateo", 28), ("marcos", "Marcos", 16), ("lucas", "Lucas", 24),
    ("juan", "Juan", 21), ("hechos", "Hechos", 28), ("romanos", "Romanos", 16),
    ("1corintios", "1 Corintios", 16), ("2corintios", "2 Corintios", 13),
    ("galatas", "Gálatas", 6), ("efesios", "Efesios", 6),
    ("filipenses", "Filipenses", 4), ("colosenses", "Colosenses", 4),
    ("1tesalonicenses", "1 Tesalonicenses", 5), ("2tesalonicenses", "2 Tesalonicenses", 3),
    ("1timoteo", "1 Timoteo", 6), ("2timoteo", "2 Timoteo", 4),
    ("tito", "Tito", 3), ("filemon", "Filemón", 1), ("hebreos", "Hebreos", 13),
    ("santiago", "Santiago", 5), ("1pedro", "1 Pedro", 5), ("2pedro", "2 Pedro", 3),
    ("1juan", "1 Juan", 5), ("2juan", "2 Juan", 1), ("3juan", "3 Juan", 1),
    ("judas", "Judas", 1), ("apocalipsis", "Apocalipsis", 22),
]

# Nombres de archivo que no coinciden con el slug canónico.
ALIAS_ARCHIVO = {
    "titus": "tito",
    "zechariah": "zacarias",
}

# Nombres de STATUS.md que no coinciden con el slug del sitio.
ALIAS_ESTADO = {
    "titus": "tito",
}

RE_LIBRO = re.compile(r"^#\s+(.+?)\s*$")
RE_CAPITULO = re.compile(r"^##\s+Cap[íi]tulo\s+(\d+)\s*$", re.IGNORECASE)
RE_VERSICULO = re.compile(r"^###\s+(\d+):(\d+)([a-z]?)\s*$")
RE_NOTA = re.compile(r"^>\s?(.*)$")
RE_NOTA_TRADUCCION = re.compile(r"^>\s*Nota:\s*(.*)$", re.IGNORECASE)


class Libro:
    def __init__(self, slug: str, titulo: str, testamento: str, orden: int):
        self.slug = slug
        self.titulo = titulo
        self.testamento = testamento
        self.orden = orden
        self.titulo_archivo = titulo
        self.notas: list[str] = []
        self.capitulos: dict[int, list[tuple[str, str, list[str]]]] = {}

    @property
    def n_versiculos(self) -> int:
        return sum(len(v) for v in self.capitulos.values())

    @property
    def n_capitulos(self) -> int:
        return len(self.capitulos)


def slug_de_archivo(ruta: Path) -> str:
    base = ruta.stem.lower()
    return ALIAS_ARCHIVO.get(base, base)


def parsear_libro(ruta: Path, meta: dict) -> Libro:
    slug = slug_de_archivo(ruta)
    if slug not in meta:
        raise SystemExit(f"Libro desconocido (no está en el canon): {ruta}")
    info = meta[slug]
    libro = Libro(slug, info["titulo"], info["testamento"], info["orden"])

    capitulo_actual: int | None = None
    versiculo_actual: str | None = None
    buffer: list[str] = []
    notas_versiculo: list[str] = []

    def cerrar_versiculo():
        nonlocal buffer, versiculo_actual, notas_versiculo
        if capitulo_actual is not None and versiculo_actual is not None:
            texto = " ".join(l.strip() for l in buffer if l.strip())
            texto = re.sub(r"\s+", " ", texto).strip()
            if texto:
                libro.capitulos.setdefault(capitulo_actual, []).append(
                    (versiculo_actual, texto, notas_versiculo)
                )
        buffer = []
        versiculo_actual = None
        notas_versiculo = []

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = RE_VERSICULO.match(linea)
        if m:
            cerrar_versiculo()
            capitulo_actual = int(m.group(1))
            versiculo_actual = m.group(2) + m.group(3)
            libro.capitulos.setdefault(capitulo_actual, [])
            continue

        m = RE_CAPITULO.match(linea)
        if m:
            cerrar_versiculo()
            capitulo_actual = int(m.group(1))
            libro.capitulos.setdefault(capitulo_actual, [])
            continue

        m = RE_LIBRO.match(linea)
        if m and versiculo_actual is None and capitulo_actual is None:
            libro.titulo_archivo = m.group(1).strip()
            continue

        if versiculo_actual is None:
            m = RE_NOTA.match(linea)
            if m and m.group(1).strip():
                libro.notas.append(m.group(1).strip())
            continue

        if versiculo_actual is not None:
            nota = RE_NOTA_TRADUCCION.match(linea)
            if nota:
                if nota.group(1).strip():
                    notas_versiculo.append(nota.group(1).strip())
                continue

        buffer.append(linea)

    cerrar_versiculo()

    vacios = [c for c, v in libro.capitulos.items() if not v]
    for c in vacios:
        del libro.capitulos[c]

    if not libro.capitulos:
        raise SystemExit(f"No se encontró ningún versículo en {ruta}")
    return libro


def yaml_txt(valor: str) -> str:
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_texto_versiculo(texto: str) -> str:
    escaped = html.escape(texto, quote=False)
    return RE_ITALICA.sub(lambda match: f"<em>{match.group(1)}</em>", escaped)


def render_nota_traduccion(notas: list[str]) -> str:
    if not notas:
        return ""
    contenido = "".join(
        f"<p>{render_texto_versiculo(nota)}</p>" for nota in notas
    )
    return f'<details class="nota-traduccion"><summary>Nota</summary>{contenido}</details>'


def nota_fuente(libro: Libro) -> str:
    if not libro.notas:
        return ""
    partes = []
    for n in libro.notas:
        n = n.replace("La Biblia Fiel", "La Palabra Fiel")
        n = html.escape(n, quote=False)
        n = re.sub(r"`([^`]+)`", r"<code>\1</code>", n)
        partes.append(n)
    return " ".join(partes)


def escribir_libro(libro: Libro) -> None:
    dir_libro = DIR_BIBLIA / libro.slug
    dir_libro.mkdir(parents=True, exist_ok=True)
    capitulos = sorted(libro.capitulos)

    fuente = nota_fuente(libro)
    portada = [
        "---",
        f"title: {yaml_txt(libro.titulo)}",
        'type: "libro"',
        f'testamento: "{libro.testamento}"',
        f"weight: {libro.orden}",
        f"capitulos: {libro.n_capitulos}",
        f"versiculos: {libro.n_versiculos}",
        f'slugLibro: "{libro.slug}"',
        f"description: {yaml_txt(f'{libro.titulo} en La Palabra Fiel (LPF): {libro.n_capitulos} capítulos, {libro.n_versiculos} versículos.')}",
    ]
    if fuente:
        portada.append(f"fuente: {yaml_txt(fuente)}")
    portada += ["---", ""]
    (dir_libro / "_index.md").write_text("\n".join(portada), encoding="utf-8")

    for idx, cap in enumerate(capitulos):
        versiculos = libro.capitulos[cap]
        cuerpo = []
        for num, texto, notas in versiculos:
            texto_html = render_texto_versiculo(texto)
            cuerpo.append(
                f'<p class="v" id="v{num}">'
                f'<a class="vn" href="#v{num}" aria-label="Versículo {num}">{num}</a> '
                f"{texto_html}</p>"
            )
            if notas:
                cuerpo.append(render_nota_traduccion(notas))

        descripcion = RE_ITALICA.sub(r"\1", versiculos[0][1][:120])
        fm = [
            "---",
            f"title: {yaml_txt(f'{libro.titulo} {cap}')}",
            'type: "capitulo"',
            f"capitulo: {cap}",
            f'libro: "{libro.titulo}"',
            f'slugLibro: "{libro.slug}"',
            f'testamento: "{libro.testamento}"',
            f"weight: {cap}",
            f"versiculos: {len(versiculos)}",
            f"description: {yaml_txt(f'{libro.titulo} {cap} — La Palabra Fiel (LPF). {descripcion}')}",
        ]
        if idx > 0:
            ant = capitulos[idx - 1]
            fm += [
                "anterior:",
                f'  url: "biblia/{libro.slug}/{ant}/"',
                f"  titulo: {yaml_txt(f'{libro.titulo} {ant}')}",
            ]
        if idx < len(capitulos) - 1:
            sig = capitulos[idx + 1]
            fm += [
                "siguiente:",
                f'  url: "biblia/{libro.slug}/{sig}/"',
                f"  titulo: {yaml_txt(f'{libro.titulo} {sig}')}",
            ]
        fm += ["---", ""]
        (dir_libro / f"{cap}.md").write_text(
            "\n".join(fm) + "\n\n".join(cuerpo) + "\n", encoding="utf-8"
        )


RE_ESTADO = re.compile(
    r"^\|\s*([a-z0-9]+)\s*\|\s*(ot|nt)\s*\|\s*(none|draft|ready|done)\s*\|\s*(none|draft|ready|done)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|"
)


def leer_estado() -> list[dict]:
    if not ARCHIVO_ESTADO.is_file():
        return []
    titulos = {s: t for s, t, _ in CANON_AT + CANON_NT}
    salida = []
    for linea in ARCHIVO_ESTADO.read_text(encoding="utf-8").splitlines():
        m = RE_ESTADO.match(linea)
        if not m:
            continue
        slug_raw, _tes, trad, alin, t_por, t_el, a_por, a_el = [
            x.strip() for x in m.groups()
        ]
        if trad == "none" and alin == "none":
            continue
        slug = ALIAS_ESTADO.get(slug_raw, slug_raw)
        salida.append(
            {
                "slug": slug,
                "titulo": titulos.get(slug, slug.title()),
                "traduccion": trad,
                "alineacion": alin,
                "traduccion_por": t_por,
                "traduccion_el": t_el,
                "alineacion_por": a_por,
                "alineacion_el": a_el,
            }
        )
    return salida


def main() -> None:
    if not DIR_TRADUCCION.is_dir():
        raise SystemExit(f"No se encontró {DIR_TRADUCCION}")

    meta: dict[str, dict] = {}
    for orden, (slug, titulo, caps) in enumerate(CANON_AT, start=1):
        meta[slug] = {"titulo": titulo, "testamento": "at", "orden": orden,
                      "capitulosCanon": caps}
    for orden, (slug, titulo, caps) in enumerate(CANON_NT, start=100):
        meta[slug] = {"titulo": titulo, "testamento": "nt", "orden": orden,
                      "capitulosCanon": caps}

    archivos = sorted(DIR_TRADUCCION.glob("*/*.md"))
    if not archivos:
        raise SystemExit(f"No hay archivos de traducción en {DIR_TRADUCCION}")

    libros = [parsear_libro(a, meta) for a in archivos]
    libros.sort(key=lambda l: l.orden)

    if DIR_BIBLIA.exists():
        shutil.rmtree(DIR_BIBLIA)
    DIR_BIBLIA.mkdir(parents=True)

    (DIR_BIBLIA / "_index.md").write_text(
        "\n".join(
            [
                "---",
                'title: "La Biblia"',
                'description: "Libros de la Biblia con textos de trabajo disponibles en La Palabra Fiel (LPF), todavía en revisión."',
                "---",
                "",
                "Libros con texto de trabajo disponible en la edición LPF. Estos",
                "borradores siguen en revisión y no representan una traducción",
                "completa terminada ni aprobada.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    indice_busqueda: list[dict] = []
    for libro in libros:
        escribir_libro(libro)
        for cap in sorted(libro.capitulos):
            for num, texto, _notas in libro.capitulos[cap]:
                indice_busqueda.append(
                    {
                        "r": f"{libro.titulo} {cap}:{num}",
                        "u": f"/biblia/{libro.slug}/{cap}/#v{num}",
                        "t": texto,
                    }
                )

    publicados = {l.slug: l for l in libros}
    canon = []
    for slug, titulo, caps in CANON_AT:
        l = publicados.get(slug)
        canon.append({"slug": slug, "titulo": titulo, "testamento": "at",
                      "capitulos": l.n_capitulos if l else caps,
                      "versiculos": l.n_versiculos if l else 0,
                      "publicado": bool(l)})
    for slug, titulo, caps in CANON_NT:
        l = publicados.get(slug)
        canon.append({"slug": slug, "titulo": titulo, "testamento": "nt",
                      "capitulos": l.n_capitulos if l else caps,
                      "versiculos": l.n_versiculos if l else 0,
                      "publicado": bool(l)})

    n_at = sum(1 for l in libros if l.testamento == "at")
    n_nt = sum(1 for l in libros if l.testamento == "nt")
    datos_libros = {
        "totales": {
            "libros": len(libros),
            "capitulos": sum(l.n_capitulos for l in libros),
            "versiculos": sum(l.n_versiculos for l in libros),
            "porcentajeAT": round(n_at / len(CANON_AT) * 100),
            "porcentajeNT": round(n_nt / len(CANON_NT) * 100),
            "porcentajeCanon": round(len(libros) / (len(CANON_AT) + len(CANON_NT)) * 100),
        },
        "publicados": [
            {
                "slug": l.slug,
                "titulo": l.titulo,
                "testamento": l.testamento,
                "capitulos": l.n_capitulos,
                "versiculos": l.n_versiculos,
            }
            for l in libros
        ],
        "canon": canon,
    }

    DIR_DATOS.mkdir(parents=True, exist_ok=True)
    DIR_ESTATICO.mkdir(parents=True, exist_ok=True)

    (DIR_DATOS / "libros.json").write_text(
        json.dumps(datos_libros, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DIR_DATOS / "versiones.json").write_text(
        json.dumps(leer_estado(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DIR_ESTATICO / "indice.json").write_text(
        json.dumps(indice_busqueda, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(f"  libros:      {len(libros)}")
    print(f"  capítulos:   {datos_libros['totales']['capitulos']}")
    print(f"  versículos:  {datos_libros['totales']['versiculos']}")
    print(f"  índice:      {(DIR_ESTATICO / 'indice.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
