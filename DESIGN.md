---
name: SiliconValueIndex
description: Crisp dark GPU buying advice, verdict first and evidence below.
colors:
  ink: "#0b0d0c"
  raised: "#131715"
  raised-2: "#1c221e"
  rule: "#303b35"
  rule-strong: "#59685f"
  text: "#eef4ef"
  muted: "#aebdb3"
  dim: "#93a69a"
  link: "#b6ed8a"
  link-hover: "#cef7b0"
  on-accent: "#101413"
  great: "#b6ed8a"
  fair: "#e3c78f"
  poor: "#e89da8"
  unplayable: "#93a69a"
  great-soft: "rgba(162, 206, 156, 0.12)"
  fair-soft: "rgba(227, 184, 103, 0.12)"
  poor-soft: "rgba(237, 148, 122, 0.12)"
  nvidia: "#76b900"
  amd: "#ed1c24"
  intel: "#0071c5"
typography:
  display:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(2.5rem, 6vw, 4.5rem)"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    lineHeight: 1.5
  numeric:
    fontFamily: "Geist, Segoe UI, system-ui, sans-serif"
    fontVariantNumeric: "tabular-nums"
  monospace:
    fontFamily: "Geist Mono, ui-monospace, Cascadia Mono, Consolas, monospace"
rounded:
  base: "6px"
  panel: "10px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  section: "64px"
  gutter: "clamp(16px, 4vw, 40px)"
layout:
  max: "1200px"
  header: "64px"
  mobile: "760px"
---

# SiliconValueIndex design system

The site helps budget PC builders choose a card quickly, then inspect the evidence.
Near-black canvas, sharp type hierarchy, generous whitespace and one-pixel rules
keep the advice readable. Surfaces use subtle neutral steps, with very little boxing.
No gradients or decorative imagery are needed.

## Tokens and typography

Global CSS has one token layer, followed by base styles, shell and shared components.
Use the spacing and radius scales above; panels never exceed 10px, badges are pills.
Mint green is the action and great-value colour. Sand means fair, rose means poor,
and gray-green marks below-playable results. Every value colour needs a word or
threshold. NVIDIA, AMD and Intel colours belong only to vendor ticks.

Geist serves UI, headings and numbers at weights 400, 500 and 600. The --font-num
token points to Geist; numeric displays and table cells use tabular figures, with
right alignment in tables. All table headers, including numeric headers, use Geist.
Geist Mono at 400 and 500 is reserved for chart tick labels and code through the
--font-mono token. Google Fonts supplies both, with system fallbacks. OG generation retains IBM Plex and
its existing assets. Display headings use tight tracking and responsive sizing;
body text remains 1rem and explanatory prose is bounded to 68 characters.

Muted text has at least 4.5:1 contrast on both ink and raised surfaces, as does mint
text on ink. Dim text remains readable for secondary information.

## Shell and navigation

A sticky 64px top bar holds the square inset brand mark and five plain links:
Find a card, Rankings, Compare, Methodology and Data. There is no duplicate Find
button. The selected route is underlined and has aria-current="page". Content is
centred within 1200px with responsive gutters and no lateral offset.

At 760px and below, the brand and native Menu disclosure replace desktop links.
The disclosure works without JavaScript, with 44px touch targets. A skip link and
visible 2px keyboard focus rings are mandatory. The footer has a quiet hairline,
data run date, source credits, GitHub link and recorded-snapshot wording.

## Homepage order and interaction

1. Verdict: the first playable card by rank, cost per FPS, recorded price, average
   FPS, estimated label when needed, value word and retailer link. A runner-up and
   price dates follow immediately. Prices older than 60 days carry a caution.
2. Picker: resolution, rendering and budget, followed by See my picks. View changes
   update the verdict, top list, chart, table, thresholds, price dates and URL.
   Budget filters the verdict and list; the chart retains the full market context.
   Empty selections explain that no playable card fits and link to Find.
3. Top five: rank, linked card, price, FPS and cost per FPS with value word. Rows
   stack on mobile without hiding price or FPS. A link opens the full ranking.
4. Market chart: an open canvas, labelled thresholds, focusable points, tooltip on
   focus and an accessible table disclosure. Its established behaviour is preserved.
5. How to read this: three short columns covering benchmark limits, measured versus
   estimated results and playability first; stacked on mobile with methodology links.

Shared pure helpers choose the verdict and top list on both server and client.
Any budget explicitly hands Find the ceiling of the highest current price to the
next $100, using the same helper as Find's slider. Numeric budgets pass unchanged.
The primary verdict and table remain visible without JavaScript.

## Other pages and shared components

Secondary pages inherit the same shell, typography and tokens. Find retains its
requirements controls and stored URL behaviour. Compare retains stored picks;
card pages retain price history and evidence. Rankings retain desktop columns
and show price and FPS in stacked mobile rows.

Buttons, selects and segmented controls have 44px minimum heights. Filled mint
actions use dark text; selected segments keep a contrasting inset focus ring.
Unavailable choices remain disabled. Tables use hairline rows, right-aligned
tabular numbers and sticky headers inside scrollable regions. Reduced-motion
preferences suppress animation and transitions.

## Do's and don'ts

- Do lead with a usable answer and put evidence immediately below.
- Do preserve real numbers, estimated labels, price dates, links and source credits.
- Do describe prices as recorded snapshots and benchmarks as test-suite averages.
- Do keep selected controls, verdict, shortlist and evidence on the same view.
- Do use visible focus, semantic HTML and non-colour selection indicators.
- Don't hide price or FPS on phones, or rely on colour alone for a rating.
- Don't use vendor colours as value ratings, RGB effects or heavy panel decoration.
- Don't stack conflicting CSS overrides or introduce runtime frameworks.
- Don't change scoring, pipeline data, OG assets or favicon as part of this system.
