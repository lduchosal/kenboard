#!/usr/bin/env python3
"""Generate a pixel-art SVG from a vector SVG source.

Usage:
    python scripts/pixelart.py [OPTIONS] INPUT_SVG

Options:
    --size N          Pixel grid size (default: 24)
    --render N        Hi-res render size before downscale (default: 4096)
    --output FILE     Output SVG path (default: <input>-pixel.svg)
    --swap BG,FG      Swap colors: BG=background hex, FG=foreground hex
                      Example: --swap ff0000,ffffff (red bg, white fg)
    --background HEX  Background color for the source render (default: ffffff)
    --preview         Also save intermediate PNGs for debugging

Examples:
    # Basic pixel art
    python scripts/pixelart.py logo-robot2.svg

    # Swiss flag style (white robot on red)
    python scripts/pixelart.py logo-robot2.svg --swap ff0000,ffffff

    # Custom grid size
    python scripts/pixelart.py logo-robot2.svg --size 32 --render 4096

    # Deploy as kenboard logo
    python scripts/pixelart.py logo-robot2.svg --swap ff0000,ffffff \\
        --output logo.svg && cp logo.svg src/dashboard/static/logo.svg
"""

import argparse
import io
import sys
from pathlib import Path

try:
    import cairosvg
    from PIL import Image
except ImportError:
    print(
        "Missing dependencies. Install with:\n"
        "    pip install cairosvg Pillow",
        file=sys.stderr,
    )
    sys.exit(1)


def render_svg(svg_path: str, render_size: int, bg_color: str) -> Image.Image:
    """Render an SVG to a square PNG at the given size."""
    png_data = cairosvg.svg2png(
        url=svg_path,
        output_width=render_size,
        output_height=render_size,
        background_color=f"#{bg_color}",
    )
    return Image.open(io.BytesIO(png_data)).convert("RGB")


def downscale(img: Image.Image, size: int) -> Image.Image:
    """Downscale to NxN using Lanczos resampling."""
    return img.resize((size, size), Image.Resampling.LANCZOS)


def swap_colors(
    img: Image.Image, bg_hex: str, fg_hex: str
) -> Image.Image:
    """Swap foreground/background colors.

    Uses brightness to interpolate between the new bg and fg colors,
    preserving anti-aliased edges.
    """
    bg = tuple(int(bg_hex[i : i + 2], 16) for i in (0, 2, 4))
    fg = tuple(int(fg_hex[i : i + 2], 16) for i in (0, 2, 4))
    out = Image.new("RGB", img.size)
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            brightness = (r + g + b) / (3 * 255)
            t = max(0.0, min(1.0, (brightness - 0.5) / 0.5))
            nr = int(fg[0] * (1 - t) + bg[0] * t)
            ng = int(fg[1] * (1 - t) + bg[1] * t)
            nb = int(fg[2] * (1 - t) + bg[2] * t)
            out.putpixel((x, y), (nr, ng, nb))
    return out


def generate_svg(img: Image.Image) -> str:
    """Generate a pixel-grid SVG from a PIL image."""
    size = img.width
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
    ]
    for y in range(size):
        for x in range(size):
            r, g, b = img.getpixel((x, y))
            lines.append(
                f'  <rect x="{x}" y="{y}" width="1" height="1" '
                f'fill="#{r:02x}{g:02x}{b:02x}"/>'
            )
    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Generate pixel-art SVG from a vector SVG source."
    )
    parser.add_argument("input", help="Input SVG file")
    parser.add_argument("--size", type=int, default=24, help="Pixel grid size (default: 24)")
    parser.add_argument("--render", type=int, default=4096, help="Hi-res render size (default: 4096)")
    parser.add_argument("--output", help="Output SVG path (default: <input>-pixel.svg)")
    parser.add_argument("--swap", help="Swap colors: BG_HEX,FG_HEX (e.g. ff0000,ffffff)")
    parser.add_argument("--background", default="ffffff", help="Background color hex (default: ffffff)")
    parser.add_argument("--preview", action="store_true", help="Save intermediate PNGs")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix("").with_name(input_path.stem + "-pixel.svg")

    print(f"Rendering {input_path} at {args.render}x{args.render}...")
    img_hires = render_svg(str(input_path), args.render, args.background)

    print(f"Downscaling to {args.size}x{args.size}...")
    img_small = downscale(img_hires, args.size)

    if args.preview:
        preview = input_path.with_name(f"{input_path.stem}-{args.size}.png")
        img_small.save(str(preview))
        print(f"  Preview: {preview}")

    if args.swap:
        parts = args.swap.split(",")
        if len(parts) != 2 or not all(len(p) == 6 for p in parts):
            print("Error: --swap must be BG_HEX,FG_HEX (e.g. ff0000,ffffff)", file=sys.stderr)
            sys.exit(1)
        bg_hex, fg_hex = parts
        print(f"Swapping colors: bg=#{bg_hex}, fg=#{fg_hex}...")
        img_small = swap_colors(img_small, bg_hex, fg_hex)
        if args.preview:
            preview = input_path.with_name(f"{input_path.stem}-{args.size}-swapped.png")
            img_small.save(str(preview))
            print(f"  Preview: {preview}")

    print(f"Generating SVG pixel grid ({args.size * args.size} rects)...")
    svg_content = generate_svg(img_small)

    output_path.write_text(svg_content, encoding="utf-8")
    size_kb = len(svg_content) / 1024
    print(f"Done: {output_path} ({size_kb:.0f}KB)")


if __name__ == "__main__":
    main()
