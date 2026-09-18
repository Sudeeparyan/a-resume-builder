import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/**
 * The PDF pane.
 *
 * Renders to a canvas rather than an <iframe> so scroll position and zoom
 * survive a recompile. Jumping back to page top on every keystroke is what
 * makes a live-preview editor feel broken.
 */
export default function PdfPane({ b64, zoom }: { b64: string | null; zoom: number }) {
  const host = useRef<HTMLDivElement>(null);
  const scrollTop = useRef(0);
  const [err, setErr] = useState("");
  const [pages, setPages] = useState(0);

  useEffect(() => {
    let cancelled = false;
    if (!b64 || !host.current) return;

    const container = host.current;
    scrollTop.current = container.parentElement?.scrollTop ?? 0;

    (async () => {
      try {
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        const doc = await pdfjs.getDocument({ data: bytes }).promise;
        if (cancelled) return;
        setPages(doc.numPages);
        setErr("");

        container.innerHTML = "";
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          if (cancelled) return;
          const viewport = page.getViewport({ scale: zoom * (window.devicePixelRatio || 1) });
          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.style.width = `${viewport.width / (window.devicePixelRatio || 1)}px`;
          canvas.style.marginBottom = "12px";
          const ctx = canvas.getContext("2d");
          if (!ctx) continue;
          await page.render({ canvasContext: ctx, viewport }).promise;
          if (cancelled) return;
          container.appendChild(canvas);
        }

        // Put the reader back where they were.
        requestAnimationFrame(() => {
          if (container.parentElement) container.parentElement.scrollTop = scrollTop.current;
        });
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || "Could not display the PDF.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [b64, zoom]);

  if (!b64) {
    return (
      <div className="pdfpane">
        <div className="empty" style={{ color: "#d0d0d8" }}>
          The preview appears here once it builds.
        </div>
      </div>
    );
  }

  return (
    <div className="pdfpane">
      {err && <div className="banner bad">{err}</div>}
      <div ref={host} />
      {pages > 1 && (
        <div className="small" style={{ color: "#ffd9a0", marginTop: 8 }}>
          {pages} pages — a resume must be exactly one. Cut content rather than
          shrinking the margins.
        </div>
      )}
    </div>
  );
}
