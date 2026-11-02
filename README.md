# FitFindr

Read [RUNNING.md](RUNNING.md) for setup, commands, and troubleshooting.

## What This Does

FitFindr helps users find thrift listings based on a clothing description, optional size, and budget. It searches a local dataset of 40 listings and suggests outfits using a saved wardrobe. It then writes a short caption describing the find, including its price and listing platform. When no listings match, it stops and suggests changing the clothing keywords, size, or maximum price.

After completing setup:

```bash
source .venv/bin/activate
python app.py ask 'vintage graphic tee under $30, size M'
```

To view a trace:

```bash
python app.py ask 'vintage graphic tee under $30' --trace
```

---

## Tool Inventory

### `search_listings`

- **What it does:** Loads listings using `load_listings()`, filters by optional size and maximum price, and ranks matches by keyword overlap with the title, description, and style tags. The agent now calls it through MCP.
- **Inputs:** `description` (str), `size` (str or None; default None), and `max_price` (float or None; default None). Prices are in US dollars.
- **Returns:** A list of matching listing dictionaries, highest keyword score first, limited to `config.SEARCH_RESULT_LIMIT`. Each dictionary contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. The maximum price is inclusive. Size matching ignores capitalization and compares complete size tokens: M matches S/M, L does not match XL, and S does not match US 9. None skips the corresponding filter.
- **When it has nothing:** Returns an empty list, `[]`.

### `suggest_outfit`

- **What it does:** Calls the model through `generate()` to suggest one or two outfits combining the selected listing with wardrobe items.
- **Inputs:** `new_item` (dict containing a listing) and `wardrobe` (dict containing an `items` list of clothing dictionaries).
- **Returns:** A string containing the model's outfit suggestions. The prompt requests the selected item and specific pieces from the wardrobe, with an explanation of how they work together.
- **When it has nothing:** If the wardrobe's `items` list is empty, requests general styling advice without claiming the user owns the suggested pieces.

### `create_fit_card`

- **What it does:** Calls the model through `generate()` to write a short social caption based on the selected item and outfit suggestion. The improved prompt establishes the user as a shopper considering someone else's listing.
- **Inputs:** `outfit` (str) and `new_item` (dict containing a listing).
- **Returns:** A caption string. The prompt requests 2–4 sentences mentioning the item, its correct price, and its platform once each, plus an accurate color or style detail.
- **When it has nothing:** If `outfit` is empty or contains only whitespace, returns `"Cannot create a fit card without an outfit suggestion."` without calling the model.

The model tools return the model's text after stripping surrounding whitespace. Their content requirements are prompt instructions rather than guarantees enforced by output validation. The agent stops with a message if either model tool returns an empty response.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, save a message in `session["error"]` suggesting the user change their description, size, or maximum price, then stop without calling `suggest_outfit` or `create_fit_card`. Otherwise, save the first result as `selected_item`, use it to suggest an outfit, and create a fit card, saving and reading each result through the session.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** `agent.py::parse_query` uses regular expressions. It extracts a price after wording such as "under," "below," "up to," or "at most," and extracts a size following "size." It removes those parts and common request wording from the description. For example, `vintage graphic tee under $30, size M` becomes description `vintage graphic tee`, size `M`, and maximum price `30.0`. It handles these patterns rather than every possible phrasing.

**What moves through the session:**

1. The original query and wardrobe are saved when the session starts.
2. The extracted description, size, and maximum price are saved in `parsed`.
3. Search reads `parsed` and saves its output in `search_results`.
4. The first search result is saved in `selected_item`.
5. The outfit tool reads `selected_item` and `wardrobe`, then saves its output in `outfit_suggestion`.
6. The caption tool reads `outfit_suggestion` and `selected_item`, then saves its output in `fit_card`.

The loop checks the session to decide which step to perform next. Each iteration calls `trace.check_iterations(count)` to enforce the configured iteration limit. It also stops for an empty description or empty model response. A `ModelUnavailable` handler saves an actionable error message instead of allowing that exception to escape.

**Session verification:** During development, I captured the actual input to `suggest_outfit` while allowing the real tool to run. The selected and received IDs were both `lst_002`, and the complete item dictionaries matched. The Unit 4 evaluator repeats this observation across five tries for criterion 3.

---

## Sample Run

### Unit 3 setup

All 10 environment checks passed. I inspected six listings and reviewed fields including title, description, style_tags, size, and price. The wardrobe stores clothing in an items list; an empty wardrobe is `{"items": []}`.

### Full agent run from Unit 3

The first built-in query is `looking for a vintage graphic tee under $30`. The second is `designer ballgown size XXS under $5`.

Produced by `agent.py::run_agent`, displayed by `agent.py::_show`:

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

This is historical output from before the caption improvement. The seller-like wording was investigated in Unit 4.

### The three tools, tested one at a time

#### Search listings

```text
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

All prices were within the maximum, but some results only mentioned tees in their descriptions. This is a relevance limitation.

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

#### Create a fit card

Historical output before the Unit 4 prompt improvement:

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('white ribbed tank top and chunky white sneakers', load_listings()[0]))"

Just scored these classic medium wash Vintage Levi's 501 Jeans on Depop for $38, and I am obsessed with the light fading at the knees. They give off such an effortless streetwear vibe when you style them with a simple white ribbed tank top and chunky white sneakers. Seriously the ultimate everyday denim find!
```

Repeated calls returned identical captions with build caching enabled and temperature 0.9. Those repeats were not independent evaluation tries.

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[0]))"

Cannot create a fit card without an outfit suggestion.
```

---

## How I Used AI

### Moment 1: Debugging the search tool

- **What I asked for:** I showed ChatGPT my code after the graphic-tee search returned an empty list.
- **What came back:** It identified that the search implementation was inside `suggest_outfit`, while `search_listings` still contained its original `return []`.
- **What I changed:** I moved the implementation into `search_listings`. Running the search again returned listings.

### Moment 2: Building the tools and loop

- **What I asked for:** I asked for complete files while keeping the starter comments and instructions.
- **What came back:** ChatGPT provided implementations and a loop that parses the query, stores tool results in the session, and stops when search returns nothing.
- **What I changed:** I used those versions and tested the tools separately, both agent paths, and the actual item handoff.

### Moment 3: Collecting evaluation evidence

- **What I asked for:** I shared the evaluator and scenarios to prepare tests for my five criteria.
- **What came back:** ChatGPT suggested five scenarios and evaluator wrappers that record actual tool calls, the received item, and complete sessions.
- **What I changed:** I updated the evaluation files and ran both evaluations locally with caching off. The wrappers call the real functions rather than supplying fake outputs.

### Moment 4: Reviewing results and choosing one improvement

- **What I asked for:** I shared the before report for help checking the criteria and finding a problem.
- **What came back:** ChatGPT identified that the criteria passed but several captions incorrectly made the shopper sound like the seller.
- **What I changed:** I added shopper-perspective instructions to the caption prompt and ran the same scenarios again. The verdicts were based on the actual reports; no targets were lowered.

---

## Run Log — Before

Command:

```bash
python run_eval.py --label before
```

Full evidence: [Before report](results/run_2026-11-01_224720_before.md).

Five scenarios ran five times each, with caching disabled and temperature 0.9. The run made 40 model calls. The impossible-search scenario requires no model calls.

The evaluator records evidence but does not automatically assign PASS or FAIL. I applied the original criteria to the saved output with AI assistance.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. All three tools return a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Empty search stops before outfit tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item ID matches received item ID | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Caption meets descriptive requirements | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Every search result respects the budget | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

### Real evidence for each criterion

All excerpts below are from the before report. Records are produced by `run_eval.py::run_once` and written by `run_eval.py::write_report`.

#### Criterion 1 — Try 1

The captured calls ran `mcp_server.py::search_listings` through MCP, followed by `tools.py::suggest_outfit` and `tools.py::create_fit_card`.

```text
search_listings (via MCP): 1
suggest_outfit: 1
create_fit_card: 1
```

Actual fit card:

```text
Found the ultimate Y2K butterfly print baby tee for just $18 over on Depop! I styled it with baggy jeans, a vintage denim jacket, and chunky sneakers for that classic tight-on-top, loose-on-bottom streetwear vibe. Such an easy fit to throw on and instantly look put together.
```

#### Criterion 2 — Try 1

`agent.py::run_agent` stopped after an empty MCP search.

```text
search_listings (via MCP): 1
suggest_outfit: 0
create_fit_card: 0
```

The saved session contained:

```json
"search_results": []
```

```json
"fit_card": null
```

Actual error message:

```text
No listings matched your search. Try different clothing keywords, another size, or a higher maximum price.
```

#### Criterion 3 — Try 1

The evaluator captured the actual item received by `tools.py::suggest_outfit` and compared it with `session["selected_item"]`.

```text
Saved item ID: lst_002
Received item ID: lst_002
Full item matches: True
```

#### Criterion 4 — Try 1

Actual output from `tools.py::create_fit_card`:

```text
Obsessed with this Y2K baby tee featuring the cutest pink and purple butterfly graphic! I just listed it over on Depop for $18, and it gives off such an effortless Y2K streetwear contrast vibe when paired with baggy jeans and chunky sneakers. Grab it before it’s gone!
```

This has three sentences, accurate pink/purple and Y2K details, the correct $18 price, and Depop. It passes the original criterion despite the incorrect seller perspective.

#### Criterion 5 — Try 1

Query: `graphic tee under $20`.

Exact field excerpts from the saved search results returned through `mcp_server.py::search_listings`:

```json
"id": "lst_002"
"price": 18.0
```

```json
"id": "lst_017"
"price": 15.0
```

```json
"id": "lst_033"
"price": 19.0
```

These are excerpts, not complete JSON objects. The full session in the report contains all three objects. Every returned price was at or below $20 in each of the five tries.

---

## Verdicts and Diagnoses

The original criteria and targets in `criteria.md` were preserved.

| # | Target | Verdict before | How I decided |
|---|---|---|---|
| 1 | 4 of 5 | MET (5/5) | Each try called all three tools and returned a non-empty fit card without a session error. |
| 2 | 5 of 5 | MET (5/5) | Each try returned an empty search list, called neither later tool, and named changes the user could try. |
| 3 | 5 of 5 | MET (5/5) | Each saved item ID matched the ID captured at the actual outfit-tool call. The complete dictionaries also matched. |
| 4 | 5 of 5 | MET (5/5) | Each caption had 2–4 sentences, identified the selected item, included an accurate color or style detail, and gave its correct price and platform. |
| 5 | 5 of 5 | MET (5/5) | All three returned prices were within the $20 limit in every try. |

**Missed criteria:** None in these scenarios, so there are no criterion failures to diagnose.

**Problem outside the original criteria:** In criterion 4's five before captions, tries 1, 3, 4, and 5 implied the user was selling the item. Examples included "I just listed it," "my Depop," and invitations to buy before the speaker decided to keep it.

**Step and mechanism:** The issue occurred in the model output from `tools.py::create_fit_card`. The prompt asked for a social caption about a thrift find but did not establish whether the speaker was a buyer or seller. The model repeatedly adopted a sales-post perspective. Search and the session handoff still worked.

**Were the targets too easy?** The tests covered structural correctness and basic caption details, but they did not fully measure whether the caption made sense for the user. They also repeatedly selected the same tee, so passing does not establish reliability across all listings. If I tightened a future criterion, I would require the caption to preserve the shopper's perspective and test more item types. I did not retroactively add that requirement to the original score.

---

## Loop Trace

These traces were produced by calls to `trace.step` inside `agent.py::run_agent`. The trace helper shortens long inputs and outputs.

### Happy path

Command:

```bash
python app.py ask 'vintage graphic tee under $30' --trace
```

Actual trace from the development run before the prompt improvement:

```text
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Saved ID: lst_002
[4] suggest_outfit input
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Item ID: lst_002; wardrobe items: 10
[5] suggest_outfit result
      out: Here is a stylish Y2K-inspired outfit using the baby tee and pieces from your wardrobe:  ### The Outfit: Y2K S…
[6] create_fit_card input
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Item ID: lst_002
[7] create_fit_card outfit input
      in:  Here is a stylish Y2K-inspired outfit using the baby tee and pieces from your wardrobe:  ### The Outfit: Y2K S…
[8] create_fit_card result
      out: Found this super cute Y2K butterfly print baby tee for just $18, and I am obsessed with the pink and purple de…
[9] complete
      →    Returning the finished session.
```

This development run used two cached model responses. Both formal evaluations disabled caching.

### Empty search

Command:

```bash
python app.py ask 'designer ballgown size XXS under $5' --trace
```

Actual trace:

```text
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
[3] empty-search branch
      →    No listings matched your search. Try different clothing keywords, another size, or a higher maximum price. Stopping before outfit and caption tools.
```

The empty-search trace is shorter because the agent stops before either model tool.

### Three deliberately triggered failure cases

#### 1. Empty search

The impossible query above returned:

```text
No listings matched your search. Try different clothing keywords, another size, or a higher maximum price.
```

The user can change the description, size, or budget.

#### 2. Empty wardrobe

Command:

```bash
python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --trace
```

The trace showed:

```text
[4] suggest_outfit input
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Item ID: lst_002; wardrobe items: 0
```

Actual outfit-tool output:

```text
Here are a couple of outfit ideas to style the Y2K Butterfly Baby Tee:

*   **Classic Y2K Streetwear:** Pair the baby tee with low-rise baggy cargo pants or light-wash wide-leg denim. Accessorize with a small baguette shoulder bag, chunky platform sneakers or retro skate shoes, and a beaded necklace to lean fully into the early 2000s aesthetic.
*   **Sweet & Casual Everyday:** Style the cropped top with a pleated tennis skirt (in white, pink, or denim) or high-waisted mom shorts. Layer with a thin zip-up hoodie and finish the look with pastel platform canvas sneakers or retro running shoes for a playful, effortless vibe.
```

The tool returned general advice instead of crashing or returning an empty string. The CLI also displayed `(running with an empty wardrobe)`.

#### 3. Model unavailable

I temporarily supplied an invalid key through an environment variable for this command only. This overrode the loaded key without modifying the real key in `.env`. Caching was disabled to force a real request.

```bash
AI201_CACHE=0 GEMINI_API_KEY=invalid-test-key python app.py ask 'vintage graphic tee under $29' --trace
```

Actual trace:

```text
[1] parse_query
      in:  vintage graphic tee under $29
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 29.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 29.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Saved ID: lst_002
[4] suggest_outfit input
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    Item ID: lst_002; wardrobe items: 10
[5] model unavailable
      →    The model could not be reached while running suggest_outfit. Check your internet connection and GEMINI_API_KEY in .env, then try again.
```

The user received the same actionable message without a raw traceback. The command made one model request. The real key remained unchanged.

### On the MCP move

I registered a typed wrapper named `search_listings` in `mcp_server.py`. The wrapper delegates to the existing implementation in `tools.py`. I changed the search call in `agent.py::run_agent` to `mcp_client.call_tool("search_listings", arguments)`.

`python mcp_client.py` listed the tool with a required description string and optional size string and maximum-price number. After the move, the matching query still selected the same $18 tee, and the impossible query still stopped early. The client returned a native list of dictionaries, so the existing branch and session handling continued to work.

Only search moved onto MCP. The other two tools still call the model locally through `generate()`.

---

## The Improvement

**What I changed:** I added shopper-perspective instructions to the prompt in `tools.py::create_fit_card`.

The new instructions say the user is considering an item from someone else's listing. They prohibit claiming the user already bought or owns the item, listed it for sale, or owns the seller's account. They also discourage sales invitations such as "grab it before it is gone."

**Which problem it was meant to fix:** The model repeatedly wrote captions from a seller's perspective because the original prompt did not specify the speaker's role.

This was one prompt change. The agent's search, parsing, branching, model, temperature, scenarios, and original acceptance criteria stayed the same between the before and after evaluations.

### Run Log — After

Command:

```bash
python run_eval.py --label after
```

Full evidence: [After report](results/run_2026-11-01_225558_after.md).

The same five scenarios ran five times each, with caching disabled and temperature 0.9. The run made 40 model calls.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. All three tools return a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Empty search stops before outfit tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item ID matches received item ID | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Caption meets descriptive requirements | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Every search result respects the budget | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

The same scoring rules were applied after the change: actual calls for criterion 1, the stop and message for criterion 2, captured IDs for criterion 3, full captions for criterion 4, and every returned price for criterion 5.

### Before and after comparison

| Measure | Before | After |
|---|---|---|
| Criterion 1 passes | 5/5 | 5/5 |
| Criterion 2 passes | 5/5 | 5/5 |
| Criterion 3 passes | 5/5 | 5/5 |
| Criterion 4 passes | 5/5 | 5/5 |
| Criterion 5 passes | 5/5 | 5/5 |
| Seller-perspective captions in criterion 4's five tries | 4/5 | 0/5 |

The seller-perspective measure is an additional diagnostic, not a replacement acceptance criterion. I counted captions that claimed the speaker was selling the item or used sales invitations implying that role. Before, tries 1, 3, 4, and 5 did this; after, none of the five did.

Actual caption from criterion 4, after Try 1, produced by `tools.py::create_fit_card`:

```text
Just found this super cute Y2K baby tee with the sweetest pink and purple butterfly graphic while scrolling through Depop. For just $18, I'm totally picturing pairing it with baggy dark-wash jeans and chunky sneakers to lean into that classic Y2K streetwear silhouette. It’s such a fun little crop, and I love how easy it would be to style!
```

**Did it help, and how do I know:** The original criteria remained met, and the specific seller-perspective issue decreased from 4/5 to 0/5 in the selected caption scenario. The after captions described finding or considering the item and possible styling choices. This supports the prompt change for these five tries, but it does not prove the issue can never recur.

---

## What's Still Broken

No original criterion was missed in the after evaluation. However, there are still limitations:

- **Search relevance:** A listing can match because its description mentions another clothing item. The graphic-tee search returned a mesh top and cargo pants. A future improvement could prioritize the title and style tags or require stronger evidence of the requested item type.
- **Narrow test coverage:** All successful evaluation scenarios selected the same baby tee. More tests should cover different categories, brands, sizes, and prices. Passing these scenarios does not demonstrate performance across the entire dataset.
- **Prompt requirements are not validated:** The program does not enforce caption sentence count or factual details after generation. The five tested captions passed, but future model responses might not.
- **Limited query parsing:** The regular expressions handle the documented patterns, not every natural-language size or budget phrase.
- **General failure message:** The model handler tells the user to check the key and connection but does not distinguish all possible provider failures.

I stopped after the one measured prompt improvement so the before/after comparison could be attributed to that change. I preserved the original criteria and reported the remaining issues instead of making additional unmeasured changes.

---

How to run this project: [RUNNING.md](RUNNING.md)

Repository: https://github.com/ar3lyy/ai201-project2-fitfindr-starter-v2026