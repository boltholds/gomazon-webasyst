from dataclasses import dataclass
import re


def clean_legacy_phone(value: str) -> str:
    value = value.strip()
    for char in "+-()":
        value = value.replace(char, "")
    return re.sub(r"(\d)\s+(\d)", r"\1\2", value)


@dataclass(slots=True, frozen=True)
class LegacyPhonePrefixPolicy:
    input_code: str = ""
    output_code: str = ""

    def candidates(self, value: str) -> tuple[str, ...]:
        direct = clean_legacy_phone(value)
        candidates = [direct]
        if not (self.input_code.isdigit() and self.output_code.isdigit()):
            return tuple(candidates)

        is_international = value.startswith("+")
        transformed = direct
        if not is_international and direct.startswith(self.input_code):
            transformed = self.output_code + direct[len(self.input_code) :]
        elif is_international and direct.startswith(self.output_code):
            transformed = self.input_code + direct[len(self.output_code) :]

        if transformed != direct:
            candidates.append(transformed)
        return tuple(candidates)
