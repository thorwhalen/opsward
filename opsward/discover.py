"""Optional cross-repo asset discovery, delegating to the ``toolery`` package.

opsward scans and *scores* the AI setup of one repo; this adds *finding* assets — skills,
subagents, docs — across one or more repos. It is opt-in and keeps opsward's core
dependency-light: ``pip install 'opsward[discovery]'`` pulls in ``toolery`` (add
``toolery[ir]`` for semantic search). Conceptually this is opsward's per-repo/fleet
orchestration meeting toolery's discovery engine (epic #12 → #13).
"""

from __future__ import annotations

from pathlib import Path


def _require_toolery():
    """Import ``toolery`` or raise an actionable error naming the extra to install."""
    try:
        import toolery
    except ImportError as e:  # pragma: no cover - only without the extra installed
        raise ImportError(
            "opsward's discovery feature needs the 'toolery' package. "
            "Install it with:  pip install 'opsward[discovery]'"
        ) from e
    return toolery


def find_assets(
    *roots,
    query: str,
    kinds="skill,agent",
    semantic: bool = False,
    limit: int = 10,
):
    """Find assets matching ``query`` across one or more project ``roots``.

    Harvests the requested ``kinds`` (comma-separated string or a sequence of
    ``"skill"``/``"agent"``/``"doc"``) from each root via ``toolery`` and returns ranked
    ``(Card, score)`` results. With ``semantic=True``, uses ``toolery``'s ir federated
    backend (needs ``toolery[ir]``). Defaults to the current directory when no roots given.
    """
    toolery = _require_toolery()
    if isinstance(kinds, str):
        kinds = [k.strip() for k in kinds.split(",") if k.strip()]
    harvesters = {
        "skill": toolery.skills,
        "agent": toolery.agents,
        "doc": toolery.folder,
    }
    sources = []
    for root in roots or (".",):
        root_path = str(Path(root).expanduser())
        for kind in kinds:
            harvester = harvesters.get(kind)
            if harvester is not None:
                sources.append(harvester(root_path))
    backend = toolery.IrFederatedBackend() if semantic else None
    if backend is not None:
        cat = toolery.catalog(*sources, search_backend=backend)
    else:
        cat = toolery.catalog(*sources)
    return cat.search(query, limit=limit)
