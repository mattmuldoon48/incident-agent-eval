from pathlib import Path


def search_markdown_runbooks(runbook_dir: Path, query: str, limit: int = 3) -> list[dict[str, str | int]]:
    terms = [term.lower() for term in query.replace("-", " ").split() if len(term) > 2]
    matches: list[dict[str, str | int]] = []
    for path in sorted(runbook_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score == 0:
            continue
        snippet = text[:700].strip()
        matches.append({"source": path.name, "score": score, "snippet": snippet})
    return sorted(matches, key=lambda item: int(item["score"]), reverse=True)[:limit]
