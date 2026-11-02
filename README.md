# FitFindr

Read [RUNNING.md](RUNNING.md) for setup, commands, and troubleshooting.

<!-- UNIT 3 — THE BUILD -->

## What This Does

FitFindr helps users find thrift listings based on a clothing description, optional size, and budget. It searches a local dataset of 40 listings and suggests outfits using a saved wardrobe. It then writes a short caption describing the find, including its price and listing platform. When no listings match, it stops and suggests changing the clothing keywords, size, or maximum price.

To run it after completing the setup in RUNNING.md:

```bash
source .venv/bin/activate
python app.py ask 'vintage graphic tee under $30, size M'
```

To run the two built-in examples:

```bash
python agent.py
```

---

## Tool Inventory

### `search_listings`

- **What it does:** Loads listings using `load_listings()`, filters by optional size and maximum price, and ranks matches by keyword overlap with the title, description, and style tags.
- **Inputs:** `description` (str), `size` (str or None; default None), and `max_price` (float or None; default None).
- **Returns:** A list of matching listing dictionaries, highest keyword score first, limited to `config.SEARCH_RESULT_LIMIT`. Each dictionary contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. The maximum price is inclusive. Size matching ignores capitalization and compares complete size tokens: M matches S/M, L does not match XL, and S does not match US 9. None skips the corresponding filter.
- **When it has nothing:** Returns an empty list, `[]`.

### `suggest_outfit`

- **What it does:** Calls the model through `generate()` to suggest one or two outfits combining the selected listing with wardrobe items.
- **Inputs:** `new_item` (dict containing a listing) and `wardrobe` (dict containing an `items` list of clothing dictionaries).
- **Returns:** A string containing the model's outfit suggestions. The prompt requests the selected item and specific pieces from the wardrobe, with an explanation of how they work together.
- **When it has nothing:** If the wardrobe's `items` list is empty, requests general styling advice without claiming the user owns the suggested pieces.

### `create_fit_card`

- **What it does:** Calls the model through `generate()` to write a short social caption based on the selected item and outfit suggestion.
- **Inputs:** `outfit` (str) and `new_item` (dict containing a listing).
- **Returns:** A caption string. The prompt requests 2–4 sentences mentioning the item, its correct price, and its platform once each, plus an accurate color or style detail.
- **When it has nothing:** If `outfit` is empty or contains only whitespace, returns `"Cannot create a fit card without an outfit suggestion."` without calling the model.

The model tools return the model's text after stripping surrounding whitespace. Their caption and outfit requirements are prompt instructions, not guarantees enforced by output validation. The agent checks for empty responses and stops with a message if one occurs.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, save a message in `session["error"]` suggesting the user change their description, size, or maximum price, then stop without calling `suggest_outfit` or `create_fit_card`. Otherwise, save the first result as `selected_item`, use it to suggest an outfit, and create a fit card, saving and reading each result through the session.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** `agent.py::parse_query` uses regular expressions. It extracts a price after wording such as "under," "below," "up to," or "at most," and extracts a size following "size." It removes those parts and common request wording from the description. For example, `vintage graphic tee under $30, size M` becomes description `vintage graphic tee`, size `M`, and maximum price `30.0`. This parser handles these patterns rather than every possible way someone might phrase a request.

**What moves through the session:**

1. The original query and wardrobe are saved when the session starts.
2. The extracted description, size, and maximum price are saved in `parsed`.
3. Search reads `parsed` and saves its output in `search_results`.
4. The first search result is saved in `selected_item`.
5. The outfit tool reads `selected_item` and `wardrobe`, then saves its output in `outfit_suggestion`.
6. The caption tool reads `outfit_suggestion` and `selected_item`, then saves its output in `fit_card`.

The loop checks the session to decide which step to perform next. Each iteration calls `trace.check_iterations(count)` to enforce the configured iteration limit. It also stops early for an empty description or an empty model response.

**Session verification:** I wrapped `suggest_outfit` with `unittest.mock.patch` using `wraps`, so the real tool still ran while its input was captured. I compared the received item with the selected item saved in the session. Both IDs were `lst_002`, and the full dictionaries matched. This verifies one development run; it is not the five-run evaluation for Unit 4.

---

## Sample Run

### Milestone 1: Starter check

All 10 environment checks passed. I inspected six listings and reviewed fields including title, description, style_tags, size, and price. The wardrobe stores clothing in an items list; an empty wardrobe is `{"items": []}`.

Before implementing the loop, the starter produced:

```text
$ python app.py ask 'vintage graphic tee under $30'

  The planning loop isn't built yet — see the TODO in agent.py.

0 model calls this session
```

### Full agent run

Command: `python agent.py`

The first built-in query is `looking for a vintage graphic tee under $30`. The second is `designer ballgown size XXS under $5`. This output comes from `agent.py::run_agent`, displayed by `agent.py::_show`.

```text
$ python agent.py
=== A query the data can match ===
  found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
  outfit:   Here is a stylish Y2K-inspired outfit using the baby tee and pieces from your wardrobe:

### The Outfit: Y2K Streetwear Contrast

*   **Selected Item:** Y2K Baby Tee — Butterfly Print (white, pink, purple)
*   **Wardrobe Piece 1:** Baggy straight-leg jeans, dark wash (`w_001`)
*   **Wardrobe Piece 2:** Vintage black denim jacket (`w_006`)
*   **Wardrobe Piece 3:** Chunky white sneakers (`w_007`)
*   **Wardrobe Piece 4:** Black crossbody bag (`w_010`)

### Why It Works:
*   **Proportion Play:** The fitted, cropped cut of the baby tee balances out the high-waisted, relaxed silhouette of the baggy dark-wash jeans, nailing that classic early 2000s streetwear aesthetic.
*   **Color Harmony:** The white base and pink/purple tones of the butterfly graphic pop against the dark indigo denim, while the white chunky sneakers tie the white elements of the shirt together.
*   **Texture & Layering:** Throwing on the slightly cropped vintage black denim jacket adds an extra layer of Y2K grunge texture without hiding the waistline of the jeans, completed simply with the black crossbody bag.
  fit card: Found this super cute Y2K butterfly print baby tee for just $18, and I am obsessed with the pink and purple details! I styled it with baggy denim and a vintage jacket for the ultimate early 2000s streetwear vibe. Now live on Depop, so grab it before I change my mind!

=== A query it can't ===
  stopped: No listings matched your search. Try different clothing keywords, another size, or a higher maximum price.
  fit_card is None — it should still be None here

The second one should stop before the fit card. If both paths look the same,
the branch isn't doing anything yet.
```

The successful path returned an outfit and caption. The impossible query stopped with a useful message and left `fit_card` as None.

One caption limitation is that "Now live on Depop" makes the user sound like the seller, although the user is looking for something to buy. This wording needs further evaluation.

### The three tools, tested one at a time

#### Search listings

```text
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

All returned listings were within the $30 maximum. However, keyword matching also returned a mesh top and cargo pants because their descriptions mention a tee. This is a search relevance limitation.

Empty-search check:

```text
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"

[]
```

#### Suggest an outfit

```text
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"

Here is an outfit featuring the selected item and pieces from your wardrobe:

### **Outfit: Casual Streetwear Classic**
* **Selected Item:** Vintage Levi's 501 Jeans — Medium Wash (`lst_001`)
* **Wardrobe Pieces Used:**
  * White ribbed tank top (`w_003`)
  * Oversized grey crewneck sweatshirt (`w_004`)
  * Chunky white sneakers (`w_007`)
  * Black crossbody bag (`w_010`)

**Why it works:**
* **Style Harmony:** The straight-leg fit of the classic Levi's 501s leans right into a vintage streetwear aesthetic. Pairing them with a fitted white ribbed tank top creates a balanced silhouette against the slouchy, oversized drape of the grey crewneck sweatshirt (which you can wear over your shoulders or layered). Finishing with chunky white sneakers keeps the vibe effortlessly casual and cohesive.
* **Color Palette:** The medium blue wash of the denim acts as a neutral base that pairs effortlessly with the crisp white tank, sneakers, and the neutral grey of the crewneck. The black crossbody bag adds a sharp, grounding contrast to complete the everyday look.
```

Empty-wardrobe check:

```text
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"

Here are a couple of outfit ideas to style these classic vintage Levi's 501s:

**1. Casual & Effortless Streetwear**
*   **Top:** A relaxed-fit, heavyweight white graphic tee or a vintage band t-shirt (slightly tucked in).
*   **Outerwear:** An oversized black leather bomber jacket or a distressed canvas workwear jacket.
*   **Footwear:** Retro low-top sneakers like Nike Dunks or Adidas Sambas.
*   **Accessories:** A canvas tote bag and a simple silver chain necklace.

**2. Smart-Casual Retro**
*   **Top:** A ribbed black or cream-colored turtleneck sweater, or a crisp button-down shirt worn open over a plain white t-shirt.
*   **Outerwear:** A plaid wool blazer or a classic trench coat.
*   **Footwear:** Leather loafers or chunky black Chelsea boots.
*   **Accessories:** A brown leather belt with a vintage buckle and a minimalist leather crossbody bag.
```

The empty wardrobe produced general styling ideas without claiming those pieces were saved in the user's wardrobe.

#### Create a fit card

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('white ribbed tank top and chunky white sneakers', load_listings()[0]))"

Just scored these classic medium wash Vintage Levi's 501 Jeans on Depop for $38, and I am obsessed with the light fading at the knees. They give off such an effortless streetwear vibe when you style them with a simple white ribbed tank top and chunky white sneakers. Seriously the ultimate everyday denim find!
```

The caption contained three sentences, the correct $38 price, the listing platform, and accurate item details.

I repeated the same caption command several times and received identical text. `CACHE_ENABLED` was on and `TEMPERATURE` was 0.9. The repeated output is consistent with the starter reusing a cached answer; these repeats do not demonstrate independent model variation.

Empty-outfit check:

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[0]))"

Cannot create a fit card without an outfit suggestion.
```

### Session and item handoff check

I ran this check to print the session and compare the saved item with the actual input to the outfit tool:

```bash
python - <<'PY'
from unittest.mock import patch
from pprint import pprint
import agent
from utils.data_loader import get_example_wardrobe

with patch.object(
    agent, "suggest_outfit", wraps=agent.suggest_outfit
) as outfit_tool:
    session = agent.run_agent(
        "vintage graphic tee under $30, size M",
        get_example_wardrobe(),
    )

    pprint(session)

    if outfit_tool.called:
        received = outfit_tool.call_args.kwargs["new_item"]
        print("\nSaved item ID:", session["selected_item"]["id"])
        print("Received item ID:", received["id"])
        print("Full item matches:", session["selected_item"] == received)
    else:
        print("\nOutfit tool was not called.")
PY
```

The printed session included these parsed values:

```text
'parsed': {'description': 'vintage graphic tee',
           'max_price': 30.0,
           'size': 'M'}
```

The comparison printed:

```text
Saved item ID: lst_002
Received item ID: lst_002
Full item matches: True
```

The session's error was None, and it contained the outfit suggestion and fit card.

---

## How I Used AI

### Moment 1: Debugging the search tool

- **What I asked for:** I showed ChatGPT my code after the graphic-tee search returned an empty list.
- **What came back:** It identified that the search implementation was inside `suggest_outfit`, while `search_listings` still contained its original `return []`.
- **What I changed:** I put the search implementation inside `search_listings` and restored the outfit placeholder. Running the search again returned listings.

### Moment 2: Building the tools and planning loop

- **What I asked for:** I asked ChatGPT for complete files while keeping the original starter comments and instructions.
- **What came back:** It provided the tool implementations and a planning loop that parses the query with regular expressions, stores results in the session, and stops when search returns an empty list.
- **What I changed:** I replaced my local files with those versions and tested the tools individually. I then ran both agent paths and a separate session check that confirmed the saved item matched the item received by the outfit tool.

<!-- UNIT 4 — THE TEST
Do not fill these sections in during unit 3.
Keep the original criteria when testing. If a criterion cannot be measured,
add a revision beneath it rather than deleting the original.
-->

---

## Run Log — Before

<!-- Run python run_eval.py --label before.
Paste the results and mark each verdict against the original target. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. | | | | | | | |
| 2. | | | | | | | |
| 3. | | | | | | | |
| 4. | | | | | | | |
| 5. | | | | | | | |

**Real output from one try**, pasted as text, naming the file and function that produced it:

```text

```

---

## Verdicts and Diagnoses

<!-- Mark each criterion MET or MISSED.
For every miss, identify whether it happened in a tool, the loop's branch,
the session, or the model's output. Explain the mechanism. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Diagnoses:**

---

## Loop Trace

<!-- Paste step-by-step traces with the MCP call visible.
Include both a happy path and an empty-search path. -->

**Happy path:**

```text

```

**Empty search:**

```text

```

**On the MCP move:**

<!-- Describe what changed and whether it behaved differently.
If it failed, record the exact error and the last step that worked. -->

---

## The Improvement

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

<!-- Run python run_eval.py --label after after making one improvement. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. | | | | | | | |
| 2. | | | | | | | |
| 3. | | | | | | | |
| 4. | | | | | | | |
| 5. | | | | | | | |

**Did it help, and how do I know:**

---

## What's Still Broken

<!-- For each criterion still missed, explain what you would try next
and why you stopped where you did. Report the remaining limitations honestly. -->

<!--
SUBMISSION CHECKLIST — UNIT 3
[ ] criteria.md has five numbered criteria, each with a target and reason
[ ] All five unit 3 README sections have real content
[ ] Tool Inventory includes typed inputs, specific returns, and empty cases
[ ] Planning Loop describes the implemented branch and names its function
[ ] Sample Run includes a full agent run and three individual tool tests
[ ] At least four new commits
[ ] Submit your fork's URL and keep the same repository for unit 4

SUBMISSION CHECKLIST — UNIT 4
[ ] One tool registered with MCP, or an exact record of where it failed
[ ] Before run log with five tries per criterion
[ ] Real output naming its file and function
[ ] Verdict for every criterion and diagnosis for every miss
[ ] Loop traces with MCP visible
[ ] All three failure modes triggered and handled
[ ] One improvement and an after run log
[ ] Remaining limitations documented
[ ] At least four additional commits
[ ] Submit the same repository URL
-->

---

How to run this project: [RUNNING.md](RUNNING.md)