import { describe, expect, it } from "vitest";

import { buildMarkdown } from "./buildMarkdown.js";

describe("buildMarkdown", () => {
  it("renders the header, source link and a quoted annotation", () => {
    const md = buildMarkdown({
      pageTitle: "Hello",
      pageUrl: "https://example.com/page",
      annotations: [
        {
          quote: "first line\nsecond line",
          textFragmentUrl: "https://example.com/page#:~:text=first%20line",
        },
      ],
    });
    expect(md).toContain("## Annotations");
    expect(md).toContain("**Source:** [Hello](https://example.com/page)");
    expect(md).toContain("> first line\n> second line");
    expect(md).toContain("[citer](https://example.com/page#:~:text=first%20line)");
  });

  it("separates multiple annotations with a horizontal rule", () => {
    const md = buildMarkdown({
      pageTitle: "T",
      pageUrl: "https://u",
      annotations: [
        { quote: "a", textFragmentUrl: "https://u#:~:text=a" },
        { quote: "b", textFragmentUrl: "https://u#:~:text=b" },
      ],
    });
    expect((md.match(/^---$/gm) || []).length).toBe(1);
    expect(md.indexOf("> a")).toBeLessThan(md.indexOf("> b"));
  });

  it("omits the [citer] line when no text-fragment URL is present", () => {
    const md = buildMarkdown({
      pageTitle: "T",
      pageUrl: "https://u",
      annotations: [{ quote: "a", textFragmentUrl: null }],
    });
    expect(md).toContain("> a");
    expect(md).not.toContain("[citer]");
  });

  it("falls back to the URL when the page title is missing", () => {
    const md = buildMarkdown({
      pageTitle: "",
      pageUrl: "https://example.com/x",
      annotations: [],
    });
    expect(md).toContain("**Source:** [https://example.com/x](https://example.com/x)");
  });

  it("still renders the header when there are no annotations", () => {
    const md = buildMarkdown({
      pageTitle: "T",
      pageUrl: "https://u",
      annotations: [],
    });
    expect(md).toContain("## Annotations");
    expect(md.split("\n").length).toBeGreaterThan(0);
  });

  it("appends a Note paragraph when the annotation carries one (#541)", () => {
    const md = buildMarkdown({
      pageTitle: "T",
      pageUrl: "https://u",
      annotations: [
        { quote: "captured text", note: "the user's annotation" },
      ],
    });
    expect(md).toContain("> captured text");
    expect(md).toContain("**Note :** the user's annotation");
  });
});
