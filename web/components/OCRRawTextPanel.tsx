import type { OCRResult } from "@/lib/types";

export function OCRRawTextPanel({ result }: { result: OCRResult | null }) {
  return (
    <section className="panel-section">
      <div className="section-heading">
        <h2>OCR raw text</h2>
        {result ? <span>{result.parser_version}</span> : null}
      </div>
      {result ? <pre className="ocr-text">{result.raw_text || "No OCR text returned."}</pre> : <p className="muted">No OCR result is stored.</p>}
    </section>
  );
}
