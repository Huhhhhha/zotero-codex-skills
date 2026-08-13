{# Obsidian Zotero Integration - Import Format 模板 #}
{# 使用前请在插件的 Data Explorer 里核对变量名（DOI、creators 等大小写） #}
{# 笔记文件名建议在插件设置里配成：{{citekey}}（或 @{{citekey}}） #}
---
title: "{{title | escape}}"
citekey: "{{citekey}}"
year: {{date | format("YYYY")}}
doi: "{{DOI}}"
tags: [{% for t in tags %}"{{t.tag}}"{% if not loop.last %}, {% endif %}{% endfor %}]
status: unread
---

# {{title}}

> [!info] 文献信息
> **Authors:** {% for c in creators %}{{c.firstName}} {{c.lastName}}{% if not loop.last %}, {% endif %}{% endfor %}
> **Year:** {{date | format("YYYY")}}
> **DOI:** {{DOI}}
> **Citekey:** `@{{citekey}}`

## 精读全文

![[{{citekey}} 精读/paper]]

## 摘要

{{abstractNote}}

## 标注

{% persist "annotations" %}
{% for a in annotations %}
{% if a.annotatedText %}
> [!quote] {{a.colorCategory}}
> {{a.annotatedText}}
{% if a.comment %}**评论:** {{a.comment}}{% endif %}
{% endif %}
{% endfor %}
{% endpersist %}

## 我的笔记

{% persist "notes" %}
{% if isFirstImport %}
- [ ] 是否已精读？
- [ ] 与我的课题的关联
{% endif %}
{% endpersist %}
