"""Преобразование учебного конфигурационного языка в JSON."""

import argparse
import json
import sys
from pathlib import Path

from lark import Lark, Transformer, exceptions, v_args


GRAMMAR = Path(__file__).with_name("grammar.lark")
PARSER = Lark.open(GRAMMAR, parser="lalr", maybe_placeholders=False)


class ConfigError(ValueError):
    """Ошибка вычисления конфигурации."""


def require_integers(left, right):
    if not isinstance(left, int) or not isinstance(right, int):
        raise ConfigError("операции + и - требуют двух чисел")


@v_args(inline=True)
class Evaluate(Transformer):
    def __init__(self):
        super().__init__()
        self.constants = {}

    def start(self, *entries):
        if entries and entries[-1] is not None:
            return entries[-1]
        return self.constants

    def declaration(self, name, value):
        if name in self.constants:
            raise ConfigError(f"константа «{name}» уже объявлена")
        self.constants[str(name)] = value

    def reference(self, name):
        if name not in self.constants:
            raise ConfigError(f"константа «{name}» ещё не объявлена")
        return self.constants[name]

    def hexadecimal(self, token):
        return int(token, 16)

    def decimal(self, token):
        return int(token, 10)

    def string(self, token):
        return str(token)[2:-2]

    def array(self, *items):
        return list(items)

    def add(self, left, right):
        require_integers(left, right)
        return left + right

    def subtract(self, left, right):
        require_integers(left, right)
        return left - right

    def length(self, _function, value):
        if not isinstance(value, (str, list)):
            raise ConfigError("len() принимает строку или массив")
        return len(value)


def convert(source):
    """Разобрать вход и вычислить значение для записи в JSON."""
    tree = PARSER.parse(source)
    try:
        return Evaluate().transform(tree)
    except exceptions.VisitError as error:
        if isinstance(error.orig_exc, ValueError):
            raise ConfigError(str(error.orig_exc)) from error
        raise


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "-o", "--output", required=True, type=Path, help="путь к JSON-файлу"
    )
    args = cli.parse_args()
    try:
        source = sys.stdin.buffer.read().decode("utf-8-sig")
        content = json.dumps(convert(source), ensure_ascii=False, indent=2)
        args.output.write_text(content + "\n", encoding="utf-8")
    except exceptions.UnexpectedInput as error:
        location = f"строка {error.line}, столбец {error.column}"
        print(f"Синтаксическая ошибка ({location}).", file=sys.stderr)
        print(error.get_context(source).rstrip(), file=sys.stderr)
        return 1
    except (OSError, ValueError, RecursionError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
