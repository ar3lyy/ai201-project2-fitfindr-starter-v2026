#!/usr/bin/env python3
"""
Run your scenarios repeatedly and write the results down. ← UNIT 4

    python run_eval.py --label before      five tries, the default
    python run_eval.py --label after       after your improvement
    python run_eval.py --tries 10          more tries

This does the mechanical half of unit 4 for you. It runs every scenario in
`scenarios.py` five separate times, with caching off, captures the trace and
session for each, and writes everything into results/.

What it does NOT do is decide whether a try passed. The Try and Verdict
columns remain blank for manual scoring against criteria.md.

Additional evidence:
- Actual tool-call counts, captured with wrappers around the real calls.
- The item actually received by suggest_outfit.
- The complete saved session, including every search result.

The wrappers call the real functions. They do not supply fake responses.
"""

import argparse
import datetime as dt
import json
import sys
import traceback
from copy import deepcopy
from unittest.mock import patch

import config
import scenarios as scenario_module


def run_once(scenario, use_trace=True):
    """Run one real agent interaction and record evidence."""
    import agent
    import trace as trace_module
    from utils.data_loader import (
        get_example_wardrobe,
        get_empty_wardrobe,
    )

    wardrobe = (
        get_empty_wardrobe()
        if scenario["wardrobe"] == "empty"
        else get_example_wardrobe()
    )

    if use_trace:
        trace_module.start_trace()

    record = {
        "error": None,
        "session": None,
        "trace": "",
        "crashed": None,
        "tool_calls": {
            "search_listings": 0,
            "suggest_outfit": 0,
            "create_fit_card": 0,
        },
        "outfit_received_item": None,
        "selected_item_matches_received": None,
    }

    real_call_tool = agent.call_tool
    real_suggest_outfit = agent.suggest_outfit
    real_create_fit_card = agent.create_fit_card

    def observed_call_tool(name, arguments):
        if name == "search_listings":
            record["tool_calls"]["search_listings"] += 1
        return real_call_tool(name, arguments)

    def observed_suggest_outfit(new_item, wardrobe):
        record["tool_calls"]["suggest_outfit"] += 1
        record["outfit_received_item"] = deepcopy(new_item)
        return real_suggest_outfit(new_item, wardrobe)

    def observed_create_fit_card(outfit, new_item):
        record["tool_calls"]["create_fit_card"] += 1
        return real_create_fit_card(outfit, new_item)

    try:
        with (
            patch.object(agent, "call_tool", observed_call_tool),
            patch.object(
                agent, "suggest_outfit", observed_suggest_outfit
            ),
            patch.object(
                agent, "create_fit_card", observed_create_fit_card
            ),
        ):
            record["session"] = agent.run_agent(
                scenario["query"], wardrobe
            )

        session = record["session"]
        received = record["outfit_received_item"]

        if received is not None:
            record["selected_item_matches_received"] = (
                session["selected_item"] == received
            )

    except Exception as exc:
        record["crashed"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()

    if use_trace:
        record["trace"] = trace_module.get_trace()

    return record


def main():
    parser = argparse.ArgumentParser(
        description="Run the scenarios and log the results."
    )
    parser.add_argument(
        "--tries",
        "--trials",
        type=int,
        default=5,
        dest="tries",
        help="tries per scenario (default 5)",
    )
    parser.add_argument(
        "--label",
        default="",
        help="a name for this run, e.g. before",
    )
    args = parser.parse_args()

    problems = scenario_module.validate()

    if problems:
        print("scenarios.py has problems:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        sys.exit(1)

    if not scenario_module.SCENARIOS:
        print("scenarios.py is empty.", file=sys.stderr)
        sys.exit(1)

    if args.tries < 1:
        parser.error("--tries must be at least 1")

    if args.tries < 5:
        print(
            f"Warning: {args.tries} tries. "
            "Your criteria are written out of five.\n"
        )

    # Five tries must be five real model responses.
    config.CACHE_ENABLED = False
    print("Cache is OFF for this run — that's deliberate.\n")

    rows = []

    for scenario in scenario_module.SCENARIOS:
        print(
            f"{scenario['name']} "
            f"({scenario['wardrobe']} wardrobe)"
        )
        print(f"  query: {scenario['query']}")

        tries = []

        for attempt in range(1, args.tries + 1):
            record = run_once(scenario)
            tries.append(record)

            if record["crashed"]:
                print(
                    f"  try {attempt}: CRASHED — "
                    f"{record['crashed']}"
                )
            else:
                session = record["session"] or {}

                if session.get("error"):
                    print(
                        f"  try {attempt}: stopped early — "
                        f"{str(session['error'])[:80]}"
                    )
                else:
                    card = session.get("fit_card") or ""
                    print(
                        f"  try {attempt}: completed — "
                        f"fit card {len(card)} chars"
                    )

        rows.append({"scenario": scenario, "tries": tries})
        print()

    write_report(rows, args)


def write_report(rows, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)

    # Include seconds so separate reports do not overwrite each other.
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"run_{stamp}{label}.md"

    n = args.tries
    headers = " | ".join(f"Try {i}" for i in range(1, n + 1))
    divider = "|".join(["---"] * n)

    lines = [
        f"# Run log — {args.label or 'unlabeled'}",
        "",
        "- Produced by: `run_eval.py::main`",
        "- Evidence captured by: `run_eval.py::run_once`",
        "- Loop: `agent.py::run_agent`",
        "- Search: `mcp_server.py::search_listings` via MCP",
        "- Model tools: `tools.py::suggest_outfit` and "
        "`tools.py::create_fit_card`",
        f"- Tries per scenario: {n}, caching off",
        f"- Temperature: {config.TEMPERATURE}",
        f"- When: {dt.datetime.now().isoformat(timespec='seconds')}",
        "",
        "Fill in targets from criteria.md. Score each try from the "
        "evidence below, then count passes for the verdict.",
        "",
        f"| Criterion | Target | {headers} | Verdict |",
        f"|---|---|{divider}|---|",
    ]

    for row in rows:
        scenario = row["scenario"]
        number = scenario.get("criterion")
        name = (
            f"{number}. {scenario['name']}"
            if number
            else f"{scenario['name']} (diagnostic)"
        )
        cells = " | ".join([" "] * n)
        lines.append(f"| {name} |  | {cells} |  |")

    lines += [
        "",
        "> PASS/FAIL and Verdict are deliberately left blank. "
        "Apply the original criteria to the recorded evidence.",
        "",
        "---",
        "",
        "## What actually happened",
        "",
    ]

    for row in rows:
        scenario = row["scenario"]
        lines += [
            f"### {scenario['name']}",
            "",
            f"- Query: `{scenario['query']}`",
            f"- Wardrobe: {scenario['wardrobe']}",
            "",
        ]

        for i, record in enumerate(row["tries"], 1):
            lines += [f"**Try {i}**", ""]

            calls = record["tool_calls"]
            lines += [
                "Actual tool-call counts:",
                "",
                "```text",
                f"search_listings (via MCP): {calls['search_listings']}",
                f"suggest_outfit: {calls['suggest_outfit']}",
                f"create_fit_card: {calls['create_fit_card']}",
                "```",
                "",
            ]

            if record["crashed"]:
                lines += [
                    "Crashed:",
                    "",
                    "```text",
                    record["crashed"],
                    record.get("traceback", ""),
                    "```",
                    "",
                ]

            session = record["session"]

            if session is not None:
                selected = session.get("selected_item") or {}
                received = record["outfit_received_item"] or {}

                lines += [
                    "Item handoff evidence:",
                    "",
                    "```text",
                    f"Saved item ID: {selected.get('id')}",
                    f"Received item ID: {received.get('id')}",
                    "Full item matches: "
                    f"{record['selected_item_matches_received']}",
                    "```",
                    "",
                    "Complete session, including all search results:",
                    "",
                    "```json",
                    json.dumps(session, indent=2, ensure_ascii=False),
                    "```",
                    "",
                ]

            if record["trace"]:
                lines += [
                    "Trace:",
                    "",
                    "```text",
                    record["trace"],
                    "```",
                    "",
                ]

    path.write_text("\n".join(lines), encoding="utf-8")

    import generate

    print(f"Wrote {path.relative_to(config.ROOT)}")
    print(generate.usage())
    print("\nCommit this file. It is evidence of the actual runs.")


if __name__ == "__main__":
    main()