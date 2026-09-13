from pathlib import Path
p=Path('frontend/src/theme/themes.css')
s=p.read_text()
s=s.replace("  --sap-field-height: 26px;\n  --sap-button-height: 26px;", "  --sap-field-height: 28px;\n  --sap-button-height: 28px;")
s=s.replace(""":root[data-nx-family='sap-gui'][data-nx-panel='titled-box'] body .nx-card__title {
  display: table;
  min-height: 0;
  margin: -17px 0 6px;
  padding: 0 5px;
  background: var(--nx-color-surface);
  border: 0;
}
:root[data-nx-family='sap-gui'][data-nx-panel='titled-box'] body .nx-card { margin-top: 14px; }""", """/* JPL Signature Titled Box: 25px header band, #c0d6ea over #dfebf5. */
:root[data-nx-family='sap-gui'][data-nx-panel='titled-box'] body .nx-card__title {
  min-height: 25px;
  background: #c0d6ea;
  border-bottom-color: #668db5;
}
:root[data-nx-family='sap-gui'][data-nx-panel='titled-box'] body .nx-card {
  background: #dfebf5;
  border-color: #668db5;
}""")
s=s.replace("  border-radius: 5px 5px 0 0;\n  margin-top: 3px;", "  border-radius: 0;\n  margin-top: 3px;")
s=s.replace("  border-top: 3px solid #21386b;\n  border-bottom-color: var(--nx-color-surface);\n  background: var(--nx-color-surface);\n  box-shadow: 2px -1px 0 #8e9eab;", "  border-top: 3px solid #21386b;\n  border-bottom-color: #265b8f;\n  background: #265b8f;\n  color: #fff;\n  box-shadow: inset 0 1px #87abd6;")
# Add specific anatomy adjacent to existing tabs, not per route.
anchor="/* Dialog window / drawer / popover */"
s=s.replace(anchor,"""/* JPL folder shoulders are diagonal, not rounded rectangles. The outer
   tab retains its rectangular focus outline; only its surface is clipped. */
:root[data-nx-tabs='folder'] body .nx-tabs__tab,
:root[data-nx-tabs='raised-folder'] body .nx-tabs__tab {
  position: relative;
  isolation: isolate;
  padding-left: 24px;
  border-radius: 0;
  clip-path: polygon(18px 0, 100% 0, 100% 100%, 0 100%, 0 18px);
}
:root[data-nx-tabs='folder'] body .nx-tabs__tab::before,
:root[data-nx-tabs='raised-folder'] body .nx-tabs__tab::before {
  content: '';
  position: absolute;
  width: 26px;
  height: 1px;
  top: 8px;
  left: -5px;
  transform: rotate(-45deg);
  background: var(--nx-color-border-strong);
}
:root[data-nx-tabs='folder'] body .nx-tabs__tab {
  background: linear-gradient(#dee9f3, #c2d8eb);
}
:root[data-nx-tabs='folder'] body .nx-tabs__tab--active {
  background: linear-gradient(#8cb1da, #bdd4e9);
  color: #172e50;
  border-bottom-color: #bdd4e9;
}
:root[data-nx-tabs='folder'] body .nx-tabs__panel {
  border-top: 2px solid #bdd4e9;
}
:root[data-nx-tabs='raised-folder'] body .nx-tabs__panel {
  border-top: 2px solid #265b8f;
}
:root[data-nx-family='sap-gui'] body .nx-tabs__tab:focus-visible {
  outline-offset: -3px;
}
:root[data-nx-family='sap-gui'] body .nx-tabs__tab:disabled {
  opacity: .55;
  cursor: default;
}

"""+anchor)
# JPL measured button palette with bevel/gradient preservation.
anchor='/* Grid tables */'
s=s.replace(anchor,"""/* Native JPL warm command buttons; dimensions intentionally enlarged to
   28px for the accepted desktop target (JPL: Signature 18 / Tradeshow 23). */
:root[data-nx-button='beveled'] body .nx-button:not(.nx-button--danger) {
  color: #172e50;
  background: linear-gradient(#fefcef, #feee9e);
  border-color: #8e9eab;
  box-shadow: inset 1px 1px #fff, inset -1px -1px #b8ac75;
}
:root[data-nx-button='gradient'] body .nx-button:not(.nx-button--danger) {
  color: #172e50;
  background: linear-gradient(#fff6d9, #f2e1af);
  border-color: #64707c;
  border-width: 1px 2px 2px 1px;
  box-shadow: inset 1px 1px #fff;
}
:root[data-nx-button='beveled'] body .nx-button:hover:not(:disabled),
:root[data-nx-button='gradient'] body .nx-button:hover:not(:disabled) {
  background: linear-gradient(#fffcef, #ffe58a);
  border-color: #265b8f;
}
:root[data-nx-family='sap-gui'] body .nx-table tr[aria-selected='true'] td {
  background: var(--nx-shell-sidebar-active-bg);
  color: var(--nx-shell-sidebar-active-text);
}

"""+anchor)
p.write_text(s)
