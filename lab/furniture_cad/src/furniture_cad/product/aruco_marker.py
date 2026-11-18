"""Generate the capture ArUco marker (DICT_4X4_50 id 7) as PNG and a printable PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from furniture_cad.intake.rectify import ARUCO_DICT_NAME, ARUCO_ID, DEFAULT_MARKER_MM, _aruco_dict


def render_marker_png(
    out: Path | str,
    *,
    marker_id: int = ARUCO_ID,
    size_mm: float = DEFAULT_MARKER_MM,
    dpi: int = 300,
) -> Path:
    """Write a print-ready PNG whose square is exactly ``size_mm`` at ``dpi``."""
    import cv2
    from PIL import Image, ImageDraw

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    px = max(64, int(round(size_mm / 25.4 * dpi)))
    dictionary = _aruco_dict()
    # OpenCV generateImageMarker
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, px)
    # Pad with white margin + label strip
    margin = px // 8
    label_h = max(40, px // 6)
    canvas = Image.new("L", (px + 2 * margin, px + 2 * margin + label_h), 255)
    canvas.paste(Image.fromarray(marker), (margin, margin))
    draw = ImageDraw.Draw(canvas)
    text = f"ArUco {ARUCO_DICT_NAME} id={marker_id} · print at {size_mm:.0f} mm ({dpi} dpi) · 100% scale"
    draw.text((margin, px + 2 * margin + 4), text, fill=0)
    canvas.save(out)
    return out


def _minimal_pdf_with_png(png_path: Path, pdf_path: Path, *, size_mm: float) -> None:
    """Embed a PNG into a one-page PDF sized so the marker square prints at ``size_mm``.

    Uses a minimal PDF writer (no reportlab dependency). The page is letter-sized;
    the image is placed at 1:1 mm scale from the PNG dpi metadata when present.
    """
    from PIL import Image

    img = Image.open(png_path).convert("RGB")
    # Convert to JPEG bytes for lean PDF embedding
    import io

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    jpeg = buf.getvalue()
    w_px, h_px = img.size
    # Assume 300 dpi from render_marker_png
    dpi = float(img.info.get("dpi", (300, 300))[0] or 300)
    w_pt = w_px / dpi * 72.0
    h_pt = h_px / dpi * 72.0
    # Letter page
    page_w, page_h = 612.0, 792.0
    x0 = (page_w - w_pt) / 2
    y0 = page_h - 72 - h_pt

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
        f"/Contents 4 0 R /Resources << /XObject << /Im0 5 0 R >> /Font << /F1 6 0 R >> >> >> >>".encode()
    )
    content = (
        f"BT /F1 10 Tf 72 {page_h - 50} Td "
        f"(ArUco marker — print at 100% scale. Square must measure {size_mm:.0f} mm.) Tj ET\n"
        f"q {w_pt:.2f} 0 0 {h_pt:.2f} {x0:.2f} {y0:.2f} cm /Im0 Do Q\n"
    ).encode()
    add(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    add(
        f"<< /Type /XObject /Subtype /Image /Width {w_px} /Height {h_px} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\n"
        f"stream\n".encode()
        + jpeg
        + b"\nendstream"
    )
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Assemble xref
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    pdf_path.write_bytes(out)


def write_marker_pack(
    dest_dir: Path | str,
    *,
    marker_id: int = ARUCO_ID,
    size_mm: float = DEFAULT_MARKER_MM,
) -> dict[str, Any]:
    """Write PNG + PDF into ``dest_dir``; return paths and metadata."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    png = dest / f"aruco_{ARUCO_DICT_NAME.lower()}_id{marker_id}_{int(size_mm)}mm.png"
    pdf = dest / f"aruco_{ARUCO_DICT_NAME.lower()}_id{marker_id}_{int(size_mm)}mm.pdf"
    render_marker_png(png, marker_id=marker_id, size_mm=size_mm)
    _minimal_pdf_with_png(png, pdf, size_mm=size_mm)
    return {
        "schema": "aruco_marker_pack.v1",
        "dict": ARUCO_DICT_NAME,
        "id": marker_id,
        "size_mm": size_mm,
        "png": str(png),
        "pdf": str(pdf),
    }
