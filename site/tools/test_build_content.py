from __future__ import annotations

import unittest
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory

build_content = run_path(str(Path(__file__).resolve().parent / "build-content.py"))


class RenderTextoVersiculoTests(unittest.TestCase):
    def test_renders_single_asterisk_emphasis_as_italics(self) -> None:
        self.assertEqual(
            build_content["render_texto_versiculo"]("Estos *son* los nombres."),
            "Estos <em>son</em> los nombres.",
        )

    def test_escapes_html_while_rendering_emphasis(self) -> None:
        self.assertEqual(
            build_content["render_texto_versiculo"]("*son* <script>alert(1)</script>"),
            "<em>son</em> &lt;script&gt;alert(1)&lt;/script&gt;",
        )

    def test_preserves_double_asterisk_text(self) -> None:
        self.assertEqual(
            build_content["render_texto_versiculo"]("**literal**"),
            "**literal**",
        )

    def test_removes_italics_markers_from_plain_metadata_text(self) -> None:
        self.assertEqual(
            build_content["RE_ITALICA"].sub(r"\1", "Estos *son* los nombres."),
            "Estos son los nombres.",
        )

    def test_updates_old_project_name_in_displayed_source_note(self) -> None:
        book = build_content["Libro"]("exodo", "Éxodo", "ot", 1)
        book.notas = ["La Biblia Fiel — Éxodo.", "Fuente: OSHB / WLC."]
        self.assertEqual(
            build_content["nota_fuente"](book),
            "La Palabra Fiel — Éxodo. Fuente: OSHB / WLC.",
        )

    def test_renders_notes_collapsed_and_escapes_html(self) -> None:
        rendered = build_content["render_nota_traduccion"](
            ["*son* se suple <para completar> la oración."]
        )
        self.assertIn('<details class="nota-traduccion"><summary>Nota</summary>', rendered)
        self.assertNotIn("<details open", rendered)
        self.assertIn("<em>son</em>", rendered)
        self.assertIn("&lt;para completar&gt;", rendered)

    def test_parses_verse_notes_separately_from_verse_text(self) -> None:
        with TemporaryDirectory() as directory:
            book_path = Path(directory) / "exodo.md"
            book_path.write_text(
                "# Éxodo\n\n## Capítulo 1\n\n### 1:1\n\n"
                "Estos *son* los nombres.\n\n"
                "> Nota: *son* se suple para completar la oración.\n",
                encoding="utf-8",
            )
            book = build_content["parsear_libro"](
                book_path,
                {
                    "exodo": {
                        "titulo": "Éxodo",
                        "testamento": "ot",
                        "orden": 1,
                    }
                },
            )

        self.assertEqual(
            book.capitulos[1],
            [("1", "Estos *son* los nombres.", ["*son* se suple para completar la oración."])],
        )


if __name__ == "__main__":
    unittest.main()
