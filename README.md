# Zotero + Codex + Obsidian 科研闭环 Skills

两个 Codex skill，把 Zotero（Better BibTeX）、Obsidian、Codex 串成一个科研阅读闭环。

## Skills

- `zotero-find` — 按阅读方向检索高质量论文并写入 Zotero `From_codex` 集合。触发词：「我需要一篇论文」。
- `zotero-deepread` — 精读 Zotero 库中的某篇论文，产出全文精读附件进 Obsidian。触发词：「精读我Zotero库中的某篇论文」。

检索只收 CCF-B 及以上期刊、IEEE Transactions 系列、或 ICRA / IROS / ICCV / CVPR / ECCV / 3DV / RSS / ICLR / ICML / NeurIPS / IJCAI / AAAI。

## 依赖

- Zotero 7/9，并在「设置 → 高级」里开启「允许其他应用与本机 Zotero 通信」（默认端口 23119）
- Zotero 的 Better BibTeX 插件
- Obsidian + Zotero Integration 插件（可选，用于文献笔记导入）
- Python 3（脚本只使用标准库）

## 安装

1. 把 `skills/zotero-find` 和 `skills/zotero-deepread` 复制到 `~/.codex/skills/`。
2. 复制配置模板并填好本机路径：
   - Windows：把 `config.example.json` 复制为 `%USERPROFILE%\.zotero-codex\config.json`
   - Linux/macOS：`cp config.example.json ~/.zotero-codex/config.json`
3. 编辑 `config.json`：填 Zotero 数据目录、Obsidian vault 路径、目标集合名和 venue 白名单。
4. 在 Zotero 里新建一个名为 `From_codex`（或你自定义的名字）的集合。

## 使用

新开一个 Codex 对话，直接说：

- 「我需要一篇论文」
- 「精读我Zotero库中的某篇论文」

## 注意

- Zotero 9 的本地 `/api/` 是只读；写入走 `/connector/`。
- `zotero-find` 默认先 `--dry-run` 预览，确认后再真正写入。
- `zotero-deepread` 默认用 nature-reader 精读；也可在提示词里点名其它技能或组合多个。

