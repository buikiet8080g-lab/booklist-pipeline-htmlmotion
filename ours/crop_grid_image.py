#!/usr/bin/env python3
# 06 九宫格切图：3×3 大图按格切开，给 y2_vox / 照片素材用（迁移自 booklist-pipeline-Lite，未改逻辑）。
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image


ASPECTS = {
    "9:16": (9, 16),
    "16:9": (16, 9),
}


def parse_aspect(cell_aspect: str) -> tuple[int, int]:
    if cell_aspect not in ASPECTS:
        raise ValueError("cell_aspect must be one of: 9:16, 16:9")
    return ASPECTS[cell_aspect]


def center_crop_box(
    width: int,
    height: int,
    aspect: tuple[int, int],
    *,
    rows: int,
    cols: int,
) -> tuple[int, int, int, int]:
    aspect_w, aspect_h = aspect
    scale = min(width // (aspect_w * cols), height // (aspect_h * rows))
    if scale < 1:
        raise ValueError(f"input image is too small for a {rows}x{cols} grid at the requested cell_aspect")
    crop_w = aspect_w * cols * scale
    crop_h = aspect_h * rows * scale
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    return (left, top, left + crop_w, top + crop_h)


def inset_box(
    left: float,
    top: float,
    right: float,
    bottom: float,
    inset_ratio: float,
) -> tuple[int, int, int, int]:
    if not 0 <= inset_ratio < 0.5:
        raise ValueError("inset_ratio must be >= 0 and < 0.5")
    width = right - left
    height = bottom - top
    inset_x = width * inset_ratio
    inset_y = height * inset_ratio
    return (
        int(round(left + inset_x)),
        int(round(top + inset_y)),
        int(round(right - inset_x)),
        int(round(bottom - inset_y)),
    )


def crop_grid_image(
    input_path: Path | str,
    output_dir: Path | str,
    *,
    cell_aspect: str = "9:16",
    inset_ratio: float = 0.05,
    prefix: str | None = None,
    rows: int = 3,
    cols: int = 3,
) -> list[Path]:
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive integers")

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    aspect = parse_aspect(cell_aspect)
    with Image.open(input_path) as source:
        image = source.copy()

    base_box = center_crop_box(image.width, image.height, aspect, rows=rows, cols=cols)
    grid = image.crop(base_box)
    cell_w = grid.width / cols
    cell_h = grid.height / rows
    output_w = int(round(cell_w))
    output_h = int(round(cell_h))
    name_prefix = prefix or input_path.stem

    outputs: list[Path] = []
    for row in range(rows):
        for col in range(cols):
            index = row * cols + col + 1
            left = col * cell_w
            top = row * cell_h
            right = (col + 1) * cell_w
            bottom = (row + 1) * cell_h
            crop_box = inset_box(left, top, right, bottom, inset_ratio)
            cell = grid.crop(crop_box).resize((output_w, output_h), Image.Resampling.LANCZOS)
            output_path = output_dir / f"{name_prefix}-cell-{index:02d}.png"
            cell.save(output_path)
            outputs.append(output_path)
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crop a booklist grid image into candidate images.")
    parser.add_argument("--input", required=True, help="Path to the grid image.")
    parser.add_argument("--output-dir", required=True, help="Directory for cropped cell images.")
    parser.add_argument("--cell-aspect", choices=sorted(ASPECTS), default="9:16", help="Target aspect ratio for each cell.")
    parser.add_argument("--rows", type=int, default=3, help="Grid row count. Default: 3.")
    parser.add_argument("--cols", type=int, default=3, help="Grid column count. Default: 3.")
    parser.add_argument("--inset", type=float, default=0.05, help="Center inset ratio used to remove grid borders. Default: 0.05.")
    parser.add_argument("--prefix", help="Output filename prefix. Defaults to input stem.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    outputs = crop_grid_image(
        args.input,
        args.output_dir,
        cell_aspect=args.cell_aspect,
        inset_ratio=args.inset,
        prefix=args.prefix,
        rows=args.rows,
        cols=args.cols,
    )
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
