---
name: zotero-find
description: Find high-quality academic papers for the user's research direction and add the top pick to the local Zotero "From_codex" collection. Use when the user asks, in Chinese or English, for a paper to read, for example "我需要一篇论文", "帮我找一篇论文", "找一篇高质量论文", "推荐一篇论文", "检索论文并存入Zotero", or any request to search academic sources and save a paper into Zotero. Filters candidates to CCF-B-or-above journals, IEEE Transactions series, or the conferences ICRA, IROS, ICCV, CVPR, ECCV, 3DV, RSS, ICLR, ICML, NeurIPS, IJCAI, AAAI.
---

# Zotero Find

Find a high-quality paper for the user's research direction and add it to the Zotero `From_codex` collection using the local connector API.

## Environment facts (do not re-derive)

- Zotero 9 runs on `http://127.0.0.1:23119`. The `/api/` layer is READ-ONLY on Zotero 9; writes go through `/connector/`.
- Zotero data directory and Obsidian vault paths come from `config.json` (default `~/.zotero-codex/config.json`).
- Target collection: `From_codex` (must already exist in Zotero; create it manually once if missing).

## Workflow

1. Determine the search query.
   - If the user named a topic, use it.
   - Otherwise infer it: run `python scripts/find_and_add.py infer` and read the collections, recent item titles, and tags from the output.
2. Search and preview (never write on the first pass):
   `python scripts/find_and_add.py search --query "<topic>" --dry-run`
   The script deduplicates Semantic Scholar + Crossref results, applies the venue filter, ranks by citations/venue/recency, and prints the winners and the exact POST it would send.
3. Confirm the winning paper is relevant, then add it:
   `python scripts/find_and_add.py search --query "<topic>" --top 1`
   This creates the item via `POST /connector/saveItems` and moves it into `From_codex` via `POST /connector/updateSession`.
4. Add a specific paper by DOI directly:
   `python scripts/find_and_add.py add --doi "10.1109/TRO.2021.3075644"`

## Rules

- Never bypass the venue filter unless the user explicitly overrides it. See `references/venue-policy.md`.
- Always run with `--dry-run` first and show the user the top candidates before writing to Zotero.
- Config overrides: `--config <path>` or env `ZOTERO_CODEX_CONFIG`; default `~/.zotero-codex/config.json`.
- Scripts use Python standard library only; run with the system `python`.
