"""Read the generated command data without executing any JavaScript."""
import ast
import re

JS_STRING = r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"


def closing_delimiter(source: str, start: int) -> int:
    """Locate the matching bracket, ignoring quoted string contents."""
    pairs = {"[": "]", "{": "}", "(": ")"}
    stack = []
    quote = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or stack.pop() != char:
                raise ValueError("Unbalanced JavaScript data")
            if not stack:
                return index
    raise ValueError("Unterminated JavaScript data")


def command_array_bounds(source: str) -> tuple[int, int]:
    match = re.search(r"\b(?:const|let|var)\s+COMMANDS\s*=\s*\[", source)
    if not match:
        raise ValueError("COMMANDS array not found")
    start = match.end() - 1
    return start, closing_delimiter(source, start)


def command_rows(source: str) -> list[dict[str, str]]:
    """Extract literal string fields from each top-level command object."""
    start, end = command_array_bounds(source)
    rows = []
    index = start + 1
    fields = ("name", "cat", "icon", "desc", "descEN", "example")
    while index < end:
        if source[index] in " \t\r\n,":
            index += 1
            continue
        if source[index] != "{":
            raise ValueError("COMMANDS must contain literal objects")
        object_end = closing_delimiter(source, index)
        blob = source[index:object_end + 1]
        row = {}
        for field in fields:
            match = re.search(
                rf"(?:\b{field}|\"{field}\"|'{field}')\s*:\s*({JS_STRING})", blob,
            )
            if match:
                row[field] = ast.literal_eval(match.group(1))
        if not row.get("name"):
            raise ValueError("Command object has no literal name")
        rows.append(row)
        index = object_end + 1
    return rows
