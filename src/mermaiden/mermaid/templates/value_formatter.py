import base64
import json
import re
from dataclasses import dataclass
from typing import ClassVar

from wireup import injectable


@injectable
@dataclass(frozen=True, slots=True)
class MermaidValueFormatter:
    identifier_pattern: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

    def identifier(self, value: object, namespace: str) -> str:
        text = str(value)
        token = (
            f"v_{text}"
            if self.identifier_pattern.fullmatch(text)
            else f"b_{base64.b32encode(text.encode()).decode().rstrip('=').lower()}"
        )
        return f"{namespace}_{token}"

    def quote(self, value: object) -> str:
        return json.dumps(str(value), ensure_ascii=False)

    def entity_quote(self, value: object) -> str:
        escaped = "".join(self._entity_character(character) for character in str(value))
        return f'"{escaped}"'

    def class_text(self, value: object) -> str:
        return "".join(
            character if character.isalnum() or character in " _-.,/;" else f"#{ord(character)};"
            for character in str(value)
        )

    def number(self, value: float | int) -> str:
        return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)

    def tree_label(self, value: object) -> str:
        text = str(value)
        if not text or text != text.strip() or "  " in text or any(token in text for token in ('"', ":::", "##")):
            return json.dumps(text, ensure_ascii=False)
        return text

    def _entity_character(self, character: str) -> str:
        if character == '"':
            return "#quot;"
        codepoint = ord(character)
        if character in "#&<>" or codepoint < 32 or codepoint == 127:
            return f"#{codepoint};"
        return character
