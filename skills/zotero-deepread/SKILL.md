---
name: zotero-deepread
description: Deep-read a paper that already exists in the user's local Zotero library and save the result into the Obsidian vault. Use when the user says "精读我Zotero库中的某篇论文", "精读这篇论文", "精读某篇论文", "帮我读这篇论文", or asks to read/translate a paper located in their Zotero library. The reading step defaults to the nature-reader skill (full bilingual reader), but the user may name another skill or combine several.
---

# Zotero Deepread

Locate a paper in Zotero, run a deep-reading workflow on it, and save the output into the Obsidian vault as a per-paper attachment.

## Environment facts (do not re-derive)

- Zotero 9 local API: `http://127.0.0.1:23119/api/` (read-only; enough for locating papers and PDFs).
- Obsidian vault path and literature folder come from `config.json` (default `~/.zotero-codex/config.json`); notes live in `Literature/`.
- This skill owns only two steps: locating the paper and saving the output. The actual reading is delegated to one or more reader skills.

## Workflow

1. Locate the paper the user means.
   - By title/keyword: `python scripts/get_paper.py find --query "ORB-SLAM3"`
   - Metadata + PDF path: `python scripts/get_paper.py locate --key <ITEM_KEY>`
   The output includes `citekey`, `doi`, `pdf_path`, title, abstract, and authors.
2. Choose the reading recipe.
   - Default reader: `nature-reader` (full bilingual Chinese-English reader). Follow its routing: `manifest.yaml`, `always_load` files, and the fragment matching the source format.
   - If the user names another skill or asks to combine (for example "用 X 技能精读", "精读并生成概念图", "精读 + 写综述"), use those skills instead of or in addition to nature-reader. Any skills matched by the user's prompt are available; use them.
   - Pass the resolved `pdf_path` (or `doi` when there is no PDF) to each reader skill.
3. Save outputs into a per-paper folder: `<literature_dir>/<citekey> 精读/`.
   - nature-reader produces `paper.md` + `source_map.json` + `translation_notes.md` + `assets/` (the canonical full-text reader).
   - Other readers save their artifacts under the same folder with clear names (for example `<citekey> 精读/概念图.md`, `<citekey> 精读/综述.md`).
   - If only a non-reader artifact is produced (such as a summary), keep it in the same folder and link it from the light note.
4. Create or update the light note `<literature_dir>/@<citekey>.md` (see `references/obsidian-note-layout.md`) and link the main artifact(s), for example `![[<citekey> 精读/paper]]`.

## Rules

- Only locating + saving are mandatory; the reader is pluggable and defaults to nature-reader.
- Honor the user's explicitly named skills; do not force nature-reader when they asked for something else.
- Do not degrade a full-reader request into a summary-only output unless the user asked for a summary.
- Keep everything inside the vault (D:), never on C:.
- If the item has no citekey yet, `locate` prints a derived fallback key; note it can be pinned later in Better BibTeX.
- Config overrides: `--config <path>` or env `ZOTERO_CODEX_CONFIG`; default `~/.zotero-codex/config.json`.
