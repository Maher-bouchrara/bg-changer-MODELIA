# test_data/

Images used to **test** (grade) the 5 segmentation models. None of this is used
for training: the models are already trained by their authors. We only run
them on these images and compare their masks with the correct answer.

The images are **not committed** to git: they are large, and their licences
allow research use, not redistribution. Fetch them with:

```bash
uv run python scripts/download_test_data.py
```

## Layout

```
test_data/
├── README.md        this file (the only file committed)
├── dis-vd/          470 object photos + their correct masks
│   ├── images/      photo.jpg
│   └── masks/       photo.png   (same name as the photo)
├── p3m-500-np/      500 portrait photos + their correct alpha mattes
│   ├── images/
│   └── masks/
└── real-photos/     ~40 free photos (Unsplash / Pexels) + later your phone
                     photos, with NO correct mask: judged by eye
```

## The golden rule: test images must not be training images

Each model was trained by its authors on some set of images. If we tested a
model on those same images, it would score well simply because it has already
seen them, like a student graded on the exact exam they practised with. So
every set below was chosen because it was **kept out of training** (at least for
BiRefNet, whose training list is public).

```
authors, before us:  training images ──► train ──► model
us, now:             TEST images     ──► run   ──► score   (must not overlap)
```

---

## 1. DIS-VD: objects (470 images)

| | |
|---|---|
| **Full name** | DIS5K Validation set ("VD" = **V**ali**D**ation) |
| **From** | *Highly Accurate Dichotomous Image Segmentation*, Qin et al., ECCV 2022 |
| **What's in it** | 470 high-resolution photos of single objects from 200+ categories: bikes, chairs, jewellery, plants, fences, tools, animals, kites, umbrellas… Many have thin or complicated parts (spokes, cables, branches). |
| **Correct answer** | A **binary mask**, drawn by hand very precisely: each pixel is subject (white) or background (black). |
| **Why we use it** | It's the closest public set to "product and object photos", and its masks are precise enough to measure **edge quality**, not just "roughly the right shape". |
| **Training overlap** | BiRefNet's README lists DIS-VD as its **test set** (not trained on). For BEN2 and InSPyReNet, see the benchmark notes. RMBG-2.0 trained on BRIA's private data. |
| **Where we get it** | Hugging Face copy [`not-lain/DIS5K`](https://huggingface.co/datasets/not-lain/DIS5K), file `DIS_VD` only (478 MB), pinned to commit `e007e9a3`. Official source: [github.com/xuebinqin/DIS](https://github.com/xuebinqin/DIS). |
| **Licence** | DIS5K Terms of Use (included in the Hugging Face copy): research use. |

**Why "dichotomous"?** It means "split in two": every pixel is either object or
not. That's exactly our task: subject vs. background.

**The other DIS5K parts, and why we don't use them:**

| Part | Images | Purpose | Used here? |
|---|---|---|---|
| DIS-TR | 3,000 | **TR**aining | ❌ BiRefNet trained on it |
| DIS-VD | 470 | **V**ali**D**ation | ✅ held out from BiRefNet's training |
| DIS-TE1…TE4 | 2,000 | **TE**sting, by difficulty (TE1 easiest → TE4 hardest) | ❌ BiRefNet's *general* weights also trained on DIS-TEs |

---

## 2. P3M-500-NP: people (500 images)

| | |
|---|---|
| **Full name** | **P**rivacy-**P**reserving **P**ortrait **M**atting, 500-image test set, **N**on-**P**rivacy version |
| **From** | *Privacy-Preserving Portrait Matting*, Li et al., ACM Multimedia 2021 |
| **What's in it** | 500 portrait photos of public figures, faces **not** blurred, with real hair, loose hair, hats, glasses and varied backgrounds. |
| **Correct answer** | An **alpha matte**: each pixel has a value from 0 to 255, so a strand of hair can be "40% subject". This is softer and more detailed than a binary mask, and it's what lets us grade hair. |
| **Why we use it** | Real people with real hair, so it tests the soft-edge cases that DIS-VD (hard edges) does not. |
| **Training overlap** | BiRefNet's README keeps TE-P3M-500-NP out of training and uses it as the test set for its matting model. |
| **Where we get it** | Hugging Face copy [`nobg/P3M-10K`](https://huggingface.co/datasets/nobg/P3M-10K), file `P3M_500_NP` only (279 MB), pinned to commit `a239de92`. Official source: [github.com/JizhiziLi/P3M](https://github.com/JizhiziLi/P3M). |
| **Licence** | P3M Dataset Release Agreement (MIT-labelled), research use. |

**The other P3M parts, and why we don't use them:**

| Part | Images | Faces | Used here? |
|---|---|---|---|
| P3M train | 9,421 | blurred | ❌ training data |
| P3M-500-P | 500 | **blurred** (the "**P**rivacy" version) | ❌ BiRefNet's general weights trained on it |
| P3M-500-NP | 500 | **not blurred** (the "**N**on-**P**rivacy" version) | ✅ held out |

---

## 3. real-photos: real-world check (~40 images, no masks)

| | |
|---|---|
| **What's in it** | About 20 product photos and 20 people photos chosen to be hard: white on white, glass, shadows, curly hair, busy backgrounds, several people. Later, your own phone photos. |
| **Correct answer** | **None.** Nobody drew masks for these, so there's no automatic score. All 5 models' masks are placed side by side, and we judge by eye. |
| **Why we use it** | No model has ever seen them, so they're the most independent check. If the winner on sets 1 and 2 also looks best here, the result is trustworthy. These photos are also reused for the shadow step. |
| **Where from** | [Unsplash](https://unsplash.com) and [Pexels](https://www.pexels.com) (free licence). Each file's source link is recorded. Not Google Images, which are usually copyrighted. |

---

## Mask vs. alpha matte, in one picture

```
binary mask (DIS-VD)        alpha matte (P3M)
pixel = 0 or 255            pixel = 0 … 255
█ █ █ ░ ░                   █ █ ▓ ▒ ░
█ █ █ ░ ░    hair edge →    █ █ ▓ ▒ ░
"in or out"                 "how much in" (soft edges)
```
