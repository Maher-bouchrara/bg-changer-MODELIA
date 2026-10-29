# Bg-changer

Put a person or product photo on a new solid-colour background, and optionally
**keep the subject's real shadow** on the new colour.

```
photo.jpg + "#FF0066"  ──►  same photo, same subject, pink background (+ shadow)
```

> **Step-by-step documentation** (one page per step, with diagrams and results): [docs/](docs/README.md)

> **Status:** work in progress. Sections marked 🚧 are planned and are filled in
> as each step is committed. See [Roadmap](#roadmap).

---

## Contents

1. [Quick start](#quick-start)
2. [How it works (the pipeline)](#how-it-works-the-pipeline)
3. [Decisions, step by step](#decisions-step-by-step)
   - [3.1 Input handling](#31-input-handling)
   - [3.2 Hex colour parsing](#32-hex-colour-parsing)
   - [3.3 Segmentation models](#33-segmentation-models)
   - [3.4 Edge cleanup (foreground estimation)](#34-edge-cleanup-foreground-estimation)
   - [3.5 Shadow extraction](#35-shadow-extraction)
   - [3.6 Compositing](#36-compositing)
   - [3.7 Architecture: CLI, API, UI](#37-architecture-cli-api-ui)
4. [Results](#results)
5. [What did not work / limitations](#what-did-not-work--limitations)
6. [Roadmap](#roadmap)
7. [Time spent and use of AI tools](#time-spent-and-use-of-ai-tools)

---

## Quick start

🚧 Filled in once the CLI and Docker Compose exist. The target is one command each:

```bash
docker compose up
```

```bash
uv run bgchange photo.jpg --color "#FF0066" --shadow keep -o out.png
```

---

## How it works (the pipeline)

The AI model does **one** job: it says, for every pixel, *how much of this pixel
is the subject* (a number from 0 to 1 called the **alpha matte**). Everything
else (reading the file, the colour, the shadow, the blend) is ordinary image
processing written in this repo.

```mermaid
flowchart LR
    IMG["Input photo"] --> IN["3.1 Input handling"]
    HEX["Hex colour<br/>#FF0066"] --> HP["3.2 Hex parsing"]

    IN --> SEG["3.3 AI model<br/>predicts alpha matte"]
    SEG --> FG["3.4 Edge cleanup<br/>true subject colours"]
    IN --> FG

    IN --> SH["3.5 Shadow extraction<br/>(optional)"]
    SEG --> SH

    FG --> CMP["3.6 Compositing"]
    HP --> CMP
    SH --> CMP
    CMP --> OUT["Output PNG"]

    style SEG fill:#ffe3ec,stroke:#d6336c
```

Only the pink box is a neural network. That separation is deliberate: the model
can be swapped (see 3.3) without touching any other stage.

---

## Decisions, step by step

Each section answers three questions: **what is the problem**, **what did I
choose**, and **why**.

### 3.1 Input handling

✅ *[`bgchange/s1_load_photo/`](bgchange/s1_load_photo/), 18 tests in [`tests/s1_load_photo/`](tests/s1_load_photo/).*

One file per step, so each can be read on its own:

```
bgchange/s1_load_photo/
├── loader.py          load_image(): runs steps 1 → 4, returns a LoadedImage
├── open_file.py       1. open + validate (not an image? truncated? too big?)
├── exif_rotation.py   2. rotate phone photos upright
├── transparency.py    3. keep existing transparency as an "alpha hint"
├── color_mode.py      4. convert to 8-bit sRGB, using:
├── bit_depth.py          · 16-bit greyscale → 8-bit (scaled, not clipped)
├── color_profile.py      · ICC profiles (iPhone P3, CMYK) → sRGB
└── errors.py          ImageLoadError
```

**Problem.** Real photos are messier than they look. A phone photo is often
stored sideways, with a tag (EXIF) telling viewers to rotate it. Files can be
greyscale, CMYK (print), 16-bit, carry a colour profile, or already have
transparency.

**What `load_image()` does.** It takes a file path (CLI) or raw bytes (API) and
always returns the same thing: an upright, 8-bit sRGB image.

```mermaid
flowchart TB
    A["File path or uploaded bytes"] --> V{"1. A real image?<br/>Under 50 MP?"}
    V -- no --> ERR["Clear error message"]
    V -- yes --> R{"2. EXIF rotation tag?"}
    R -- yes --> R2["Rotate pixels upright"] --> S
    R -- no --> S{"3. Has transparency?"}
    S -- yes --> S2["Keep it as an alpha hint"] --> C
    S -- no --> C{"4. Colour format?"}
    C -- "16-bit grey" --> C1["Scale to 8-bit"] --> OUT
    C -- "ICC profile (P3, CMYK…)" --> C2["Convert to sRGB"] --> OUT
    C -- "CMYK / grey / palette" --> C3["Convert to RGB"] --> OUT
    C -- "RGB" --> OUT["LoadedImage<br/>8-bit sRGB + alpha hint + notes"]
```

| Hard case | What would go wrong without it | Fix |
|---|---|---|
| Phone photo with EXIF rotation | Subject processed and returned lying on its side | Rotate the pixels, drop the tag |
| 16-bit greyscale PNG | Pillow's `convert("L")` *clips* instead of scaling, so mid-grey becomes white | Scale by hand (÷257) |
| iPhone photo (Display-P3) | Colours read as sRGB look washed out | Convert with the embedded ICC profile |
| CMYK print JPEG | Model expects RGB | Use the ICC profile if present, else Pillow's formula |
| PNG already partly transparent | That information would be lost | Kept as an *alpha hint* for compositing |
| Animated GIF / multi-page TIFF | Ambiguous input | First frame, with a note |
| Not an image, truncated download | Crash with a Python traceback | One clear error message |
| 20,000 × 20,000 image, decompression bomb | Freezes the machine | Refused **before** decoding (limit 50 MP) |
| Broken colour profile | Good photo rejected | Profile ignored, with a note |

**Design choices.**
- **Nothing happens silently.** Every fix adds a line to `notes`, and the CLI and
  API show them, so a user can see *why* the output looks the way it does.
- **Transparency is removed before colour conversion**, because colour profiles
  apply to colour channels only.
- **All test images are generated in code.** No binary test files in the repo,
  and each test triggers exactly one problem.

### 3.2 Hex colour parsing

✅ *[`bgchange/s2_read_color/`](bgchange/s2_read_color/), 30 tests in [`tests/s2_read_color/`](tests/s2_read_color/).*

```
bgchange/s2_read_color/
├── rgba.py         Color(r, g, b, a): the value every other stage uses
├── hex_parser.py   parse_hex_color(): "#FF0066" → Color(255, 0, 102, 255)
└── errors.py       ColorParseError
```

**What `parse_hex_color()` does.** It accepts the formats people actually type
and rejects everything else with a message that says what to type instead.

```mermaid
flowchart LR
    T["' #ff0066 '"] --> A["Trim spaces"] --> B["Strip optional #"]
    B --> C{"Hex digits only?<br/>Length 3, 4, 6, 8?"}
    C -- no --> E["Error naming the<br/>accepted formats"]
    C -- "3 or 4" --> D["Expand short form<br/>F06 → FF0066"] --> F
    C -- "6 or 8" --> F["Read pairs as numbers"]
    F --> O["Color(r=255, g=0, b=102, a=255)"]
```

| Input | Meaning | Result |
|---|---|---|
| `#FF0066`, `#ff0066`, `FF0066`, `" #FF0066 "` | standard, any case, `#` optional | `(255, 0, 102)` solid |
| `#F06` | short form | `(255, 0, 102)` solid |
| `#FF006680` / `#F068` | with alpha | semi-transparent background → PNG with transparency |
| `#00000000` | fully transparent | a plain cut-out |
| `red`, `#GG0000`, `#FF006`, empty | invalid | error listing the accepted formats |

**Design choices.**
- **No colour names** (`red`, `navy`). The brief asks for hex, and one strict
  format is easier to test and explain.
- **Known trap: `#FF00` is not a typo error.** It's a valid `#RGBA` short form,
  which means *fully transparent yellow*. It follows the CSS standard, so it is
  accepted, and a test pins down this behaviour.

### 3.3 Segmentation models

✅ *All 5 models run. [`bgchange/s3_ai_models/`](bgchange/s3_ai_models/), 6 registry tests in
[`tests/s3_ai_models/`](tests/s3_ai_models/). The default is provisional until the benchmark (step 5).*

**What a model does here.** Image in, alpha matte out. Nothing else.

```
 photo                       alpha matte (white = subject)
 +--------------+            +--------------+
 |  person on   |   model    |  white shape |
 |  a street    | ---------> |  on black    |
 +--------------+            +--------------+
```

**Downloaded is not the same as usable.** `models/` holds the weights (files).
To use them, code must build the network, fill it with the weights, prepare
each photo the way that model expects and convert its output to a 0–1 matte.
Each model does this differently, so each has a small adapter. All adapters
follow one rule, `predict(image) -> alpha`, and the registry picks one by name.

```mermaid
flowchart LR
    subgraph disk["models/ (weights)"]
        W1["birefnet/"]
        W2["birefnet-matting/"]
        W3["rmbg-2.0/"]
        W4["ben2/"]
        W5["inspyrenet/"]
    end
    subgraph code["bgchange/s3_ai_models/ (code)"]
        A1["birefnet.py<br/>3 models, 1 network"]
        A2["ben2.py"]
        A3["inspyrenet.py"]
        R["registry.py<br/>get_segmenter(name)<br/>one model on GPU at a time"]
    end
    W1 --> A1
    W2 --> A1
    W3 --> A1
    W4 --> A2
    W5 --> A3
    A1 --> R
    A2 --> R
    A3 --> R
    R --> P["Pipeline:<br/>predict(image) → alpha"]
```

```
bgchange/s3_ai_models/
├── base.py         the rule: predict(image) -> alpha
├── birefnet.py     BiRefNet, BiRefNet-matting, RMBG-2.0 (same network, different training)
├── ben2.py         BEN2
├── inspyrenet.py   InSPyReNet
└── registry.py     get_segmenter("ben2"); unloads the previous model first
```

| Model | How it works | Trained on / strength | License |
|---|---|---|---|
| `birefnet` | Looks twice: whole scene small + full detail | General subjects; suggested in the brief | MIT |
| `birefnet-matting` | Same network as above | Matting data: soft, partly transparent edges (hair) | MIT |
| `rmbg-2.0` | Same network as above (its config declares BiRefNet) | BRIA's 15k hand-labelled, licensed images; products | **CC BY-NC 4.0, non-commercial**: benchmarked, never the default |
| `ben2` | 4 zoomed tiles + 1 overview, merged | Fine edges | MIT |
| `inspyrenet` | Rough mask first, then adds edge detail level by level | High-resolution images | MIT |

**Smoke test** ([`scripts/check_models.py`](scripts/check_models.py), RTX 5050 Laptop):

| Model | Mask on test disc | Load (cached) | Per image | Peak VRAM | Blank grey image: max / mean |
|---|---|---|---|---|---|
| birefnet | OK | 2–15 s | 0.36 s | 1.58 GB | 0.00 / 0.00 |
| birefnet-matting | OK | 2.6 s | 0.37 s | 1.58 GB | 0.74 / 0.32 |
| rmbg-2.0 | OK | 2.3 s | 0.37 s | 1.58 GB | 1.00 / **0.95** |
| ben2 | OK | 1.8 s | 0.47 s | 2.35 GB | 0.99 / 0.04 |
| inspyrenet | OK | 1.8 s | 0.37 s | 3.10 GB | 0.00 / 0.00 |

The "blank grey image" column asks: with no subject at all, does the model
invent one? RMBG-2.0 calls almost the whole grey image "subject". A blank image
is ambiguous (a grey card could be the product), so this is a lead for the
benchmark, not a verdict.

```bash
uv run python scripts/check_models.py
```

**Decisions and problems found while wiring the models.**
- **Weights load from `models/`, pinned.** No hidden cache, no internet at
  runtime. BiRefNet-family code runs via `trust_remote_code`, which is safe here
  because it's the pinned file we downloaded and the folder name never comes
  from user input.
- **BEN2 and InSPyReNet both stretch their masks min-to-max** in their own
  helpers, which turns an unsure prediction into a confident-looking one. Both
  adapters skip that step and return the model's real probabilities.
- **BEN2's code changes global PyTorch settings on import** (random seeds and
  matmul precision "highest"). The adapter restores the precision so the other
  models don't slow down.
- **InSPyReNet gives NaN masks in fp16**, because some internal values are too
  large for half precision. It runs in fp32, which costs it the most VRAM.
- **InSPyReNet's package would install 24 extra packages**, including a second
  OpenCV that clashes with ours. `pyproject.toml` declares its dependencies as
  empty, and the adapter imports only the network files, never the package's
  GUI or tools.
- **Safer weight formats:** `.safetensors` where available (cannot run code),
  and `torch.load(weights_only=True)` for InSPyReNet's `.pth`.

Check your own GPU, or get the mask of one photo:

```bash
uv run python scripts/check_gpu.py
```

```bash
uv run python scripts/predict_mask.py photo.jpg
```

### 3.4 Edge cleanup (foreground estimation)

🚧 *Implemented in step 6.*

**Problem.** Along hair and soft edges, pixels are a *mix* of subject and old
background. Pasting them as-is onto pink leaves a green fringe if the old
background was grass.

**Plan.** Before blending, estimate the subject's *true* colour at each edge
pixel (removing the old background's contribution), then blend that.

### 3.5 Shadow extraction

🚧 *Implemented in step 7.*

**Problem.** The model marks the shadow as "not subject", so a normal cut-out
loses it and the subject looks pasted on.

**Plan.** A shadow is the background made darker. So:

```mermaid
flowchart LR
    A["Original background<br/>(subject removed)"] --> B["Estimate how bright it would be<br/>without the shadow"]
    A --> C["Measured brightness"]
    B --> D["shadow = 1 - measured / expected"]
    C --> D
    D --> E["Keep only near the subject,<br/>smooth"]
    E --> F["Darken the NEW colour by that amount"]
```

Options: `--shadow none|keep` and `--shadow-strength 0..1`. On very busy
backgrounds the shadow cannot be separated reliably; the tool detects this and
warns instead of producing a dirty result.

### 3.6 Compositing

🚧 *Implemented in step 6.*

The standard blend, one line per pixel:

```
result = alpha × subject + (1 − alpha) × (new colour × shadow darkening)
```

### 3.7 Architecture: CLI, API, UI

🚧 *Implemented in steps 8–10.*

```mermaid
flowchart TB
    subgraph core["bgchange (Python core)"]
        PIPE["pipeline"]
    end
    CLI["CLI<br/>bgchange ..."] --> PIPE
    API["FastAPI<br/>POST /process"] --> PIPE
    WEB["Next.js UI"] -->|HTTP| API
    subgraph docker["docker compose up"]
        API
        WEB
    end
```

The CLI and API are thin wrappers, so both give identical results.

---

## Results

🚧 Contact sheet of the hard cases (original / mask / result / result + shadow)
and the benchmark table go here.

## What did not work / limitations

🚧 Filled in honestly as things fail.

## Roadmap

Each step is one or more small commits.

- [x] **1. Repo baseline**: structure, README plan, notes
- [x] **2. Python env + GPU check + first model (BiRefNet)**
- [x] **3. Input handling + hex parsing** (48 tests)
- [x] **4. Model registry + the other 4 models**

> **Why the model comes before input handling.** Getting PyTorch to run on a
> brand-new GPU and loading the model is the riskiest part, so it is done first
> to surface problems early. Input handling and hex parsing are plain Python and
> low risk.

Run the tests (no GPU or downloads needed):

```bash
uv run pytest
```
- [ ] **5. Benchmark** → pick the default model
- [ ] **6. Edge cleanup + compositing** → first full CLI result
- [ ] **7. Shadow extraction**
- [ ] **8. FastAPI**
- [ ] **9. Next.js UI**
- [ ] **10. Docker Compose** (CPU default, GPU profile)
- [ ] **11. Results, limitations, final README**

## Time spent and use of AI tools

Tracked as I go in [NOTES.md](NOTES.md).
