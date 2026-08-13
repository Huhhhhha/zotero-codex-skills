# Venue policy for zotero-find

A candidate passes the quality bar when its venue matches any of the following:

1. Conference whitelist (proceedings): ICRA, IROS, ICCV, CVPR, ECCV, 3DV, RSS, ICLR, ICML, NeurIPS, IJCAI, AAAI.
2. IEEE Transactions series: any venue whose normalized name contains `IEEE Transactions` or `IEEE Trans.`.
3. CCF-B or CCF-A journals (curated, editable list below).

## Curated journal list

- IEEE Transactions on Pattern Analysis and Machine Intelligence (CCF-A)
- International Journal of Computer Vision (CCF-A)
- IEEE Transactions on Robotics (IEEE Trans series)
- IEEE Transactions on Neural Networks and Learning Systems (CCF-B)
- IEEE Transactions on Image Processing (CCF-B)
- IEEE Transactions on Cybernetics (CCF-B)
- IEEE Transactions on Multimedia (CCF-B)
- Pattern Recognition (CCF-B)
- IEEE Robotics and Automation Letters
- Journal of Field Robotics
- Autonomous Robots

## Matching notes

- Normalize venue strings to lowercase and strip punctuation before matching.
- Semantic Scholar exposes `venue`; Crossref exposes `container-title`. Check both.
- arXiv is a preprint server, not a venue; a result whose only venue is "arXiv" does not pass by itself. Prefer the published venue reported by Semantic Scholar/Crossref.
- If the user explicitly asks to relax the bar, honor it for that request only and say so.

