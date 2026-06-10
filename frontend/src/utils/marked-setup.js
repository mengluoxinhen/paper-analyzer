import { marked } from "marked";

function renderKatex(formula, display) {
  if (typeof window !== "undefined" && window.katex) {
    try {
      return window.katex.renderToString(formula, {
        displayMode: display,
        throwOnError: false,
      });
    } catch {
      // fall through to fallback
    }
  }
  // Fallback: display raw LaTeX in styled containers
  const tag = display ? "div" : "span";
  const cls = display ? "math-block" : "math-inline";
  return `<${tag} class="${cls}">${formula}</${tag}>`;
}

function renderMarkdown(text) {
  if (!text) return "";

  const mathBlocks = [];

  // Step 1: protect display math $$...$$
  let protectedText = text.replace(/\$\$([\s\S]*?)\$\$/g, (_match, formula) => {
    mathBlocks.push({ formula: formula.trim(), display: true });
    return `%%MATH_${mathBlocks.length - 1}%%`;
  });

  // Step 2: protect inline math $...$ (single $, not $$)
  protectedText = protectedText.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, (_match, formula) => {
    mathBlocks.push({ formula: formula.trim(), display: false });
    return `%%MATH_${mathBlocks.length - 1}%%`;
  });

  // Step 3: render with marked
  let html = marked.parse(protectedText);

  // Step 4: replace placeholders with KaTeX-rendered HTML
  html = html.replace(/%%MATH_(\d+)%%/g, (_match, idx) => {
    const { formula, display } = mathBlocks[parseInt(idx)];
    return renderKatex(formula, display);
  });

  return html;
}

export { renderMarkdown };