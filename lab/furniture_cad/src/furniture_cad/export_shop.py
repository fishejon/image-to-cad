"""Shop sheet exports — DXF outline + PDF summary stubs (Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_cutlist_csv(parts_v2: dict[str, Any], dest: Path | str) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = ["id,qty,material,finished_t,finished_w,finished_l,blank_t,blank_w,blank_l"]
    for p in parts_v2.get("parts") or []:
        fin = p.get("finished_mm") or [0, 0, 0]
        blank = p.get("blank_mm") or fin
        lines.append(
            f"{p.get('id')},{p.get('qty')},{p.get('material')},"
            f"{fin[0]},{fin[1]},{fin[2]},{blank[0]},{blank[1]},{blank[2]}"
        )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def export_dxf_stub(parts_v2: dict[str, Any], dest: Path | str) -> Path:
    """Minimal DXF: rectangles for each unique part blank (ASCII DXF R12-ish)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    entities: list[str] = []
    x = 0.0
    for p in parts_v2.get("parts") or []:
        blank = p.get("blank_mm") or p.get("finished_mm") or [10, 10, 10]
        # Use width × length as face
        w, L = float(blank[1]), float(blank[2])
        entities.append(_lwpoly(x, 0, w, L, layer=str(p.get("id") or "part")))
        x += w + 20.0
    body = _dxf_wrap(entities)
    dest.write_text(body, encoding="utf-8")
    return dest


def export_pdf_stub(parts_v2: dict[str, Any], dest: Path | str, *, title: str = "Cut list") -> Path:
    """Minimal one-page PDF (text only) without external deps."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [title, ""]
    for p in parts_v2.get("parts") or []:
        fin = p.get("finished_mm") or [0, 0, 0]
        lines.append(f"{p.get('qty')}× {p.get('id')}  {fin[0]}×{fin[1]}×{fin[2]} mm  {p.get('material')}")
    content = "\n".join(lines)
    # Very small PDF: one page with Helvetica text via literal strings
    # Escape for PDF literal
    esc = content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Position lines
    y = 750
    tj_ops = []
    for line in content.split("\n"):
        e = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        tj_ops.append(f"BT /F1 10 Tf 50 {y} Td ({e}) Tj ET")
        y -= 14
    stream = "\n".join(tj_ops)
    objects = []
    objects.append("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append("2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n{stream}\nendstream\nendobj\n")
    objects.append("5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    pdf = ["%PDF-1.4\n"]
    xref_positions = [0]
    for obj in objects:
        xref_positions.append(sum(len(x) for x in pdf))
        pdf.append(obj)
    xref_start = sum(len(x) for x in pdf)
    pdf.append(f"xref\n0 {len(xref_positions)}\n")
    pdf.append("0000000000 65535 f \n")
    for pos in xref_positions[1:]:
        pdf.append(f"{pos:010d} 00000 n \n")
    pdf.append(f"trailer<< /Size {len(xref_positions)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n")
    dest.write_bytes("".join(pdf).encode("latin-1", errors="replace"))
    _ = esc  # silence unused in minimal path
    return dest


def _lwpoly(x: float, y: float, w: float, h: float, *, layer: str) -> str:
    return (
        f"0\nLWPOLYLINE\n8\n{layer}\n90\n4\n70\n1\n"
        f"10\n{x}\n20\n{y}\n"
        f"10\n{x + w}\n20\n{y}\n"
        f"10\n{x + w}\n20\n{y + h}\n"
        f"10\n{x}\n20\n{y + h}\n"
    )


def _dxf_wrap(entities: list[str]) -> str:
    header = "0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"
    footer = "0\nENDSEC\n0\nEOF\n"
    return header + "".join(entities) + footer
