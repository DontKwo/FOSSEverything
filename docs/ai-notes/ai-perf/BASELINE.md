# Baseline Performance Measurements (Branch: ai/perf)

## 1. Startup & Import Cost Breakdown
- Python startup baseline with `-X importtime`:
  - `import app.web.api` total time: ~2355 ms
  - Major culprits identified via `import time` profiling:
    * `app.web.api.tool_converter`: ~1111 ms cumulative (loads `trimesh` ~920 ms, which pulls in `scipy.spatial`, `networkx`, and 104 submodules)
    * `app.features.unit_converter.ops`: ~791 ms cumulative (~645 ms self time initializing two Pint unit registries `UREG` and `EXPR_UREG` at top-level)
    * Combined eager cost: ~1.7 seconds of the 2.3s startup time.

## 2. Heavy Dependency Import Cost (Isolated Process)
Individual process cold import timings:
- `rembg`: 1696.68 ms
- `trimesh`: 996.21 ms
- `pdf2docx`: 429.72 ms
- `cairosvg`: 370.07 ms
- `pint`: 353.03 ms
- `psd_tools`: 345.86 ms
- `matplotlib`: 312.23 ms
- `spotipy`: 297.67 ms
- `language_tool_python`: 224.60 ms
- `pymupdf`: 179.99 ms
- `h5py`: 164.12 ms
- `scipy`: 144.21 ms
- `cv2`: 142.33 ms
- `shapely`: 138.56 ms
- `rawpy`: 124.90 ms
- `pikepdf`: 112.11 ms
- `googleapiclient`: 24.85 ms

## 3. Router Open Latency (Playwright Harness)
Measured cold open (first time navigating to tool) vs warm open (switching away and back):
- `archive`: cold 61.01 ms | warm 12.44 ms
- `collage`: cold 57.29 ms | warm 19.24 ms
- `compressor`: cold 16.66 ms | warm 12.37 ms
- `converter`: cold 24.24 ms | warm 61.26 ms
- `data`: cold 17.89 ms | warm 17.30 ms
- `encoding`: cold 13.84 ms | warm 12.46 ms
- `images`: cold 28.66 ms | warm 16.69 ms
- `markdown`: cold 38.77 ms | warm 21.64 ms
- `media`: cold 23.19 ms | warm 19.92 ms
- `metadata`: cold 18.33 ms | warm 20.76 ms
- `model3d`: cold 53.22 ms | warm 26.23 ms
- `network_monitor`: cold 45.58 ms | warm 25.05 ms
- `ocr`: cold 31.28 ms | warm 27.14 ms
- `palette`: cold 28.24 ms | warm 16.02 ms
- `pdf`: cold 37.69 ms | warm 17.02 ms
- `playlist`: cold 21.63 ms | warm 15.23 ms
- `qr`: cold 27.62 ms | warm 21.01 ms
- `renamer`: cold 22.75 ms | warm 22.02 ms
- `resume`: cold 371.70 ms | warm 341.76 ms  <-- Target for optimization (< 150 ms target)
- `text_tools`: cold 37.37 ms | warm 26.72 ms
- `unit_converter`: cold 87.95 ms | warm 36.97 ms

## 4. API Method Latencies (> 200 ms)
- 346 total public WebApi methods audited.
- Methods exceeding 200 ms latency during default/inspection calls:
  * `images_prefetch_models`: ~1176 ms (synchronous cache directory and network inspection)
  * `shell_get_associations`: ~370 ms (queries desktop association files across 7 common extensions)

## 5. Front-End Metrics
- `index.html` script tags: 49 scripts, ~1.05 MB total unminified JS source.
- Heap memory after 100 tool switch cycles: stable (no memory leaks detected across tool lifecycle).
- DOM element counts per tool: lean (< 500 nodes per view).
- Animations strictly adhere to transform and opacity.
