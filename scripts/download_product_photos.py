"""Download the extra test photos (option D) from Pexels.

Run:  uv run python scripts/download_product_photos.py

    test_data/products/answer-key/images/   10 product photos; you draw their correct masks
    test_data/products/eye-test/images/     ~25 product hard cases, judged by eye
    test_data/real-photos/images/           ~30 real-world people + product photos
                                            (clutter, night, same colour as background),
                                            judged by eye
    test_data/photo_sources.csv             link + Pexels id of every photo

Pexels licence: free to use, including commercially, no attribution required
(we still record the source of each photo). Photos are downloaded at 1600 px
wide to keep the download small (~10 MB in total).
"""

from __future__ import annotations

import csv
import sys
import urllib.request

from bgchange.paths import TEST_DATA_DIR

WIDTH = 1600

# Where each set goes, under test_data/.
SET_FOLDERS = {
    "answer-key": "products/answer-key",
    "eye-test": "products/eye-test",
    "real-world": "real-photos",
}

# (set, Pexels id, short name). Ids above ~30,000,000 were uploaded in 2025 or later,
# i.e. after the models were trained, so they cannot be in their training data.
PHOTOS = [
    # --- answer-key: simple enough shapes to draw a correct mask by hand ---
    ("answer-key", 31688982, "red-sneakers-on-white"),
    ("answer-key", 33629780, "white-sneakers-on-bed"),
    ("answer-key", 30970926, "minimalist-perfume-bottle"),
    ("answer-key", 35825543, "perfume-on-pink"),
    ("answer-key", 36940128, "vintage-nikon-camera"),
    ("answer-key", 31876260, "analog-camera-on-wood"),
    ("answer-key", 11075707, "white-mug-on-white"),
    ("answer-key", 97260, "cactus-in-white-pot"),
    ("answer-key", 2433862, "brown-leather-bag"),
    ("answer-key", 4339598, "brown-shoulder-bag"),
    # --- eye-test: hard cases, no mask needed ---
    ("eye-test", 30990130, "blue-glass-perfume"),
    ("eye-test", 36779953, "perfume-on-dark-fabric"),
    ("eye-test", 4110400, "wine-glasses-on-white"),
    ("eye-test", 14185465, "wine-glasses-on-black"),
    ("eye-test", 8599448, "wine-glasses-on-glass-table"),
    ("eye-test", 136651, "glass-bottle-coloured-shadows"),
    ("eye-test", 11711813, "perfume-in-sunlight"),
    ("eye-test", 14174467, "white-grey-shoe-on-white"),
    ("eye-test", 1461048, "white-sneakers-on-white"),
    ("eye-test", 754178, "white-bear-plush"),
    ("eye-test", 42230, "teddy-bear"),
    ("eye-test", 815491, "panda-plush"),
    ("eye-test", 4247412, "mug-on-laptop"),
    ("eye-test", 762092, "red-mug-on-mat"),
    ("eye-test", 8102139, "cosmetics-and-gua-sha"),
    ("eye-test", 6167865, "amber-bottles-on-marble"),
    ("eye-test", 13693319, "backpack-on-brown"),
    ("eye-test", 22696560, "vintage-cameras"),
    ("eye-test", 311458, "five-cacti"),
    ("eye-test", 1499477, "two-eyewear-on-white"),
    ("eye-test", 10388460, "sunglasses-on-wood"),
    ("eye-test", 7193653, "lamp-on-stool"),
    ("eye-test", 1445416, "snake-plant"),
    ("eye-test", 2529148, "sneakers-in-the-air"),
    ("eye-test", 6698234, "puma-sneakers"),
    # --- real-world: no studio background. Products in clutter, low light,
    #     same colour as the background; people on streets, at night, holding things ---
    ("real-world", 29312153, "product-kitchen-shelf-bottles"),
    ("real-world", 28853826, "product-coffee-counter"),
    ("real-world", 5793770, "product-condiment-bottles"),
    ("real-world", 10568482, "product-soap-sponge-bottle"),
    ("real-world", 16256007, "product-green-perfume"),
    ("real-world", 14395195, "product-bottle-on-green"),
    ("real-world", 3989394, "product-perfume-on-leaves"),
    ("real-world", 3259600, "product-bottles-on-moss"),
    ("real-world", 11161892, "product-perfume-among-branches"),
    ("real-world", 29707925, "product-cocktail-at-bar"),
    ("real-world", 9566353, "product-whiskey-glass-bar"),
    ("real-world", 6503578, "product-beer-bottle-bar"),
    ("real-world", 1471880, "product-shoes-on-asphalt"),
    ("real-world", 19957690, "product-akg-headphones"),
    ("real-world", 159376, "product-laptop-headphones"),
    ("real-world", 381228, "product-toy-car-on-floor"),
    ("real-world", 34667512, "person-trench-coat-street"),
    ("real-world", 1437614, "person-walking-market"),
    ("real-world", 20184493, "person-curly-hair-metro"),
    ("real-world", 30695211, "person-night-portrait-mexico"),
    ("real-world", 23432448, "person-hooded-neon"),
    ("real-world", 29559269, "person-motion-blur-night"),
    ("real-world", 9931573, "person-bearded-neon"),
    ("real-world", 16277369, "person-silhouette-night"),
    ("real-world", 20060098, "person-covered-face-night"),
    ("real-world", 30471727, "person-holding-coffee-top-view"),
    ("real-world", 733764, "person-cup-dim-cafe"),
    ("real-world", 13696082, "person-on-sofa"),
    ("real-world", 4114855, "person-grey-jacket-green-couch"),
]


def image_url(pexels_id: int) -> str:
    return (
        f"https://images.pexels.com/photos/{pexels_id}/pexels-photo-{pexels_id}.jpeg"
        f"?auto=compress&cs=tinysrgb&w={WIDTH}"
    )


def main() -> None:
    rows, failed = [], []
    for set_name, pexels_id, name in PHOTOS:
        target = TEST_DATA_DIR / SET_FOLDERS[set_name] / "images" / f"{name}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            request = urllib.request.Request(image_url(pexels_id), headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    target.write_bytes(response.read())
            except Exception as error:  # report and continue with the others
                failed.append(f"{name} ({pexels_id}): {error}")
                continue
        print(f"[{set_name}] {name}.jpg  {target.stat().st_size / 1024:.0f} KB")
        rows.append(
            {
                "set": set_name,
                "file": f"{name}.jpg",
                "pexels_id": pexels_id,
                "page": f"https://www.pexels.com/photo/{pexels_id}/",
            }
        )

    with (TEST_DATA_DIR / "photo_sources.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["set", "file", "pexels_id", "page"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)}/{len(PHOTOS)} photos in {TEST_DATA_DIR}")
    if failed:
        print("Failed:\n  " + "\n  ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
