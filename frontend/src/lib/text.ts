/**
 * Convert catalog HTML into safe plain text.
 *
 * The result is only ever rendered as React text nodes, never as HTML, so no
 * markup from the catalog can execute. DOMParser builds an inert document
 * (scripts are not run), and script/style contents are dropped.
 */
export function htmlToText(input: string | null | undefined): string {
  if (!input) return "";
  let value = String(input);

  if (/[<&]/.test(value)) {
    value = value
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(p|div|h[1-6]|table)>/gi, "\n\n")
      .replace(/<\/(li|ul|ol|tr)>/gi, "\n")
      .replace(/<li[^>]*>/gi, "• ");
    const doc = new DOMParser().parseFromString(value, "text/html");
    doc.querySelectorAll("script,style,noscript,template").forEach((n) => n.remove());
    value = doc.body.textContent ?? "";
  }

  return value
    .replace(/\u00a0/g, " ")
    .replace(/[ \t\f\v]+/g, " ")
    .replace(/ *\n */g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Split cleaned text into paragraphs for readable rendering. */
export function toParagraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/** Single-line preview for result cards, cut at a word boundary. */
export function shortDescription(input: string | null | undefined, max = 180): string {
  const text = htmlToText(input).replace(/\s*\n\s*/g, " ").trim();
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  return (lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd() + "…";
}
