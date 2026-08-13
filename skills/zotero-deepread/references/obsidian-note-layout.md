# Obsidian literature-note layout

Each paper gets two things in `<vault>/Literature/`:

1. Light note `@<citekey>.md` — frontmatter + abstract + annotations + a link to the 精读 bundle. This is the note produced by the Obsidian Zotero Integration plugin's import template.
2. Deepread bundle `<citekey> 精读/` — produced by the chosen reader skill (nature-reader by default):
   - `paper.md` (full bilingual reader)
   - `source_map.json` (stable source anchors)
   - `translation_notes.md` (terminology/uncertainty)
   - `assets/` (figures, tables, equation crops)

The light note embeds the bundle with:

```markdown
![[<citekey> 精读/paper]]
```

Frontmatter keys to keep consistent: `title`, `citekey`, `year`, `doi`, `tags`, `authors`. Keeping `citekey` identical to Better BibTeX's key is what ties the note to `references.bib`.
