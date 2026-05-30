// Pure SVG helpers for the paintbrush extension (#541, #549).
//
// Separated from annotate.src.js so vitest can exercise them without a real
// browser runtime — the content script imports them and bundles them via
// esbuild, the test file imports them directly.

export const SVG_NS = "http://www.w3.org/2000/svg";
export const RED = "#cf222e";
export const RECT_STROKE = 5;
export const TEXT_SIZE = 12;

/**
 * Escape ``& < > "`` for inclusion as XML text or attribute value.
 *
 * @param {unknown} s value to escape (coerced via ``String``)
 * @returns {string}
 */
export function escapeXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Serialise the paintbrush attachement SVG (#541, #549).
 *
 * Builds a standalone SVG XML string from the user's shapes + an optional
 * page skeleton, framed on the current viewport. Pure: takes the shapes
 * and the viewport explicitly so it can be unit-tested without the live
 * runtime.
 *
 * @param {object} input
 * @param {Array<{type:string,x:number,y:number,w?:number,h?:number,content?:string}>} input.shapes
 *   - User shapes in page coordinates. ``rect`` carries w/h, ``text``
 *     carries the inline content.
 * @param {number} input.scrollX - ``window.scrollX`` at push time
 * @param {number} input.scrollY - ``window.scrollY`` at push time
 * @param {number} input.innerWidth - ``window.innerWidth``
 * @param {number} input.innerHeight - ``window.innerHeight``
 * @param {string} [input.skeleton] - Pre-rendered page skeleton XML (the
 *   live-DOM walk happens in annotate.src.js and is not pure).
 * @returns {string} A self-contained ``<svg>...</svg>`` string, or ``""``
 *   when there are no shapes (nothing to push).
 */
export function serialiseSvg({
  shapes,
  scrollX,
  scrollY,
  innerWidth,
  innerHeight,
  skeleton = "",
}) {
  if (!Array.isArray(shapes) || shapes.length === 0) return "";
  const annParts = [];
  for (const s of shapes) {
    if (s.type === "rect") {
      annParts.push(
        `<rect x="${s.x}" y="${s.y}" width="${s.w}" height="${s.h}" fill="transparent" stroke="${RED}" stroke-width="${RECT_STROKE}"/>`,
      );
    } else {
      annParts.push(
        `<text x="${s.x}" y="${s.y}" fill="${RED}" font-size="${TEXT_SIZE}" font-family="sans-serif">${escapeXml(s.content)}</text>`,
      );
    }
  }
  const displayW = Math.min(1600, innerWidth);
  return (
    `<svg xmlns="${SVG_NS}" viewBox="${scrollX} ${scrollY} ${innerWidth} ${innerHeight}" width="${displayW}">` +
    `<rect x="${scrollX}" y="${scrollY}" width="${innerWidth}" height="${innerHeight}" fill="#ffffff"/>` +
    (skeleton ? `<g class="kb-skel">${skeleton}</g>` : "") +
    `<g class="kb-annotations">${annParts.join("")}</g>` +
    `</svg>`
  );
}
