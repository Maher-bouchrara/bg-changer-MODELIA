# Model benchmark

Compares the segmentation models on the same images, so the default model is
chosen from measurements rather than assumed.

**Planned measurements**

| Metric | What it tells us |
|---|---|
| MAE | Average per-pixel error of the alpha matte (lower is better) |
| max F-measure | How well the subject region matches ground truth |
| Boundary F | Quality at the edges, where models differ most |
| Latency (GPU / CPU) | Seconds per image |
| Peak VRAM | Memory needed on the GPU |

The scripts and the results table are added in the benchmark step.
