import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lark.exceptions import UnexpectedInput

from src.main import ConfigError, convert


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_literals_and_nesting(self):
        source = "' comment\r\nlist(0xAf, 0X0, [[о'кей]], list(), list([[]]))"
        self.assertEqual(convert(source), [175, 0, "о'кей", [], [""]])

    def test_declarations(self):
        source = "const first = 0xA\nconst next = $first + 1$"
        self.assertEqual(convert(source), {"first": 10, "next": 11})

    def test_expressions_in_nested_arrays(self):
        source = """
            const text = [[кот]]
            const data = list(0x9, $len(text)$)
            list($len(data)$, list($10 - 3 - 2$, $len(list($text$))$),
                 $(0xA - (2 + 3)) + 1$, $data$)
        """
        self.assertEqual(convert(source), [2, [5, 1], 6, [9, 3]])

    def test_invalid_syntax(self):
        sources = [
            "12", "list(0x1 0x2)", "list(0x1,)", "list(",
            "0xG", "0x1z", "const A = 0x1", "constant=0x1",
            "[[unfinished", "$1 +$", "$1 * 2$", "0x1 0x2",
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(UnexpectedInput):
                    convert(source)

    def test_invalid_expressions(self):
        sources = [
            "$missing$", "const a = 0x0 const a = 0x1",
            "$len(0x1)$", "$[[text]] + 1$", "$1 - list()$",
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(ConfigError):
                    convert(source)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, source, output):
        return subprocess.run(
            [sys.executable, str(ROOT / "src/main.py"), "-o", str(output)],
            input=source,
            capture_output=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_examples(self):
        cases = {
            "library": [
                "Городская библиотека", [2, ["Абонемент", "Читальный зал"]],
                32,
            ],
            "greenhouse": [
                "Теплица", [23, 29],
                [3, ["температура", "влажность", "свет"]],
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "result.json"
            for name, expected in cases.items():
                with self.subTest(name=name):
                    example = ROOT / "examples" / f"{name}.cfg"
                    result = self.run_cli(example.read_text("utf-8"), output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(output.read_text("utf-8")),
                                     expected)

    def test_syntax_error_preserves_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "result.json"
            output.write_text("[]", encoding="utf-8")
            result = self.run_cli("' comment\nlist(0x1 0x2)", output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("строка 2, столбец", result.stderr)
            self.assertEqual(output.read_text("utf-8"), "[]")


if __name__ == "__main__":
    unittest.main()
