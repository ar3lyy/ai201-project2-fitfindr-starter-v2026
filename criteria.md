# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
The provided target is 4 of 5 because the outfit and caption tools call a model,
so an occasional failed or empty response could prevent the full
run from finishing. The agent should still complete most matching
requests successfully.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
I chose 5 of 5 because checking whether search returned an empty
list is a fixed rule in the code. When nothing matches, the agent
should always stop and explain what the user could change.

---

## 3. The selected item reaches the outfit tool unchanged

For each run that finds a listing, the ID in session["selected_item"]
must match the ID of the new_item actually received by suggest_outfit —
5 of 5 tries.

**Why this target:**
I expect the correct item to be passed along every time. If search finds
a shirt but the outfit tool receives a different item, the suggestions
would be for something I did not select. Passing a saved item between
tools should not depend on the model's wording.



---
## 4. Fit cards are descriptive and include listing details

For five runs that produce a fit card, each caption must contain
2–4 sentences, describe the selected item using at least one accurate
color or style detail, and include its correct price and listing
platform — 5 of 5 tries.

**Why this target:**
I want every caption to describe the item clearly and tell me its price
and where to find it. The wording can change, but these details should
be included every time because they are provided in the listing.


---
## 5. Search respects the maximum price

For five searches with a maximum price, every listing returned by
search_listings must have a price less than or equal to that maximum —
5 of 5 tries.


**Why this target:**
I chose 5 of 5 because the budget is a firm limit. Even one result above
my budget would be irritating because it is not what I asked for.
The tool filters numeric prices, so it should enforce this limit every time.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
