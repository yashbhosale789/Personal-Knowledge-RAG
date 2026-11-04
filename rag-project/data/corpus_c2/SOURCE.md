# Corpus c2 — source

- Repository: https://github.com/udayallu/RAG-Multi-Corpus
- Commit: `39071af3f4dd25e59f5c59a6f9b6e8e99cd643b3`
- License: MIT (copied as `LICENSE`, Copyright (c) 2025 UDAY ALLU)
- Taken: every `.pdf` under `datasets/<Company>/pdf/` — 236 files, 6,582,761 bytes, 5 companies. Other formats, `bechmark/` and `metadata/` are not included.
- Layout: `datasets/<Company>/pdf/<name>.pdf` → `<Company>/<name>.pdf`.
- Verified: every file's git blob hash equals the upstream tree entry at that commit; `SHA256SUMS` lists the sha256 of each file (`sha256sum -c SHA256SUMS`).

Renames (file contents unchanged):

| Upstream name | Here |
|---|---|
| `ASK Zia – Your 24:7 Banking Assistant.pdf` | `ASK Zia – Your 24-7 Banking Assistant.pdf` (`:` is not allowed in Windows file names) |
| ` Aventro Motors- How to Change a Tyre.pdf` | `_Aventro Motors- How to Change a Tyre.pdf` (leading space; same name as in corpus c1) |
| ` AventroZoom SUV.pdf` | `_AventroZoom SUV.pdf` (leading space) |
| ` Fine-Dining Menus.pdf` | `_Fine-Dining Menus.pdf` (leading space) |

Public synthetic test data; committed and usable in the demo (F-21). Offline only: excluded from the Docker image by `.dockerignore`, and never copied into `data/documents/` (corpus c1).
