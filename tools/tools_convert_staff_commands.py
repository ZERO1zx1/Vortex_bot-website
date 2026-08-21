from pathlib import Path
import re


def find_root(start: str) -> Path:
    """Tools/ хоттасаас ажиллахэд ч project root-г хамх: cogs/ байгаа хүртэл дээшээ өөр."""
    d = Path(start).resolve()
    while not (d / "cogs").is_dir():
        if d.parent == d:
            break
        d = d.parent
    return d


ROOT = find_root(__file__)

for name in ("cogs/admin.py", "cogs/moderation.py"):
    path = ROOT / name
    text = path.read_text()
    anchor = "from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR"
    if "from utils.slash_context import SlashContext" not in text:
        text = text.replace(anchor, anchor + "\nfrom utils.slash_context import SlashContext")
    text = text.replace("@commands.has_permissions", "@app_commands.checks.has_permissions")
    text = text.replace("@commands.hybrid_command(", "@app_commands.command(")
    text = text.replace(", with_app_command=True", "")
    # Slash commands do not support prefix aliases; retain canonical names only.
    text = re.sub(r", aliases=\[[^\]]*\]", "", text)
    lines = text.splitlines()
    output = []
    in_command = False
    for line in lines:
        if line.startswith("    @app_commands.command("):
            in_command = True
        if in_command and line.startswith("    async def ") and "(self, ctx" in line:
            line = line.replace("(self, ctx", "(self, interaction", 1)
            output.append(line)
            output.append("        ctx = SlashContext(interaction)")
            in_command = False
            continue
        output.append(line)
    path.write_text("\n".join(output) + "\n")
