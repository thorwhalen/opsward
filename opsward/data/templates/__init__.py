"""Generation templates organized by target project type.

``shared/`` holds templates (and installable Claude Code skills) that apply to
any project; ``python/`` and ``jsts/`` hold language-specific variants. The
generator reads these via ``importlib.resources`` and substitutes
``${variable}`` placeholders (``string.Template``) before writing to a target.
"""
