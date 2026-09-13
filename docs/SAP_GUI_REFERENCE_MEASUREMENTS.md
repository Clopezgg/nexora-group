# Direct JPL measurement — 2026-09-12

Source: `~/Downloads/sap-widgets.jpl`; `info.xml` name SAP, description explicitly Signature and Tradeshow. `widgets.xml` version `8.5.0.20180828`. 26 widgets: Signature 17, Tradeshow 9. No Horizon family. XML and all 26 preview images inspected, the latter in `sap-jpl-reference/reference-contact-sheet.png` opened via view_image. Extraction/reference material stays ignored in .artifacts; no asset enters product.

Local, uncommitted evidence: raw per-element geometry, color, border, position, font and padding: `sap-jpl-reference/raw-measurements.txt`. XML font `size` is the authoring-system value, not proven CSS px; `height` records text line geometry. Unknown values below are not fabricated.

| Variant/component | Reference height | Padding X/Y | Border/radius | Font size / weight | Background / text | Selected bg/text | Focus / divider |
|---|---:|---|---|---|---|---|---|
| Signature Main Screen | 795 outer, 780 inner | authored nested coordinates | square outer / decorative chrome | labels 8–14 /400–700 Arial | #fefeff /#21386b | n/a | divider #c3ccd7 1px |
| Signature Screen | 803 outer, 632 work area | work left 17, top 105 | 1px | title 14 /700 italic | work #eaf1f6 | n/a | divider #c3ccd7 |
| Signature title strip | 30 | 32/2 text coordinate | 0 | 14 /700 | #d8e3ed→#adc5db /black | n/a | none |
| Signature Menu / top chrome | 17 text strip | labels at x17,64,130,209 | thin separator | 8 /400 | transparent /#21386b | n/a | #c3ccd7 |
| Signature Command Bar | 29 | nested positions | divider 1px | 8–9 /400 | #f4f6fa→white | n/a | #c3ccd7 |
| Signature Toolbar | 18 outer auxiliary, 28 in screen title group | 0 declared | thin separator | 8–9 /400 | #cfdde8 | n/a | #c3ccd7 |
| Signature Easy Access left bar | 720, width 211 | item text x22 y4 | 1px | 9 /400 | blue workstation | n/a | #182a53 |
| Signature Tree Item | 27, width 204 | 22/4 actual text origin | 1px #466dbd, radius0 | 9 /400 | #466dbd /white | #4d8adb /white | dividers #182a53 |
| Signature Tab | 21, width130 | left shoulder20, label origin0 inside | 1px #668db5, diagonal shoulder21×21 | 9 /400 | #c2d8eb, outer #dee9f3 /#64707c | #8cb1da, outer #bdd4e9 /black | unavailable |
| Signature Titled Box | 181 overall,25 header | title7/3, header inset1/2 |1px #668db5 |9 /400 |header #c0d6ea, body #dfebf5 /black |n/a |none |
| Signature Field |18, width164; inner159×14 |actual inner3/2, declared0 |1px #a8a8a9; XML radius30 authoring units |9 /400 Arial, line12 |outer #cad1d6→#dfebf5, innerwhite /black |n/a |Blue field inner #dfebf5; NOT an explicit focus event |
| Signature Focused Field | unavailable explicit focus state | n/a | n/a | n/a | Blue field is separate supplied widget | n/a | not proven focus semantics |
| Signature Select | no separate widget | n/a | n/a | n/a | n/a | n/a | n/a |
| Signature Button |18, width62 |0/0 declared |1px #636467; XML radius25 authoring units |9 /400 |#fefcef→#feee9e /black |unavailable |unavailable |
| Signature Grid/header/row | no grid widget | n/a | n/a | n/a | n/a | n/a | n/a |
| Signature Dialog | no standalone widget | n/a | n/a | n/a | derive window grammar only | n/a | n/a |
| Signature Status Bar |25 outer, images21–23 |status at bottom y744–770 nested |thin dividers |n/a |screen chrome | n/a | n/a |
| Tradeshow Screen |690, width1031 |content x6 y129 |layered separator 3×1px |10 /400 body; title16 /700 |bands #d9e5f3/#cbd5e1/white |n/a |#404040/#a6a6a6/#d9d9d9 |
| Tradeshow Title/Menu block |37 |text y14 |left 6px #004461 stroke |10 /400, line16 |#d9e5f3 /#172e50 |n/a |none |
| Tradeshow Command Bar |30, y36 |field x46 y6 |3px separator below |8 /400 |#cbd5e1 /black |n/a |#404040/#a6a6a6/#d9d9d9 |
| Tradeshow Toolbar |29 at y68; title strip32 y98 |0 declared |square |10 /400 |white, then #cbd5e1 |n/a |thin |
| Tradeshow Tree |300, width200 |first node x5/y5 relative |1px #92aab7 |10 /400 Arial |#aeceda /black |unavailable |none |
| Tradeshow Tree Item |16 |13px incremental indentation |none |10 /400, line16 |transparent /black |unavailable |none |
| Tradeshow Selected Tree Item |not authored |n/a |n/a |n/a |n/a |n/a |n/a |
| Tradeshow Tabs |22 |22px diagonal shoulder, label59 wide |panel top2px #265b8f, other1px |9 /400 line15 |inactive #87abd6 /black |#265b8f /white |panel #cbd4e1 |
| Tradeshow Titled Box |82 overall,20 header |title0 declared; diagonal shoulder20 |1px #8e9eab, radius0 |10 /400 line13 |header #abced9, body #cbd4e1 /black |n/a |none |
| Tradeshow Field |18, width118 |0/0 |1px #939aa2,radius0 |9 /400 line12 |white /black |unavailable |unavailable |
| Tradeshow Focused Field |no explicit widget/state |n/a |n/a |n/a |n/a |n/a |n/a |
| Tradeshow Select |22 overall; input18 |input y2 |1px #939aa2,radius0 |9 /400 line15 |white /black |unavailable |10×22 arrow image |
| Tradeshow Button |23, width83 |0/0 declared |1px top/left,2px bottom/right #666,radius0 |10 /400 line16 |#f2e1af /black |unavailable |unavailable |
| Tradeshow Grid/header/row |no grid widget |n/a |n/a |n/a |n/a |n/a |n/a |
| Tradeshow Dialog |307,width488;title19 |content inset8, content y46 |1px #333348,radius0; content top2px #265b8f |10 /400 |body #cbd4e1,titlewhite /black |tab #265b8f /white |footer top1px #6289ae |
| Tradeshow Status Bar |dialog footer21; screen unspecified |footer x8,y279 |1px top #6289ae |10 /400 |transparent /black |n/a |#6289ae |

## Reconciliation with docs/SAP_GUI_JPL_MAPPING.md

Correct: package identity, 2 groups/26 widgets, core listed blue/gray palette exists, no proprietary assets in product, Horizon is not in JPL.

Overstatements that must not be inherited as proof:

- 28–30px fields are Nexora accessibility/usability adaptation, **not** JPL measurements (both families are18px). Current user explicitly requests28–30px desktop, so retain user target and disclose adaptation.
- JPL Signature button is yellow gradient and Tradeshow button solid yellow/beveled, while user requests Signature beveled and Tradeshow gradient. Implement user anatomy contract and distinguish it from strict pixel equality.
- Blue field is a separate JPL widget; XML does not establish browser :focus behavior. WCAG focus treatment is deliberate Nexora extension.
- Signature tabs have diagonal left shoulders; matching radius alone misses the most visible anatomy. Tradeshow selected tab dark #265b8f white differs clearly from Signature light #8cb1da black.
- Signature Titled Box is a25px blue band, not a legend interrupting an unbanded border. Tradeshow Box title has20px band plus diagonal trailing shoulder.
- Grid/Grid Header/Grid Row are **absent**. No claim of measured grid pixel accuracy can be made from this file. ThemeAnatomy/ERP requirements govern adaptation.
- Signature standalone Dialog/Select and explicit focus/disabled/hover states do not exist. Do not invent source measurements.
- XML radius values25/30/33/34 conflict with tiny component previews if read as CSS px. They are authoring-specific parameters; actual preview looks minimally rounded, so do not use radius:30px in CSS.

CSS priorities from direct evidence: diagonal folder shoulders; light selected Signature versus dark selected Tradeshow; real steel-blue title stripes; sharp square fields; different panel fills #dfebf5 versus #cbd4e1; distinct Tradeshow multi-line toolbar separators; compact tree hierarchy. No exact runtime or proprietary pixel identity is certified by this report.


## Evidence interpretation

The preview bitmap is40px wide for most widgets; it is not a full-resolution screenshot. Enlarged nearest-neighbor contact sheets (`SAP-Signature-enlarged.png`, `SAP-Tradeshow-enlarged.png`) were opened to inspect anatomy, while geometry comes from XML. Native bitmap strips were opened in `native-chrome-strips-2x.png`:629×23 is the command/toolbar (OK + field + tools),419×23 is toolbar icons,222×23 is the real status strip (system/session, user, INS). Chrome gradient strips are282×18. These directly support23px tool/status assets and17–18px top-strip geometry. The primary title stripe30px is an internal screen title, distinct from the operating-window top stripe. There is no single standalone Menu Bar, Command Bar or Toolbar widget; their role mapping is inferred from position and contents inside Screen/Main Screen and therefore is not an exact named-component assertion. No browser state or production fidelity PASS is implied by source measurement.
