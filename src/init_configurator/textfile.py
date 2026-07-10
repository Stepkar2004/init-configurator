"""Write generated files with LF endings, on every OS.

``Path.write_text`` opens the file with ``newline=None``, which turns on
universal-newline translation *on write*: every newline in the content becomes
``os.linesep``, which on Windows means CRLF. So a project scaffolded on Windows
received CRLF in every file init-configurator generated, and a fresh Node
scaffold then failed its own ``biome check`` -- whose formatter defaults to LF --
before a single line of code was written.

Generated files are inputs to other tools, and those tools expect LF. Nothing
this package writes should pick its line ending from the machine it happens to
run on, so every write goes through here rather than through ``write_text``.

The repo's own ``.gitattributes`` closes the other half of the same gap: what
this module writes, git must not rewrite on checkout.
"""

from pathlib import Path


def write_text_lf(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` as UTF-8 with LF endings, on every platform."""
    path.write_text(content, encoding="utf-8", newline="\n")
