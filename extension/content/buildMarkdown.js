// Pure markdown composer for the annotation push (#520).
//
// Separated from annotate.src.js so it can be vitest-tested without spinning
// up the whole content-script runtime (no chrome.*, no DOM mutation, no
// extension globals — just a function from data to a string).

/**
 * Build the task description markdown from a page's annotations.
 *
 * @param {object} input
 * @param {string} input.pageTitle - The page's <title>, used as link label.
 * @param {string} input.pageUrl - Canonical URL of the page.
 * @param {Array<{quote: string, textFragmentUrl?: string|null, note?: string|null}>} input.annotations
 *   - Each annotation has the verbatim quote text (or, for the paintbrush
 *     epic #541, the text captured under a rectangle), an optional URL with
 *     a text fragment (#:~:text=…) that scrolls to it in a fresh tab, and
 *     an optional ``note`` (the user's free-form annotation alongside the
 *     boxed element).
 * @returns {string} A markdown block: `## Annotations`, the source link,
 *   then one blockquote per annotation followed by an inline "[citer](URL)"
 *   when a text-fragment URL is available and a "**Note:**" paragraph when
 *   the user attached one, separated by `---`.
 */
export function buildMarkdown({ pageTitle, pageUrl, annotations }) {
  const label = (pageTitle || pageUrl || "").trim() || pageUrl || "";
  const lines = ["## Annotations", "", `**Source:** [${label}](${pageUrl})`, ""];
  const items = Array.isArray(annotations) ? annotations : [];
  for (let i = 0; i < items.length; i++) {
    const a = items[i];
    const quote = String(a?.quote ?? "");
    const quoteLines = quote
      .split("\n")
      .map((l) => `> ${l}`)
      .join("\n");
    lines.push(quoteLines);
    if (a?.textFragmentUrl) {
      lines.push("");
      lines.push(`[citer](${a.textFragmentUrl})`);
    }
    if (a?.note) {
      lines.push("");
      lines.push(`**Note :** ${String(a.note)}`);
    }
    if (i < items.length - 1) {
      lines.push("");
      lines.push("---");
      lines.push("");
    }
  }
  return lines.join("\n");
}
