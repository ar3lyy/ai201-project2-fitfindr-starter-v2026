"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

The scenarios below correspond to criteria 1–5 in criteria.md.
The empty-wardrobe diagnostic was tested separately in Milestone 2.
"""

SCENARIOS = [
    {
        "name": "matching query completes all three tools",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        "name": "impossible query stops before outfit tool",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        "name": "selected item matches outfit tool input",
        "query": "vintage graphic tee under $30, size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "fit card includes accurate descriptive details",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "all search results respect maximum price",
        "query": "graphic tee under $20",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed before a long run."""
    problems = []

    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")

        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe "
                f"{scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )

    return problems