// Builds docs/demo/VeriSource-demo.pptx (product-first demo deck).
// Run from a folder where pptxgenjs, react, react-dom, react-icons and sharp are installed:
//   node build_deck.mjs <path-to-pptx-skill-scripts>   (apply_theme.js lives there)
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fi = require("react-icons/fi");

const here = path.dirname(fileURLToPath(import.meta.url));
const img = (n) => path.join(here, "img", n);
const skillScripts = process.argv[2];
const { applyTheme } = require(path.join(skillScripts, "apply_theme.js"));
const OUT = path.join(here, "VeriSource-demo.pptx");

const THEME = {
  name: "VeriSource",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "12201F", lt1: "FFFFFF", dk2: "0B3D3A", lt2: "EEF4F3",
    accent1: "0F766E", accent2: "B45309", accent3: "15803D",
    accent4: "B91C1C", accent5: "5B6B6A", accent6: "99D5CE",
    hlink: "0F766E", folHlink: "5B6B6A",
  },
};
// Hex twins of the theme colours, only for icon images (which cannot use scheme colours).
const HEX = { teal: "0F766E", white: "FFFFFF", amber: "B45309", green: "15803D", red: "B91C1C", light: "99D5CE" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "VeriSource demo";
pres.subject = "Supplier verification agent";
const C = pres.SchemeColor;
const W = 13.33;
const M = 0.7;

async function icon(name, hex) {
  const Icon = fi[name];
  if (!Icon) throw new Error("missing icon " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color: "#" + hex, size: 256 }));
  const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
const shadow = () => ({ type: "outer", color: "000000", opacity: 0.18, blur: 10, offset: 3, angle: 90 });

// ---- layouts ----
pres.defineSlideMaster({
  title: "DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: 9.6, h: 1.9, fontSize: 54, bold: true, color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.1, w: 9.0, h: 1.3, fontSize: 22, color: C.accent6, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.45, w: 11.9, h: 0.9, fontSize: 34, bold: true, color: C.text2, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: "VeriSource", options: { x: M, y: 7.0, w: 3, h: 0.3, fontSize: 11, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 11, color: C.accent5, align: "right" },
});

// ---- small helpers ----
function T(slide, text, o) {
  slide.addText(text, { isTextBox: true, margin: 0, valign: "top", color: C.text1, ...o });
}
function card(slide, x, y, w, h, o = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: "none" }, ...o,
  });
}
async function iconDot(slide, name, x, y, d, circleColor, iconHex, name2) {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: circleColor }, line: { type: "none" }, objectName: "dot-" + (name2 || name) });
  const p = d * 0.22;
  slide.addImage({ data: await icon(name, iconHex), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: name2 || name });
}
function framed(slide, file, x, y, w, h) {
  slide.addShape(pres.ShapeType.rect, { x: x - 0.04, y: y - 0.04, w: w + 0.08, h: h + 0.08, fill: { color: C.background1 }, line: { color: C.accent6, width: 1 }, shadow: shadow() });
  slide.addImage({ path: img(file), x, y, w, h, altText: "VeriSource screenshot" });
}
function content(section, title) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

// ===== Slide 1: title =====
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Introduction" });
  s.addImage({ data: await icon("FiShield", HEX.light), x: M, y: 0.9, w: 0.7, h: 0.7, altText: "shield" });
  T(s, "A VERIFICATION AGENT FOR BUYERS", { x: M + 0.95, y: 1.05, w: 8, h: 0.4, fontSize: 16, bold: true, color: C.accent6, charSpacing: 3 });
  s.addText("VeriSource", { placeholder: "title" });
  s.addText("Check what suppliers claim against official sources, and see exactly how each answer was reached.", { placeholder: "body" });
  T(s, "Product demo  |  India", { x: M, y: 6.6, w: 6, h: 0.4, fontSize: 16, color: C.accent6 });
  s.addNotes("Open with the one-line idea: a buyer already knows some suppliers and needs to check what those suppliers claim. VeriSource does the checking and shows its work.");
}

// ===== Slide 2: the problem =====
{
  const s = content("Introduction", "Supplier claims are hard to verify by hand");
  const rows = [
    ["FiSearch", "Evidence is scattered", "Official lists, issuer records and supplier websites, each checked one supplier at a time."],
    ["FiAlertCircle", "Claims are self-reported", "A supplier's website says what the supplier wants to say."],
    ["FiMessageSquare", "A chatbot can sound sure while guessing", "The buyer cannot tell which answers come from evidence."],
  ];
  let y = 1.75;
  for (const [ic, head, desc] of rows) {
    await iconDot(s, ic, M, y, 0.85, C.accent1, HEX.white);
    T(s, head, { x: M + 1.15, y: y - 0.02, w: 5.6, h: 0.45, fontSize: 22, bold: true, color: C.text2 });
    T(s, desc, { x: M + 1.15, y: y + 0.45, w: 5.6, h: 0.9, fontSize: 16, color: C.accent5 });
    y += 1.7;
  }
  s.addShape(pres.ShapeType.roundRect, { x: 8.1, y: 1.75, w: 4.55, h: 4.9, rectRadius: 0.12, fill: { color: C.text2 }, line: { type: "none" } });
  T(s, "SEEN IN OUR OWN TESTING", { x: 8.5, y: 2.1, w: 3.8, h: 0.35, fontSize: 13, bold: true, color: C.accent6, charSpacing: 2 });
  T(s, "“4 out of 12 checks”", { x: 8.5, y: 2.65, w: 3.8, h: 1.3, fontSize: 32, bold: true, color: C.background1, fontFace: "Cambria" });
  T(s, "A small language model once said this. The number was invented.", { x: 8.5, y: 4.1, w: 3.8, h: 1.0, fontSize: 18, color: C.background1 });
  T(s, "So in VeriSource the app writes every result, not the model.", { x: 8.5, y: 5.3, w: 3.8, h: 1.0, fontSize: 18, bold: true, color: C.accent6 });
  s.addNotes("The problem is not only the effort of checking. It is trust. We saw a small model invent a count that did not exist, and that shaped the design: the model never states facts.");
}

// ===== Slide 3: what it is =====
{
  const s = content("Introduction", "VeriSource in four steps");
  T(s, "The buyer describes a need and the suppliers they know. The agent gathers evidence from public pages and official records. Every claim ends as proven, unproven or contradicted, with its source and date.", { x: M, y: 1.5, w: 11.4, h: 1.0, fontSize: 18, color: C.accent5 });
  const steps = [
    ["FiMessageCircle", "1  Describe", "Type or speak the need and the suppliers, in plain language."],
    ["FiCheckSquare", "2  Confirm", "Check what the agent understood, then confirm the requirements and the checks."],
    ["FiDatabase", "3  Collect", "Evidence arrives from public pages and official lists while you watch."],
    ["FiFileText", "4  Review", "Read the verdicts, open the evidence, record your decision, export a PDF."],
  ];
  const cw = 2.75, gap = 0.3;
  for (let i = 0; i < 4; i++) {
    const x = M + i * (cw + gap);
    card(s, x, 2.85, cw, 3.45);
    await iconDot(s, steps[i][0], x + 0.3, 3.15, 0.8, C.accent1, HEX.white);
    T(s, steps[i][1], { x: x + 0.3, y: 4.2, w: cw - 0.6, h: 0.45, fontSize: 22, bold: true, color: C.text2 });
    T(s, steps[i][2], { x: x + 0.3, y: 4.75, w: cw - 0.6, h: 1.2, fontSize: 16 });
  }
  T(s, "India only. The system never contacts a supplier.", { x: M, y: 6.5, w: 11, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  s.addNotes("Keep this brief: four steps. The rest of the demo walks through them with a real case.");
}

// ===== Slide 4: describe =====
pres.addSection({ title: "Walkthrough" });
{
  const s = content("Walkthrough", "Start by chatting, in your own words");
  T(s, "THE CASE WE WILL RUN", { x: M, y: 1.6, w: 4.4, h: 0.35, fontSize: 13, bold: true, color: C.accent1, charSpacing: 2 });
  T(s, "A hospital group audits the FFP2 respirators it bought during the 2020 emergency.", { x: M, y: 2.0, w: 4.4, h: 1.3, fontSize: 20, bold: true, color: C.text2 });
  T(s, "For each of four suppliers: did they hold a BIS licence for IS 9473:2002 on 27 August 2020, and do they make the masks themselves?", { x: M, y: 3.4, w: 4.4, h: 1.5, fontSize: 16 });
  T(s, "The agent fills in what it can read from the message and shows it back for correction. It asks only when in doubt.", { x: M, y: 5.0, w: 4.4, h: 1.4, fontSize: 16, color: C.accent5 });
  framed(s, "s2-requirements.png", 5.55, 1.65, 7.1, 5.19);
  s.addNotes("LIVE DEMO starts here. Paste the message with the four suppliers. Point out that nothing is checked yet; the agent has only drafted what it understood.");
}

// ===== Slide 5: gates =====
{
  const s = content("Walkthrough", "The buyer holds every gate");
  framed(s, "s3-checks.png", M, 1.65, 7.1, 5.19);
  const gates = [
    ["Confirm requirements", "Correct anything the agent read wrongly."],
    ["Confirm checks", "Tick what a supplier must pass to qualify."],
    ["Start verification", "Nothing runs until the buyer says go."],
    ["Record a decision", "The buyer decides. The agent never does."],
  ];
  let y = 1.65;
  for (let i = 0; i < 4; i++) {
    s.addShape(pres.ShapeType.ellipse, { x: 8.3, y, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { type: "none" } });
    T(s, String(i + 1), { x: 8.3, y, w: 0.6, h: 0.6, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, gates[i][0], { x: 9.1, y: y - 0.03, w: 3.6, h: 0.4, fontSize: 20, bold: true, color: C.text2 });
    T(s, gates[i][1], { x: 9.1, y: y + 0.4, w: 3.6, h: 0.6, fontSize: 15, color: C.accent5 });
    y += 1.15;
  }
  T(s, "No model output can trigger any of these.", { x: 8.3, y: 6.3, w: 4.4, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  s.addNotes("This is the trust story for a buyer. The agent proposes, the buyer decides. Show the checks card and tick the licence check. Mention the 'what counts as proof' expanders.");
}

// ===== Slide 6: collection =====
{
  const s = content("Walkthrough", "Watch the evidence arrive");
  T(s, "257 s", { x: M, y: 1.55, w: 4.6, h: 1.2, fontSize: 66, bold: true, color: C.accent1, fontFace: "Cambria" });
  T(s, "live collection for four suppliers in a measured run (236 s for two)", { x: M, y: 2.8, w: 4.4, h: 0.9, fontSize: 16, color: C.accent5 });
  const pts = [
    ["FiLayers", "Every supplier gets its own checks: the official licence export, the supplier website and BIS order applicability."],
    ["FiClock", "A background worker keeps the queue, so the work survives a closed tab or a restart."],
    ["FiEye", "Progress is announced per supplier, and a log of every attempt is one click away."],
  ];
  let y = 3.85;
  for (const [ic, t] of pts) {
    await iconDot(s, ic, M, y, 0.55, C.accent1, HEX.white);
    T(s, t, { x: M + 0.75, y: y - 0.05, w: 3.85, h: 0.95, fontSize: 15 });
    y += 1.0;
  }
  framed(s, "s4-running.png", 5.55, 1.65, 7.1, 5.19);
  s.addNotes("Start verification in the demo. While it runs (about four minutes for four suppliers), talk through slides 7 and 8, or take questions. The 257 s figure is from a measured live run; 236 s was for two suppliers.");
}

// ===== Slide 7: results =====
{
  const s = content("Walkthrough", "Results the buyer can inspect");
  const tiles = [
    ["4", "proven", C.accent3, "FiCheck"],
    ["8", "unproven", C.accent2, "FiHelpCircle"],
    ["0", "contradicted", C.accent4, "FiX"],
  ];
  const tw = 2.1, g = 0.3;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (tw + g);
    card(s, x, 1.65, tw, 1.65);
    T(s, tiles[i][0], { x: x + 0.3, y: 1.8, w: tw - 0.6, h: 0.9, fontSize: 48, bold: true, color: tiles[i][2], fontFace: "Cambria" });
    T(s, tiles[i][1], { x: x + 0.3, y: 2.75, w: tw - 0.6, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
  }
  T(s, "Held the BIS licence on 27 Aug 2020", { x: M, y: 3.65, w: 6.9, h: 0.4, fontSize: 20, bold: true, color: C.text2 });
  T(s, "All four suppliers proven, from the official BIS FFP2 licence list. Each result links to the record it came from.", { x: M, y: 4.1, w: 6.9, h: 0.9, fontSize: 16 });
  T(s, "Manufacturer and licence valid today", { x: M, y: 5.1, w: 6.9, h: 0.4, fontSize: 20, bold: true, color: C.text2 });
  T(s, "Unproven. The evidence needed was not found. That does not mean the claim is false, and the report says so.", { x: M, y: 5.55, w: 6.9, h: 0.9, fontSize: 16 });
  framed(s, "s6-table.png", 8.75, 1.5, 3.93, 5.31);
  s.addNotes("Open the report. Show a proven row and expand its Record to show the source and publication date. Then show an unproven row and its 'records set aside'. Stress: unproven is not false.");
}

// ===== Slide 8: verdicts =====
pres.addSection({ title: "How it works" });
{
  const s = content("How it works", "Three verdicts, nothing guessed");
  const v = [
    ["FiCheck", C.accent3, HEX.white, "Proven", "Evidence found for exactly this claim and period, from an official source. History is labelled as history: “held the licence on 27 Aug 2020”."],
    ["FiHelpCircle", C.accent2, HEX.white, "Unproven", "Evidence is missing, stale or ambiguous. Shown as a gap, never as a failure."],
    ["FiX", C.accent4, HEX.white, "Contradicted", "A source refutes the claim. Built into the rules, but no real source can show it yet."],
  ];
  const cw = 3.75, g = 0.325;
  for (let i = 0; i < 3; i++) {
    const x = M + i * (cw + g);
    card(s, x, 1.7, cw, 3.7);
    await iconDot(s, v[i][0], x + 0.35, 2.0, 0.85, v[i][1], v[i][2]);
    T(s, v[i][3], { x: x + 0.35, y: 3.05, w: cw - 0.7, h: 0.5, fontSize: 26, bold: true, color: C.text2, fontFace: "Cambria" });
    T(s, v[i][4], { x: x + 0.35, y: 3.65, w: cw - 0.7, h: 1.6, fontSize: 16 });
  }
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.75, w: 11.95, h: 0.85, rectRadius: 0.12, fill: { color: C.text2 }, line: { type: "none" } });
  T(s, "Every verdict shows its source, its date and the checks that were tried.", { x: M + 0.4, y: 5.75, w: 11.2, h: 0.85, fontSize: 20, bold: true, color: C.background1, valign: "middle" });
  s.addNotes("The vocabulary is fixed on purpose. Processing state (queued, checking, done) is shown separately from the verdict. Be upfront that contradicted exists in the design but cannot be demonstrated on the real data we have.");
}

// ===== Slide 9: how it works =====
{
  const s = content("How it works", "What happens behind the chat");
  const nodes = [
    ["FiMessageCircle", "Chat assistant", "Understands the message and asks short questions. Writes no facts."],
    ["FiUserCheck", "Buyer gates", "The buyer confirms requirements and checks, and starts verification."],
    ["FiGlobe", "Collector", "A background worker reads public pages and official lists."],
    ["FiShield", "Evidence engine", "Rules every claim from stored evidence, not from a model."],
    ["FiFileText", "Report", "Verdicts with sources and dates, a PDF export, the buyer's decision."],
  ];
  const nw = 2.1, ag = 0.36, y0 = 1.75;
  for (let i = 0; i < 5; i++) {
    const x = M + i * (nw + ag);
    card(s, x, y0, nw, 3.5);
    await iconDot(s, nodes[i][0], x + 0.3, y0 + 0.3, 0.75, i === 3 ? C.accent2 : C.accent1, HEX.white);
    T(s, nodes[i][1], { x: x + 0.25, y: y0 + 1.25, w: nw - 0.5, h: 0.7, fontSize: 18, bold: true, color: C.text2 });
    T(s, nodes[i][2], { x: x + 0.25, y: y0 + 1.95, w: nw - 0.5, h: 1.45, fontSize: 14 });
    if (i < 4) {
      s.addShape(pres.ShapeType.rightArrow, { x: x + nw + 0.04, y: y0 + 1.55, w: ag - 0.08, h: 0.4, fill: { color: C.accent1 }, line: { type: "none" } });
    }
  }
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.6, w: 11.95, h: 1.05, rectRadius: 0.12, fill: { color: C.accent1, transparency: 88 }, line: { type: "none" } });
  T(s, "Runs on one laptop. Cases are private to the signed-in buyer. Evidence and verdicts stay on the machine; only the chat text goes to a hosted free model, and the screen says which model is in use.", { x: M + 0.4, y: 5.6, w: 11.2, h: 1.05, fontSize: 16, color: C.text2, valign: "middle" });
  s.addNotes("Minimal technical view. Key message: the model sits in the first box only. Verdicts come from the evidence engine through ordinary application code. The privacy note matters: the typed chat text is the one thing that leaves the laptop, and the UI discloses it.");
}

// ===== Slide 10: guardrails =====
{
  const s = content("How it works", "Honest by construction");
  const g = [
    ["FiLock", "The assistant confirms nothing", "It can open a case, ask a question and explain results. Nothing else."],
    ["FiEdit3", "Facts are written by the app", "Once a case exists, results come from the stored assessment. The model's free text never reaches the buyer."],
    ["FiHelpCircle", "Gaps stay gaps", "Missing or ambiguous evidence is unproven. No guessing, no rounding up."],
    ["FiSlash", "No shortcuts", "It never contacts a supplier, never solves a CAPTCHA and never uses seeded demo data."],
  ];
  const cw = 5.85, ch = 2.2, gx = 0.25, gy = 0.25;
  for (let i = 0; i < 4; i++) {
    const x = M + (i % 2) * (cw + gx), y = 1.7 + Math.floor(i / 2) * (ch + gy);
    card(s, x, y, cw, ch);
    await iconDot(s, g[i][0], x + 0.35, y + 0.4, 0.8, C.accent1, HEX.white);
    T(s, g[i][1], { x: x + 1.45, y: y + 0.35, w: cw - 1.75, h: 0.5, fontSize: 20, bold: true, color: C.text2 });
    T(s, g[i][2], { x: x + 1.45, y: y + 1.0, w: cw - 1.75, h: 1.2, fontSize: 15 });
  }
  s.addNotes("This is what separates VeriSource from a neighbouring chatbot: it could not truthfully claim its answers come only from stored evidence; this one can. The guardrails stay in place whichever model is used.");
}

// ===== Slide 11: can / cannot prove =====
pres.addSection({ title: "Status" });
{
  const s = content("Status", "What it can prove today, and what it cannot");
  const cw = 5.85;
  card(s, M, 1.7, cw, 4.2, { fill: { color: C.accent3, transparency: 90 } });
  await iconDot(s, "FiCheck", M + 0.35, 2.0, 0.65, C.accent3, HEX.white);
  T(s, "Provable now", { x: M + 1.2, y: 2.05, w: 4, h: 0.55, fontSize: 24, bold: true, color: C.text2, fontFace: "Cambria" });
  T(s, [
    { text: "Held the BIS licence for IS 9473:2002 on 27 Aug 2020", options: { bold: true, breakLine: true } },
    { text: "Source: the imported BIS FFP2 licence list (cutoff 27 Aug 2020, 29 rows).", options: { breakLine: true } },
    { text: "Real runs on 20 Oct 2026: 4 of 4 suppliers proven.", options: {} },
  ], { x: M + 0.4, y: 3.0, w: cw - 0.8, h: 2.7, fontSize: 18, paraSpaceAfter: 12 });
  const x2 = M + cw + 0.25;
  card(s, x2, 1.7, cw, 4.2, { fill: { color: C.accent2, transparency: 90 } });
  await iconDot(s, "FiHelpCircle", x2 + 0.35, 2.0, 0.65, C.accent2, HEX.white);
  T(s, "Not provable yet", { x: x2 + 1.2, y: 2.05, w: 4.4, h: 0.55, fontSize: 24, bold: true, color: C.text2, fontFace: "Cambria" });
  T(s, [
    { text: "Manufacturer: a supplier's own website is self-report, so the engine refuses it.", options: { bullet: true, breakLine: true } },
    { text: "Licence valid today: the export is historical and the live BIS search is CAPTCHA-protected.", options: { bullet: true, breakLine: true } },
    { text: "Legal existence and current GST: no free, attributable source wired in.", options: { bullet: true, breakLine: true } },
    { text: "Contradicted: no source can refute a claim yet.", options: { bullet: true } },
  ], { x: x2 + 0.4, y: 3.0, w: cw - 0.8, h: 2.8, fontSize: 16, paraSpaceAfter: 10 });
  T(s, "If the buyer requires “valid today”, no supplier qualifies. That is by design.", { x: M, y: 6.2, w: 11.9, h: 0.45, fontSize: 18, bold: true, color: C.accent1 });
  s.addNotes("Be candid here. If a buyer ticks 'valid today' as required, no supplier qualifies, by design. We prefer an honest gap to a guess.");
}

// ===== Slide 12: measured =====
{
  const s = content("Status", "What we have measured so far");
  const st = [
    ["~5 s", "to create a case from a pasted message"],
    ["257 s", "live collection, four suppliers"],
    ["4 of 4", "suppliers proven for the BIS licence claim"],
    ["2 to 7 s", "for hosted chat answers"],
  ];
  const tw = 2.75, g = 0.3;
  for (let i = 0; i < 4; i++) {
    const x = M + i * (tw + g);
    card(s, x, 1.7, tw, 2.5);
    T(s, st[i][0], { x: x + 0.3, y: 2.0, w: tw - 0.6, h: 1.0, fontSize: 44, bold: true, color: C.accent1, fontFace: "Cambria" });
    T(s, st[i][1], { x: x + 0.3, y: 3.05, w: tw - 0.6, h: 1.0, fontSize: 16 });
  }
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 4.6, w: 11.95, h: 2.0, rectRadius: 0.12, fill: { color: C.accent2, transparency: 88 }, line: { type: "none" } });
  T(s, "Not measured yet, and not claimed", { x: M + 0.4, y: 4.85, w: 11, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
  T(s, "Accuracy against human auditors. Timing for a 30-supplier case. Voice accuracy with a real microphone. An accessibility audit of the new layout.", { x: M + 0.4, y: 5.4, w: 11.1, h: 1.0, fontSize: 17 });
  s.addNotes("Only numbers we actually measured. The 257 s run was live, four suppliers; the ~5 s case creation was from a pasted message. We have no accuracy figure and will not quote one.");
}

// ===== Slide 13: next =====
{
  const s = content("Status", "Where it goes next");
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.7, w: 11.95, h: 1.3, rectRadius: 0.12, fill: { color: C.text2 }, line: { type: "none" } });
  T(s, "First: make more claims provable", { x: M + 0.4, y: 1.9, w: 11, h: 0.45, fontSize: 22, bold: true, color: C.background1 });
  T(s, "A certificate route (ISO certificate to issuer record) and a real source that can contradict a claim.", { x: M + 0.4, y: 2.4, w: 11.1, h: 0.5, fontSize: 16, color: C.accent6 });
  T(s, "ROADMAP: DRAFTED AS SPECS, NOT BUILT", { x: M, y: 3.35, w: 8, h: 0.35, fontSize: 13, bold: true, color: C.accent1, charSpacing: 2 });
  const r = [
    ["Supplier discovery", "The agent finds suppliers for the buyer."],
    ["Drawings and PDFs", "Start a case from an uploaded document."],
    ["Outreach", "Follow-ups drafted, each one approved by the buyer."],
    ["Monitoring", "Re-check suppliers over time."],
    ["Voice acceptance", "Prove spoken input works for real buyers."],
    ["Second country", "Extend beyond India."],
  ];
  const cw = 3.75, ch = 1.2, g = 0.35;
  for (let i = 0; i < 6; i++) {
    const x = M + (i % 3) * (cw + 0.325), y = 3.8 + Math.floor(i / 3) * (ch + 0.25);
    card(s, x, y, cw, ch);
    T(s, r[i][0], { x: x + 0.3, y: y + 0.2, w: cw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
    T(s, r[i][1], { x: x + 0.3, y: y + 0.65, w: cw - 0.6, h: 0.5, fontSize: 14, color: C.accent5 });
  }
  s.addNotes("Supplier discovery is the closest to the original agentic goal. Outreach is only ever with the buyer's approval of each message. None of the roadmap items is built; they are drafted as specifications.");
}

// ===== Slide 14: close =====
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Status" });
  s.addText("The agent proposes. The buyer decides.", { placeholder: "title" });
  s.addText("Every answer is tied to a source, a date and the checks that were tried. A gap is shown as a gap.", { placeholder: "body" });
  T(s, "Thank you. Questions?", { x: M, y: 6.3, w: 8, h: 0.5, fontSize: 24, bold: true, color: C.background1 });
  s.addNotes("Close on the principle, then take questions. If time allows, show the cases drawer to reopen an earlier assessed case.");
}

await pres.writeFile({ fileName: OUT });
await applyTheme(OUT, THEME);
console.log("wrote", OUT);
