from PIL import Image
import numpy as np

from app.features.palette.ops import kmeans_palette, extract_palette, rgb_to_hsl


def test_kmeans_palette_percentages_sum() -> None:
    # Verify K-means clustering percentages sum to near 100 percent on gradient image.
    width, height = 120, 120
    x_coords = np.linspace(0, 255, width, dtype=np.uint8)
    gradient_array = np.tile(x_coords, (height, 1))
    rgb_array = np.stack([gradient_array, 255 - gradient_array, gradient_array // 2], axis=-1)
    img = Image.fromarray(rgb_array, mode="RGB")

    swatches = kmeans_palette(img, n_colors=6, max_dimension=120)
    assert len(swatches) == 6
    total_percentage = sum(swatch.percentage for swatch in swatches)
    assert total_percentage >= 95.0

    # Ensure swatches are sorted descending by percentage
    for idx in range(len(swatches) - 1):
        assert swatches[idx].percentage >= swatches[idx + 1].percentage

    # Ensure HSL is populated on each swatch
    for swatch in swatches:
        assert swatch.hsl is not None
        assert len(swatch.hsl) == 3


def test_kmeans_palette_solid_color() -> None:
    # Verify K-means handles single solid color cleanly.
    img = Image.new("RGB", (64, 64), (120, 45, 200))
    swatches = kmeans_palette(img, n_colors=3)
    assert len(swatches) >= 1
    assert swatches[0].percentage >= 99.0
    assert swatches[0].rgb == (120, 45, 200)


def test_rgb_to_hsl_calculation() -> None:
    # Verify accurate RGB to HSL color space conversion.
    assert rgb_to_hsl((255, 0, 0)) == (0, 100, 50)
    assert rgb_to_hsl((0, 255, 0)) == (120, 100, 50)
    assert rgb_to_hsl((0, 0, 255)) == (240, 100, 50)
    assert rgb_to_hsl((0, 0, 0)) == (0, 0, 0)
    assert rgb_to_hsl((255, 255, 255)) == (0, 0, 100)


def test_extract_palette_median_cut_has_hsl() -> None:
    # Verify median-cut palette extraction populates HSL values.
    img = Image.new("RGB", (64, 64), (255, 128, 0))
    swatches = extract_palette(img, n_colors=4, method="median-cut")
    assert len(swatches) >= 1
    assert swatches[0].hsl is not None

