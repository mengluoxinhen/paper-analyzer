import MarkdownIt from "markdown-it";
import katex from "katex";

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
});

export function renderMarkdown(text) {
  if (!text || typeof text !== "string") return "";

  // Protect math blocks
  var mathBlocks = [];
  var safe = text;
  safe = safe.replace(/\$\$([\s\S]*?)\$\$/g, function (_, f) {
    mathBlocks.push({ formula: f.trim(), display: true });
    return "\uFFF0M" + (mathBlocks.length - 1) + "M\uFFF0";
  });
  safe = safe.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, function (_, f) {
    mathBlocks.push({ formula: f.trim(), display: false });
    return "\uFFF0M" + (mathBlocks.length - 1) + "M\uFFF0";
  });

  // Render
  var html;
  try { html = md.render(safe); }
  catch (e) { return safe; }

  // Restore math with KaTeX
  html = html.replace(/\uFFF0M(\d+)M\uFFF0/g, function (_, idx) {
    var m = mathBlocks[parseInt(idx)];
    if (!m) return "";
    try { return katex.renderToString(m.formula, { displayMode: m.display, throwOnError: false }); }
    catch (e) { return m.display ? "$$" + m.formula + "$$" : "$" + m.formula + "$"; }
  });

  return html;
}