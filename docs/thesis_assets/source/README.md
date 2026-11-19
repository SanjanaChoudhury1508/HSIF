# Figure generation source

- `build_assets.py` contains the editable, source-referenced specifications for all 25 figures. It uses only the Python standard library and writes per-figure Mermaid (`.mmd`) and JSON render specifications plus SVG exports under `docs/thesis_assets/`.
- `render_png.ps1` reads those JSON specifications and writes high-resolution PNGs using Windows System.Drawing. It does not load project secrets, call external APIs, or modify application files.

Run from the repository root:

```powershell
.venv\Scripts\python.exe docs\thesis_assets\source\build_assets.py
& .\docs\thesis_assets\source\render_png.ps1
```

After changing a diagram specification, regenerate both the SVG and PNG before using the figure. The Mermaid source is retained in `docs/thesis_assets/diagram_sources/` for editing or rendering in another Mermaid-compatible tool.
