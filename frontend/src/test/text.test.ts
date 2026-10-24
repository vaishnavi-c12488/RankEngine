import { htmlToText, shortDescription, toParagraphs } from "../lib/text";

describe("htmlToText", () => {
  it("returns empty string for missing input", () => {
    expect(htmlToText(undefined)).toBe("");
    expect(htmlToText(null)).toBe("");
    expect(htmlToText("")).toBe("");
  });

  it("strips tags and decodes entities", () => {
    expect(htmlToText("<b>Fast</b> &amp; light &quot;pack&quot;")).toBe('Fast & light "pack"');
  });

  it("keeps structure from block tags and list items", () => {
    const out = htmlToText("<p>One</p><p>Two</p><ul><li>A</li><li>B</li></ul>a<br>b");
    expect(out).toContain("One\n\nTwo");
    expect(out).toContain("• A\n• B");
    expect(out).toMatch(/a\nb$/);
  });

  it("drops script and style content and never leaves tags", () => {
    const out = htmlToText('Hi<script>alert(1)</script><style>p{}</style><img src=x onerror="alert(2)">there');
    expect(out).toBe("Hithere");
    expect(out).not.toMatch(/[<>]/);
  });

  it("leaves plain text untouched apart from whitespace", () => {
    expect(htmlToText("  a   b \n\n\n\n c ")).toBe("a b\n\nc");
  });

  it("does not turn escaped markup into executable markup", () => {
    expect(htmlToText("&lt;script&gt;x&lt;/script&gt;")).toBe("<script>x</script>");
  });
});

describe("toParagraphs / shortDescription", () => {
  it("splits on blank lines", () => {
    expect(toParagraphs("a\n\nb\n\n\nc")).toEqual(["a", "b", "c"]);
  });

  it("truncates at a word boundary with an ellipsis", () => {
    const out = shortDescription("word ".repeat(100), 50);
    expect(out.length).toBeLessThanOrEqual(51);
    expect(out.endsWith("…")).toBe(true);
  });

  it("returns short text unchanged and empty for missing", () => {
    expect(shortDescription("<p>Hello</p>")).toBe("Hello");
    expect(shortDescription("")).toBe("");
  });
});
