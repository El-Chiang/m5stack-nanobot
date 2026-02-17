#!/usr/bin/env python3
"""切分空洞骑士 spritesheet 为 M5 可直接播放的逐帧 JPG。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "Pillow is required. Install with: pip install pillow"
    ) from exc


# 对应用户给的 7 行状态定义
MOOD_ROWS = {
    "idle": 1,
    "happy": 2,
    "love": 2,
    "excited": 3,
    "celebrate": 3,
    "sleepy": 4,
    "snoring": 4,
    "working": 5,
    "angry": 6,
    "surprised": 6,
    "shy": 6,
    "dragging": 7,
}


def parse_rgb(text: str) -> tuple[int, int, int]:
    parts = [x.strip() for x in text.split(",")]
    if len(parts) != 3:
        raise ValueError("RGB must be in form R,G,B")
    rgb = tuple(int(x) for x in parts)
    for v in rgb:
        if v < 0 or v > 255:
            raise ValueError("RGB values must be 0..255")
    return rgb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=Path("assets/空洞骑士"),
        help="源素材目录（包含 manifest.json 与 sprite.jpg）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("assets/spirits/frames"),
        help="输出帧目录",
    )
    parser.add_argument(
        "--out-manifest",
        type=Path,
        default=Path("assets/spirits/frames_manifest.json"),
        help="输出映射 manifest",
    )
    parser.add_argument("--width", type=int, default=120, help="输出帧宽度")
    parser.add_argument("--height", type=int, default=120, help="输出帧高度")
    parser.add_argument("--quality", type=int, default=72, help="JPG 质量（1-95）")
    parser.add_argument(
        "--keep-bg",
        action="store_true",
        help="保留原始背景色（默认会做粉色背景替换）",
    )
    parser.add_argument(
        "--bg-color",
        default="0,0,0",
        help="背景替换目标颜色，格式 R,G,B，默认黑色",
    )
    parser.add_argument(
        "--key-threshold",
        type=int,
        default=80,
        help="兼容参数：作为 --key-high 默认值（欧氏距离）",
    )
    parser.add_argument(
        "--key-low",
        type=int,
        default=24,
        help="色键软阈值下界（<=该值视为纯背景）",
    )
    parser.add_argument(
        "--key-high",
        type=int,
        default=None,
        help="色键软阈值上界（>=该值视为纯前景），默认取 --key-threshold",
    )
    parser.add_argument(
        "--despill",
        type=float,
        default=0.55,
        help="边缘去溢色强度（0~1，越大越去粉边）",
    )
    return parser.parse_args()


def load_source_manifest(src_dir: Path) -> dict:
    manifest_path = src_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Missing manifest: %s" % manifest_path)
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def crop_frame(sprite: Image.Image, left: int, top: int, width: int, height: int) -> Image.Image:
    """超出边界时自动补黑，避免最后一行像素缺失报错。"""
    right = min(left + width, sprite.width)
    bottom = min(top + height, sprite.height)
    cut = sprite.crop((left, top, right, bottom))

    if cut.width == width and cut.height == height:
        return cut

    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    canvas.paste(cut, (0, 0))
    return canvas


def remove_bg_by_chroma_soft(
    frame: Image.Image,
    bg_rgb: tuple[int, int, int],
    low: int,
    high: int,
    despill: float,
) -> Image.Image:
    """软色键抠图 + 去溢色（适合 JPG 精灵图边缘）。"""
    w, h = frame.size
    corners = [
        frame.getpixel((0, 0)),
        frame.getpixel((w - 1, 0)),
        frame.getpixel((0, h - 1)),
        frame.getpixel((w - 1, h - 1)),
    ]
    key_rgb = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    low2 = low * low
    high2 = high * high
    if high2 <= low2:
        high2 = low2 + 1

    out = []
    for r, g, b in frame.getdata():
        d2 = (r - key_rgb[0]) ** 2 + (g - key_rgb[1]) ** 2 + (b - key_rgb[2]) ** 2

        if d2 <= low2:
            alpha = 0.0
        elif d2 >= high2:
            alpha = 1.0
        else:
            # smoothstep 过渡，边缘更平滑
            t = (d2 - low2) / float(high2 - low2)
            alpha = t * t * (3.0 - 2.0 * t)

        # 去溢色：对半透明边缘做去粉/去绿
        if alpha < 1.0 and despill > 0:
            edge = (1.0 - alpha) * despill
            gray = (r + g + b) / 3.0
            r = int(r * (1.0 - edge) + gray * edge)
            g = int(g * (1.0 - edge) + gray * edge)
            b = int(b * (1.0 - edge) + gray * edge)

        rr = int(r * alpha + bg_rgb[0] * (1.0 - alpha))
        gg = int(g * alpha + bg_rgb[1] * (1.0 - alpha))
        bb = int(b * alpha + bg_rgb[2] * (1.0 - alpha))
        out.append((rr, gg, bb))

    composited = Image.new("RGB", frame.size)
    composited.putdata(out)
    return composited


def build_frames(args: argparse.Namespace) -> dict:
    src_manifest = load_source_manifest(args.src_dir)
    sprite_file = args.src_dir / src_manifest["spriteFile"]
    if not sprite_file.exists():
        raise FileNotFoundError("Missing sprite image: %s" % sprite_file)

    frame_w = int(src_manifest["frameWidth"])
    frame_h = int(src_manifest["frameHeight"])
    cols = int(src_manifest["columns"])
    frame_count = int(src_manifest["frameCount"])

    sprite = Image.open(sprite_file).convert("RGB")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    bg_rgb = parse_rgb(args.bg_color)
    key_high = args.key_high if args.key_high is not None else args.key_threshold
    if args.key_low < 0:
        args.key_low = 0
    if key_high <= args.key_low:
        key_high = args.key_low + 1

    frames_per_row: dict[str, int] = {}

    for idx in range(frame_count):
        row_idx = idx // cols  # 0-based
        col_idx = idx % cols
        row = row_idx + 1      # 1-based

        left = col_idx * frame_w
        top = row_idx * frame_h
        frame = crop_frame(sprite, left, top, frame_w, frame_h)

        if not args.keep_bg:
            # 先抠图再缩放，避免缩放引入粉边
            frame = remove_bg_by_chroma_soft(
                frame,
                bg_rgb=bg_rgb,
                low=args.key_low,
                high=key_high,
                despill=max(0.0, min(1.0, args.despill)),
            )

        frame = frame.resize((args.width, args.height), Image.LANCZOS)

        out_name = "r%02d_f%02d.jpg" % (row, col_idx)
        out_path = args.out_dir / out_name
        frame.save(out_path, format="JPEG", quality=args.quality, optimize=True)
        frames_per_row[str(row)] = frames_per_row.get(str(row), 0) + 1

    return {
        "source": str(args.src_dir),
        "sprite": str(sprite_file),
        "frame_count": frame_count,
        "frame_size": [args.width, args.height],
        "columns": cols,
        "frames_per_row": frames_per_row,
        "background_removed": not args.keep_bg,
        "background_fill": list(bg_rgb),
        "key_low": args.key_low,
        "key_high": key_high,
        "despill": max(0.0, min(1.0, args.despill)),
        "mood_rows": MOOD_ROWS,
    }


def main() -> int:
    args = parse_args()
    out_manifest = build_frames(args)
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.out_manifest.open("w", encoding="utf-8") as f:
        json.dump(out_manifest, f, ensure_ascii=False, indent=2)

    print("Generated spirit frames:")
    print("  dir:", args.out_dir)
    print("  manifest:", args.out_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
