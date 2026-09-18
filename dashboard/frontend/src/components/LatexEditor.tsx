import { useEffect, useRef } from "react";
import { EditorState, StateEffect } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { StreamLanguage, syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";
import { stex } from "@codemirror/legacy-modes/mode/stex";
import { linter, lintGutter, type Diagnostic } from "@codemirror/lint";

export interface EditorProblem {
  severity: string;
  line: number | null;
  message: string;
}

/**
 * The LaTeX source pane.
 *
 * Uses the stex stream mode rather than a Lezer LaTeX grammar: it ships with
 * CodeMirror, needs no extra package, and highlights this document class
 * correctly. Diagnostics come from the real Tectonic log, so an error here is
 * an error the compiler actually reported.
 */
export default function LatexEditor({
  value,
  problems,
  onChange,
  onSave,
  jumpToLine,
}: {
  value: string;
  problems: EditorProblem[];
  onChange: (v: string) => void;
  onSave: () => void;
  jumpToLine?: number | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const problemsRef = useRef<EditorProblem[]>(problems);
  const onChangeRef = useRef(onChange);
  const onSaveRef = useRef(onSave);

  problemsRef.current = problems;
  onChangeRef.current = onChange;
  onSaveRef.current = onSave;

  useEffect(() => {
    if (!host.current) return;

    const lintSource = linter((v) => {
      const out: Diagnostic[] = [];
      for (const p of problemsRef.current) {
        if (!p.line || p.line < 1 || p.line > v.state.doc.lines) continue;
        const line = v.state.doc.line(p.line);
        out.push({
          from: line.from,
          to: line.to,
          severity: p.severity === "error" ? "error" : "warning",
          message: p.message,
        });
      }
      return out;
    });

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        lintGutter(),
        history(),
        highlightActiveLine(),
        highlightSelectionMatches(),
        StreamLanguage.define(stex),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        lintSource,
        keymap.of([
          {
            key: "Mod-s",
            preventDefault: true,
            run: () => {
              onSaveRef.current();
              return true;
            },
          },
          indentWithTab,
          ...defaultKeymap,
          ...historyKeymap,
          ...searchKeymap,
        ]),
        EditorView.lineWrapping,
        EditorView.updateListener.of((u) => {
          if (u.docChanged) onChangeRef.current(u.state.doc.toString());
        }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "12.5px" },
          ".cm-scroller": { overflow: "auto" },
          ".cm-content": { paddingBottom: "40vh" },
        }),
      ],
    });

    const v = new EditorView({ state, parent: host.current });
    view.current = v;
    return () => {
      v.destroy();
      view.current = null;
    };
  }, []);

  // Replace the document only when it genuinely differs, so typing is not
  // interrupted by an echo of the value we just sent up.
  useEffect(() => {
    const v = view.current;
    if (!v) return;
    if (v.state.doc.toString() !== value) {
      v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: value } });
    }
  }, [value]);

  useEffect(() => {
    const v = view.current;
    if (v) v.dispatch({ effects: StateEffect.appendConfig.of([]) });
  }, [problems]);

  useEffect(() => {
    const v = view.current;
    if (!v || !jumpToLine || jumpToLine < 1 || jumpToLine > v.state.doc.lines) return;
    const line = v.state.doc.line(jumpToLine);
    v.dispatch({
      selection: { anchor: line.from, head: line.to },
      effects: EditorView.scrollIntoView(line.from, { y: "center" }),
    });
    v.focus();
  }, [jumpToLine]);

  return <div className="cm-wrap" ref={host} />;
}
