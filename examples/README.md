# Test images

A small hand-picked set of hard cases used to judge every stage of the pipeline.
Each image is chosen to break a specific step:

| Case | Why it is hard | Stage it stresses |
|---|---|---|
| Curly / flyaway hair | Thin semi-transparent strands | Segmentation, matting |
| White product on white | Low contrast between subject and background | Segmentation |
| Glass / transparent object | Background shows *through* the subject | Matting, compositing |
| Product with a cast shadow | Shadow must be kept, not cut out | Shadow extraction |
| Several people | Which subject is "the" subject? | Segmentation |
| Busy street background | Shadow is impossible to separate cleanly | Shadow extraction (fallback) |
| Phone photo with EXIF rotation | Pixels stored sideways | Input handling |
| PNG with transparency / CMYK JPEG | Unusual colour modes | Input handling |

Images are added in a later step, along with where each one came from.
