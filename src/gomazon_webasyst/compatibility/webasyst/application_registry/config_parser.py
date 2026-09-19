from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import re

from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyPhpConfigError,
    LegacyPhpConfigLimitError,
    LegacyPhpConfigSyntaxError,
    LegacyPhpConfigUnsupportedExpression,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayAutoKey,
    PhpArrayEntry,
    PhpArrayIntKey,
    PhpArrayStringKey,
    PhpNull,
    PhpValue,
)


DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_TOKENS = 100_000
DEFAULT_MAX_ENTRIES = 20_000


class _TokenKind(Enum):
    OPEN_TAG = auto()
    IDENT = auto()
    STRING = auto()
    INT = auto()
    FLOAT = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    FAT_ARROW = auto()
    COMMA = auto()
    SEMICOLON = auto()
    EOF = auto()


@dataclass(slots=True, frozen=True)
class _Token:
    kind: _TokenKind
    value: str
    offset: int


_NUMBER = re.compile(r"[+-]?(?:\d+\.\d+|\d+)")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class _Tokenizer:
    def __init__(self, source: str, *, max_tokens: int) -> None:
        self._source = source
        self._index = 0
        self._max_tokens = max_tokens
        self._tokens: list[_Token] = []

    def tokenize(self) -> tuple[_Token, ...]:
        while True:
            self._skip_ignored()
            if self._index >= len(self._source):
                self._append(_TokenKind.EOF, "", self._index)
                return tuple(self._tokens)

            offset = self._index
            if self._source.startswith("<?php", self._index):
                self._index += 5
                self._append(_TokenKind.OPEN_TAG, "<?php", offset)
                continue
            if self._source.startswith("=>", self._index):
                self._index += 2
                self._append(_TokenKind.FAT_ARROW, "=>", offset)
                continue

            char = self._source[self._index]
            punctuation = {
                "(": _TokenKind.LPAREN,
                ")": _TokenKind.RPAREN,
                "[": _TokenKind.LBRACKET,
                "]": _TokenKind.RBRACKET,
                ",": _TokenKind.COMMA,
                ";": _TokenKind.SEMICOLON,
            }
            if char in punctuation:
                self._index += 1
                self._append(punctuation[char], char, offset)
                continue
            if char in {"'", '"'}:
                self._append(_TokenKind.STRING, self._read_string(char), offset)
                continue

            number = _NUMBER.match(self._source, self._index)
            if number:
                text = number.group(0)
                self._index = number.end()
                kind = _TokenKind.FLOAT if "." in text else _TokenKind.INT
                self._append(kind, text, offset)
                continue

            ident = _IDENT.match(self._source, self._index)
            if ident:
                text = ident.group(0)
                self._index = ident.end()
                self._append(_TokenKind.IDENT, text, offset)
                continue

            if char == "$":
                raise LegacyPhpConfigUnsupportedExpression(
                    f"PHP variables are not supported at offset {offset}"
                )
            if char == ".":
                raise LegacyPhpConfigUnsupportedExpression(
                    f"PHP concatenation is not supported at offset {offset}"
                )
            if self._source.startswith("?>", self._index):
                raise LegacyPhpConfigUnsupportedExpression(
                    "PHP closing tag/trailing execution is not supported"
                )
            raise LegacyPhpConfigSyntaxError(
                f"unsupported token {char!r} at offset {offset}"
            )

    def _append(self, kind: _TokenKind, value: str, offset: int) -> None:
        if len(self._tokens) >= self._max_tokens:
            raise LegacyPhpConfigLimitError("PHP config token budget exceeded")
        self._tokens.append(_Token(kind=kind, value=value, offset=offset))

    def _skip_ignored(self) -> None:
        while self._index < len(self._source):
            char = self._source[self._index]
            if char.isspace():
                self._index += 1
                continue
            if self._source.startswith("//", self._index):
                newline = self._source.find("\n", self._index + 2)
                self._index = len(self._source) if newline < 0 else newline + 1
                continue
            if char == "#":
                newline = self._source.find("\n", self._index + 1)
                self._index = len(self._source) if newline < 0 else newline + 1
                continue
            if self._source.startswith("/*", self._index):
                end = self._source.find("*/", self._index + 2)
                if end < 0:
                    raise LegacyPhpConfigSyntaxError("unterminated block comment")
                self._index = end + 2
                continue
            return

    def _read_string(self, quote: str) -> str:
        self._index += 1
        chars: list[str] = []
        while self._index < len(self._source):
            char = self._source[self._index]
            if char == quote:
                self._index += 1
                return "".join(chars)
            if quote == '"' and char == "$":
                raise LegacyPhpConfigUnsupportedExpression(
                    f"double-quoted interpolation is not supported at offset {self._index}"
                )
            if char != "\\":
                chars.append(char)
                self._index += 1
                continue

            escape_offset = self._index
            self._index += 1
            if self._index >= len(self._source):
                raise LegacyPhpConfigSyntaxError(
                    f"unterminated escape at offset {escape_offset}"
                )
            escaped = self._source[self._index]
            self._index += 1

            if quote == "'":
                if escaped in {"'", "\\"}:
                    chars.append(escaped)
                else:
                    chars.extend(("\\", escaped))
                continue

            double_escapes = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                '"': '"',
                "\\": "\\",
                "$": "$",
            }
            if escaped in double_escapes:
                chars.append(double_escapes[escaped])
            else:
                chars.extend(("\\", escaped))

        raise LegacyPhpConfigSyntaxError("unterminated string literal")


class _Parser:
    def __init__(
        self,
        tokens: tuple[_Token, ...],
        *,
        max_depth: int,
        max_entries: int,
    ) -> None:
        self._tokens = tokens
        self._index = 0
        self._max_depth = max_depth
        self._max_entries = max_entries
        self._entry_count = 0

    def parse(self) -> PhpValue:
        if self._peek().kind is _TokenKind.OPEN_TAG:
            self._advance()

        token = self._expect(_TokenKind.IDENT)
        if token.value.lower() != "return":
            raise LegacyPhpConfigUnsupportedExpression(
                f"only a top-level return statement is supported at offset {token.offset}"
            )

        value = self._parse_value(depth=0)
        self._expect(_TokenKind.SEMICOLON)
        trailing = self._peek()
        if trailing.kind is not _TokenKind.EOF:
            raise LegacyPhpConfigUnsupportedExpression(
                f"trailing PHP statements are not supported at offset {trailing.offset}"
            )
        return value

    def _parse_value(self, *, depth: int) -> PhpValue:
        token = self._peek()
        if token.kind is _TokenKind.STRING:
            self._advance()
            return token.value
        if token.kind is _TokenKind.INT:
            self._advance()
            return int(token.value)
        if token.kind is _TokenKind.FLOAT:
            self._advance()
            return float(token.value)
        if token.kind is _TokenKind.LBRACKET:
            self._advance()
            return self._parse_array(_TokenKind.RBRACKET, depth=depth + 1)
        if token.kind is _TokenKind.IDENT:
            normalized = token.value.lower()
            if normalized == "true":
                self._advance()
                return True
            if normalized == "false":
                self._advance()
                return False
            if normalized == "null":
                self._advance()
                return PhpNull()
            if normalized == "array":
                self._advance()
                self._expect(_TokenKind.LPAREN)
                return self._parse_array(_TokenKind.RPAREN, depth=depth + 1)
            raise LegacyPhpConfigUnsupportedExpression(
                f"unsupported PHP expression {token.value!r} at offset {token.offset}"
            )
        raise LegacyPhpConfigSyntaxError(
            f"expected declarative value at offset {token.offset}"
        )

    def _parse_array(self, closing: _TokenKind, *, depth: int) -> PhpArray:
        if depth > self._max_depth:
            raise LegacyPhpConfigLimitError("PHP config nesting depth exceeded")

        entries: list[PhpArrayEntry] = []
        if self._peek().kind is closing:
            self._advance()
            return PhpArray(tuple(entries))

        while True:
            first = self._parse_value(depth=depth)
            if self._peek().kind is _TokenKind.FAT_ARROW:
                self._advance()
                key = self._array_key(first)
                value = self._parse_value(depth=depth)
            else:
                key = PhpArrayAutoKey()
                value = first

            self._entry_count += 1
            if self._entry_count > self._max_entries:
                raise LegacyPhpConfigLimitError("PHP config entry budget exceeded")
            entries.append(PhpArrayEntry(key=key, value=value))

            next_token = self._peek()
            if next_token.kind is closing:
                self._advance()
                return PhpArray(tuple(entries))
            if next_token.kind is not _TokenKind.COMMA:
                raise LegacyPhpConfigSyntaxError(
                    f"expected comma or closing delimiter at offset {next_token.offset}"
                )
            self._advance()
            if self._peek().kind is closing:
                self._advance()
                return PhpArray(tuple(entries))

    @staticmethod
    def _array_key(value: PhpValue) -> PhpArrayStringKey | PhpArrayIntKey:
        if isinstance(value, str):
            return PhpArrayStringKey(value)
        if type(value) is int:
            return PhpArrayIntKey(value)
        raise LegacyPhpConfigUnsupportedExpression(
            "only string and integer PHP array keys are supported"
        )

    def _peek(self) -> _Token:
        return self._tokens[self._index]

    def _advance(self) -> _Token:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _expect(self, kind: _TokenKind) -> _Token:
        token = self._peek()
        if token.kind is not kind:
            raise LegacyPhpConfigSyntaxError(
                f"expected {kind.name} at offset {token.offset}, got {token.kind.name}"
            )
        return self._advance()


def parse_php_return_value(
    source: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> PhpValue:
    if len(source.encode("utf-8")) > max_bytes:
        raise LegacyPhpConfigLimitError("PHP config byte budget exceeded")
    if min(max_bytes, max_depth, max_tokens, max_entries) <= 0:
        raise ValueError("parser safety limits must be positive")

    tokens = _Tokenizer(source, max_tokens=max_tokens).tokenize()
    return _Parser(
        tokens,
        max_depth=max_depth,
        max_entries=max_entries,
    ).parse()


__all__ = [
    "LegacyPhpConfigError",
    "LegacyPhpConfigLimitError",
    "LegacyPhpConfigSyntaxError",
    "LegacyPhpConfigUnsupportedExpression",
    "parse_php_return_value",
]
