"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def parse_query(query: str) -> dict:
    """Extract a description, optional size, and optional maximum price."""
    description = query.strip()
    max_price = None
    size = None

    price_match = re.search(
        r"\b(?:under|below|up to|at most)\s*\$?\s*"
        r"(\d+(?:\.\d{1,2})?)(?![\d.])",
        description,
        flags=re.IGNORECASE,
    )

    if price_match:
        max_price = float(price_match.group(1))
        description = (
            description[:price_match.start()]
            + " "
            + description[price_match.end():]
        )

    size_match = re.search(
        r"\b(?:in\s+)?size\s+"
        r"([a-z0-9]+(?:[./-][a-z0-9]+)*(?:\s+L\d+)?)\b",
        description,
        flags=re.IGNORECASE,
    )

    if size_match:
        size = size_match.group(1).upper()
        description = (
            description[:size_match.start()]
            + " "
            + description[size_match.end():]
        )

    # Remove common request wording rather than treating it as search keywords.
    description = re.sub(
        r"^\s*(?:i(?:'m| am)\s+)?"
        r"(?:looking for|searching for|find me|find|show me)"
        r"\s+",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"^\s*(?:a|an|some)\s+",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\s+", " ", description).strip(" ,")

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    count = 0

    while session["fit_card"] is None:
        count += 1
        trace.check_iterations(count)

        if not session["parsed"]:
            session["parsed"] = parse_query(session["query"])

            if not session["parsed"]["description"]:
                session["error"] = (
                    "Please describe the clothing you want, such as "
                    "'graphic tee', along with an optional size and budget."
                )
                return session

        elif session["selected_item"] is None:
            session["search_results"] = call_tool(
                "search_listings",
                {
                    "description": session["parsed"]["description"],
                    "size": session["parsed"]["size"],
                    "max_price": session["parsed"]["max_price"],
                },
            )

            if not session["search_results"]:
                session["error"] = (
                    "No listings matched your search. Try different "
                    "clothing keywords, another size, or a higher "
                    "maximum price."
                )
                return session

            session["selected_item"] = session["search_results"][0]

        elif session["outfit_suggestion"] is None:
            session["outfit_suggestion"] = suggest_outfit(
                new_item=session["selected_item"],
                wardrobe=session["wardrobe"],
            )

            if not session["outfit_suggestion"].strip():
                session["error"] = (
                    "The outfit tool returned no suggestions. "
                    "Please try your request again."
                )
                return session

        else:
            session["fit_card"] = create_fit_card(
                outfit=session["outfit_suggestion"],
                new_item=session["selected_item"],
            )

            if not session["fit_card"].strip():
                session["fit_card"] = None
                session["error"] = (
                    "The caption tool returned no caption. "
                    "Please try your request again."
                )
                return session

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )