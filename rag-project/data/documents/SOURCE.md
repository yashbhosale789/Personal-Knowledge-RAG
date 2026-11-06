# Corpus — source

- Repository: https://github.com/udayallu/RAG-Multi-Corpus
- Commit: `39071af3f4dd25e59f5c59a6f9b6e8e99cd643b3`
- License: MIT (copied as `LICENSE`, Copyright (c) 2025 UDAY ALLU)
- Taken: every `.pdf` under `datasets/<Company>/pdf/` — 236 files, 6,582,761 bytes, 5 companies. Other formats, `bechmark/` and `metadata/` are not included.
- Layout: `datasets/<Company>/pdf/<name>.pdf` → `<name>.pdf`, flat (since 2026-11-06; was `<Company>/<name>.pdf` in `data/corpus_c2/`). The UI's Documents panel lists, replaces and deletes top-level files only. Four names occur in two companies and get a `<Company> - ` prefix (table below).
- Verified: every file's git blob hash equals the upstream tree entry at that commit; `SHA256SUMS` lists the sha256 of each file (`sha256sum -c SHA256SUMS`).

Renames (file contents unchanged):

| Upstream name | Here |
|---|---|
| `ASK Zia – Your 24:7 Banking Assistant.pdf` | `ASK Zia – Your 24-7 Banking Assistant.pdf` (`:` is not allowed in Windows file names) |
| ` Aventro Motors- How to Change a Tyre.pdf` | `_Aventro Motors- How to Change a Tyre.pdf` (leading space; same name as in corpus c1) |
| ` AventroZoom SUV.pdf` | `_AventroZoom SUV.pdf` (leading space) |
| ` Fine-Dining Menus.pdf` | `_Fine-Dining Menus.pdf` (leading space) |
| Cendara University `awards_and_recognition.pdf` | `Cendara University - awards_and_recognition.pdf` (name clash) |
| Velvera Technologies `awards_and_recognition.pdf` | `Velvera Technologies - awards_and_recognition.pdf` (name clash) |
| CloudWay-24 `Awards & Recognitions.pdf` | `CloudWay-24 - Awards & Recognitions.pdf` (name clash) |
| ZX Bank `Awards & Recognitions.pdf` | `ZX Bank - Awards & Recognitions.pdf` (name clash) |

Public synthetic test data; committed and usable in the demo (F-21). Since 2026-11-06 this is the only corpus: the image, CI and prod all use it. The 5 PDFs of the former corpus `c1` are byte-identical members (Aventro Motors).
