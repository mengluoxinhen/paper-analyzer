import MarkdownIt from "markdown-it";

const md = new MarkdownIt({
  html: false,
  breaks: false,
  linkify: true,
});

// Patterns that commonly start a new sentence in Chinese academic writing
const SENTENCE_START = ["根据", "该", "这", "此", "然而", "其", "但", "由", "对", "在", "从", "与", "和", "及", "以"];

function fixMergedHeading(text) {
  return text.replace(/^#{1,3} .+$/gm, function (line) {
    if (line.length < 50) return line;

    var bestIdx = -1;
    for (var i = 0; i < SENTENCE_START.length; i++) {
      var idx = line.indexOf(SENTENCE_START[i], 4);
      if (idx > 4 && (bestIdx === -1 || idx < bestIdx)) {
        bestIdx = idx;
      }
    }

    if (bestIdx > 0) {
      return line.substring(0, bestIdx).trim() + "\n\n" + line.substring(bestIdx).trim();
    }
    return line;
  });
}

export function renderMarkdown(text) {
  if (!text || typeof text !== "string") return "";

  try {
    // Fix 1: Split merged heading+body on same line
    var fixed = fixMergedHeading(text);

    // Fix 2: Insert newline before inline headings (e.g. "text### Title")
    fixed = fixed.replace(/([^\n#])(#{1,3}) (?!\d)/g, function (_m, c, h) {
      return c + "\n" + h + " ";
    });

    // Protect math blocks
    var mathBlocks = [];
    var safe = fixed;

    safe = safe.replace(/\$\$([\s\S]*?)\$\$/g, function (_, f) {
      mathBlocks.push({ formula: f.trim(), display: true });
      return "\x00M" + (mathBlocks.length - 1) + "\x00";
    });

    safe = safe.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, function (_, f) {
      mathBlocks.push({ formula: f.trim(), display: false });
      return "\x00M" + (mathBlocks.length - 1) + "\x00";
    });

    var html = md.render(safe);

    // Restore math
    html = html.replace(/\x00M(\d+)\x00/g, function (_, idx) {
      var m = mathBlocks[parseInt(idx)];
      return m ? (m.display ? "$$" + m.formula + "$$" : "$" + m.formula + "$") : "";
    });

    // Demote long headings (>60 chars) to bold paragraphs
    html = html.replace(/<h([1-3])>((?:(?!<\/h\1>)[\s\S]){60,})<\/h\1>/gi, function (_m, level, text) {
      return "<p><strong>" + text + "</strong></p>";
    });

    return html;
  } catch (e) {
    console.error("[renderMarkdown] error:", e);
    return text;
  }
}
