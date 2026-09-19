# Optional feature status

| No. | Feature | Status | Safe scope | Unlock condition |
|---:|---|---|---|---|
| 21 | Table calculations | beta | Safe aggregate/arithmetic grammar over rectangular cells with dependency and cycle checks | renderer-backed recalculation fixtures and broader spreadsheet semantics |
| 26 | Charts | locked | detection and explicit failure only | chart parts, relationships, rendering, and round-trip fixtures |
| 29 | Notes | experimental | footnotes and endnotes with stable numbering | multi-section continuation fixtures |
| 30 | Captions | experimental | table caption sublists | automatic figure/equation numbering fixtures |
| 31 | Bookmarks and hyperlinks | beta | internal and allowed external links with target validation | renderer-backed navigation fixtures |
| 32 | Cross-references | beta | target validation and stable static target IDs | number/text/page reference fields |
| 33 | TOC and index | beta | linked TOC without page numbers; sorted static index | renderer-backed pagination module |
| 35 | Track changes and compare | locked | detection and explicit failure only | accept/reject semantic model and round-trip fixtures |
| 40 | Password, distribution, signature | locked | detection and explicit failure only | audited cryptographic adapter and test vectors |

Never downgrade a locked request to plain text or a visual imitation.
