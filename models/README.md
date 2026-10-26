# models/

Model weights live here, one folder per model. They are **not committed** (too
large, and each has its own license). Fetch them with:

```bash
uv run python scripts/download_models.py
```

| Folder | Model | Source | License | Size |
|---|---|---|---|---|
| `birefnet/` | BiRefNet (general) | [ZhengPeng7/BiRefNet](https://huggingface.co/ZhengPeng7/BiRefNet) | MIT | 445 MB |
| `birefnet-matting/` | BiRefNet, matting variant (soft edges) | [ZhengPeng7/BiRefNet-matting](https://huggingface.co/ZhengPeng7/BiRefNet-matting) | MIT | 885 MB |
| `rmbg-2.0/` | BRIA RMBG-2.0 | [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) | **Non-commercial**, gated | 885 MB |
| `ben2/` | BEN2 base | [PramaLLC/BEN2](https://huggingface.co/PramaLLC/BEN2) | MIT | 381 MB |
| `inspyrenet/` | InSPyReNet base | [plemeri/transparent-background](https://github.com/plemeri/transparent-background) release 1.2.12 | MIT | 368 MB |

**Total: about 2.96 GB** (2.76 GiB, as Windows Explorer reports it).

Each Hugging Face folder also has a small hidden `.cache/` folder; the download
library uses it to resume interrupted downloads. It can be ignored.

All are pinned to exact versions in [`scripts/download_models.py`](../scripts/download_models.py).

**RMBG-2.0 needs two manual steps** (the script explains them if they are missing):
accept BRIA's terms on its Hugging Face page, then log in with `uv run hf auth login`.
