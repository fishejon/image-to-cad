"""Perspective shaded render stub (Phase 0/1). Falls back to orthographic silhouette if pyrender missing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from furniture_cad.render_views import render_stl_views


def render_perspective_stub(
    stl_path: Path | str,
    out_dir: Path | str,
    *,
    views: list[str] | None = None,
) -> dict[str, Any]:
    """Prefer pyrender shaded views; otherwise emit labeled orthographic placeholders."""
    stl_path = Path(stl_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    views = views or ["front", "three_quarter", "section"]
    try:
        import pyrender  # noqa: F401
        import trimesh

        # Minimal shaded offscreen — if EGL fails, fall through
        mesh = trimesh.load_mesh(str(stl_path), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
        tm = pyrender.Mesh.from_trimesh(mesh, smooth=False)
        scene = pyrender.Scene(bg_color=[245, 242, 236, 255])
        scene.add(tm)
        camera = pyrender.PerspectiveCamera(yfov=np_pi_3())
        scene.add(camera, pose=_cam_pose())
        light = pyrender.DirectionalLight(color=np_ones3(), intensity=3.0)
        scene.add(light, pose=_cam_pose())
        r = pyrender.OffscreenRenderer(512, 512)
        color, _ = r.render(scene)
        r.delete()
        from PIL import Image

        path = out_dir / "front_shaded.png"
        Image.fromarray(color).save(path)
        return {"ok": True, "method": "pyrender", "views": {"front": str(path)}}
    except Exception as e:
        # Map three_quarter → iso, section → side for silhouette fallback
        mapped = []
        for v in views:
            if v in ("three_quarter", "3/4"):
                mapped.append("iso")
            elif v == "section":
                mapped.append("side")
            else:
                mapped.append(v if v in ("front", "side", "iso", "top", "back") else "front")
        meta = render_stl_views(stl_path, out_dir, mapped)
        meta["method"] = "orthographic_fallback"
        meta["fallback_reason"] = f"{type(e).__name__}: {e}"
        meta["ok"] = True
        return meta


def np_pi_3() -> float:
    import math

    return math.pi / 3


def np_ones3():
    import numpy as np

    return np.ones(3)


def _cam_pose():
    import numpy as np

    pose = np.eye(4)
    pose[2, 3] = 2.5
    return pose
