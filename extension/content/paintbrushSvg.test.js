import { describe, expect, it } from "vitest";

import { escapeXml, RED, serialiseSvg } from "./paintbrushSvg.js";

describe("escapeXml", () => {
  it("escapes the four characters that break XML / SVG attributes", () => {
    expect(escapeXml('Tom & Jerry <hi> "quoted"')).toBe(
      "Tom &amp; Jerry &lt;hi&gt; &quot;quoted&quot;",
    );
  });

  it("coerces non-strings", () => {
    expect(escapeXml(42)).toBe("42");
    expect(escapeXml(null)).toBe("null");
  });
});

describe("serialiseSvg", () => {
  const VIEW = { scrollX: 100, scrollY: 50, innerWidth: 800, innerHeight: 600 };

  it("returns empty string when no shapes", () => {
    expect(serialiseSvg({ shapes: [], ...VIEW })).toBe("");
  });

  it("emits a self-contained SVG with viewBox framed on the viewport", () => {
    const out = serialiseSvg({
      shapes: [{ type: "rect", x: 120, y: 200, w: 100, h: 40 }],
      ...VIEW,
    });
    expect(out.startsWith("<svg ")).toBe(true);
    expect(out.endsWith("</svg>")).toBe(true);
    expect(out).toContain('xmlns="http://www.w3.org/2000/svg"');
    // viewBox uses scrollX/scrollY + viewport dims.
    expect(out).toContain('viewBox="100 50 800 600"');
    // Background rect tracks the viewport too.
    expect(out).toContain('width="800" height="600" fill="#ffffff"');
  });

  it("renders user rectangles in red 5px stroke, transparent fill", () => {
    const out = serialiseSvg({
      shapes: [{ type: "rect", x: 10, y: 20, w: 30, h: 40 }],
      ...VIEW,
    });
    expect(out).toContain(
      `<rect x="10" y="20" width="30" height="40" fill="transparent" stroke="${RED}" stroke-width="5"/>`,
    );
  });

  it("renders text annotations and escapes their content", () => {
    const out = serialiseSvg({
      shapes: [{ type: "text", x: 5, y: 6, content: 'bug <x> & "y"' }],
      ...VIEW,
    });
    expect(out).toContain(
      `<text x="5" y="6" fill="${RED}" font-size="12" font-family="sans-serif">bug &lt;x&gt; &amp; &quot;y&quot;</text>`,
    );
  });

  it("includes the skeleton group when one is supplied", () => {
    const skel = '<rect x="0" y="0" width="10" height="10" fill="#eee"/>';
    const out = serialiseSvg({
      shapes: [{ type: "rect", x: 0, y: 0, w: 1, h: 1 }],
      skeleton: skel,
      ...VIEW,
    });
    expect(out).toContain('<g class="kb-skel">' + skel + "</g>");
    // Annotations are always rendered in their own group too, layered above.
    expect(out).toContain('<g class="kb-annotations">');
  });

  it("caps the display width at 1600 for very wide viewports", () => {
    const out = serialiseSvg({
      shapes: [{ type: "rect", x: 0, y: 0, w: 1, h: 1 }],
      scrollX: 0,
      scrollY: 0,
      innerWidth: 4000,
      innerHeight: 800,
    });
    expect(out).toContain('width="1600"');
  });
});
