// pdf.js, loaded only when a PDF is opened or thumbnailed (it's large).
type Pdfjs = typeof import("pdfjs-dist");

let lib: Promise<Pdfjs> | null = null;

export function loadPdfjs(): Promise<Pdfjs> {
  lib ??= (async () => {
    // The legacy build includes polyfills for older Safari.
    const pdfjs = (await import("pdfjs-dist/legacy/build/pdf.mjs")) as unknown as Pdfjs;
    // Bundled as a .js worker so every static host serves it with a JavaScript MIME type.
    const { default: PdfWorker } = await import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?worker");
    pdfjs.GlobalWorkerOptions.workerPort = new PdfWorker();
    return pdfjs;
  })();
  lib.catch(() => (lib = null));
  return lib;
}

export async function openPdf(data: Uint8Array) {
  const pdfjs = await loadPdfjs();
  // No eval: the site's CSP doesn't allow it.
  return pdfjs.getDocument({ data, isEvalSupported: false }).promise;
}
