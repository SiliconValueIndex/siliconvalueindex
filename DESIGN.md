---
name: SiliconValueIndex
description: Charcoal analytics with pale green actions and readable GPU value comparisons.
colors:
  ink: "#101413"
  raised: "#191f1d"
  raised-2: "#232c28"
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
  sidebar: "#151a17"
  nav-selected: "#293629"
  price-context: "#202a23"
typography:
  display:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "clamp(2rem, 3vw, 3rem)"
    fontWeight: 500
    lineHeight: 1.16
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "1.5625rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  title:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  body:
    fontFamily: "IBM Plex Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    lineHeight: 1.5
  label:
    fontFamily: "IBM Plex Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "0.75rem"
    lineHeight: 1.5
  numeric:
    fontFamily: "IBM Plex Mono, ui-monospace, Cascadia Mono, Consolas, monospace"
rounded:
  base: "6px"
  control: "8px"
  segment: "5px"
  panel: "14px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "28px"
  gutter: "clamp(16px, 4vw, 40px)"
components:
  button-primary:
    backgroundColor: "{colors.link}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  button-primary-hover:
    backgroundColor: "{colors.link-hover}"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  market-panel:
    backgroundColor: "{colors.raised}"
    rounded: "{rounded.panel}"
    padding: "24px"
  navigation-selected:
    backgroundColor: "{colors.nav-selected}"
    textColor: "{colors.link}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
---

# Design System: SiliconValueIndex

## Overview

The implemented direction is a charcoal analytics workspace with pale green actions. Compact navigation, restrained panels, and clear numerical hierarchy support the practical job of comparing GPU price and performance. This is a code-led adaptation of dashboard reference lessons, with original site content and no copied external artwork.

Key characteristics:

- Persistent desktop wayfinding and compact mobile top navigation.
- Tonal surface separation, fine borders, and quiet supporting copy.
- Sans-serif explanations paired with monospaced numerical evidence.
- Semantic value colors backed by labels and a visible FPS minimum.

## Colors

The primary pale green marks actions, selected controls, links, and great value. Its lighter hover variant provides feedback. Dark on-accent text keeps filled actions readable.

Fair value uses warm sand; poor value uses muted rose. Below-minimum cards use subdued gray-green and hollow chart marks. Vendor colors belong to narrow vendor ticks, distinct from value judgments.

The neutral palette steps from the ink canvas through raised surfaces to hovered surfaces. Text, muted text, and dim text establish three levels of emphasis. Fine rules divide information; stronger rules define controls. The sidebar, selected navigation background, and price context strip have specific tonal fills extracted from the implementation.

**The Context Rule.** Value colors never replace the accompanying labels, thresholds, or below-minimum state.

## Typography

IBM Plex Sans carries navigation, headings, and body copy. IBM Plex Mono carries numeric values and tabular comparisons. Both are loaded at weights 400, 500, and 600; system fallbacks remain available.

The homepage display role is compact enough to leave room for data. Its mobile size becomes 2.3rem. General headings retain the global scale, while dashboard headings use smaller contextual sizes. Body paragraphs are bounded at 68ch globally; homepage introductory text is 70ch with a smaller size and relaxed line height. Labels stay in sentence case. Tabular numerals preserve comparison alignment.

## Layout

Above 1100px, the fixed desktop sidebar is 224px wide. Main content starts at 264px, has a 40px right margin, and a maximum width of 1440px. At 1100px and below, the sidebar narrows to 190px and content starts at 214px with a 24px right margin.

At 760px and below, the shell becomes a static top header, with six navigation links in three columns and content inset by 16px. The sidebar note is hidden. Controls retain usable touch targets.

The current homepage pairs a flexible chart panel with a 270px shortlist, separated by 22px. At 1200px and below the shortlist moves underneath in three columns; at 760px it becomes a single list. The price snapshot strip precedes the chart and the explanatory reading guide follows it. These are the homepage composition, not a mandatory template for every route.

## Elevation & Depth

Panels use tonal layering and one-pixel borders rather than ambient shadows. The fixed chart tooltip is the exception: its light surface, dark text, and small shadow distinguish transient data from the chart. The tooltip shadow and responsive breakpoints live in the sidecar.

## Shapes

Controls use gently rounded corners, dashboard panels use broader corners, and compact badges are pills. The chart itself sits flat within its panel. The brand is a small pale green rounded square with an inset outlined square; navigation uses simple stroke icons.

## Components

### Buttons and fields

Primary actions use pale green with dark text; secondary actions use raised neutral surfaces and a stronger border. Buttons and selects have a minimum height of 44px. The homepage main action increases to 48px and uses roomier padding. Hover changes the fill. Keyboard focus uses a two-pixel accent outline with a two-pixel offset.

### Segmented controls

Resolution and rendering selectors sit on an ink surface with compact spacing. Selected segments use the primary fill; unavailable choices are visibly disabled. Homepage segments are 36px tall on desktop and 44px on mobile. Selected controls retain a contrasting inset focus indicator.

### Navigation

Navigation pairs a stroke icon with a plain label. The selected route has pale green text on a tinted background and sets `aria-current`. Hover uses a raised surface. The skip link becomes visible on keyboard focus.

### Chart and shortlist

The chart uses dashed value thresholds, a shaded below-minimum region, labeled axes, and semantic dots. Hovered or focused points receive a stronger outline and enlarged mark. A disclosure exposes the numerical table, including estimated-FPS labels.

Resolution and rendering changes synchronize the chart, shortlist, threshold legend, minimum-FPS note, table, ranked-list link, and URL. The shortlist contains best value, close second, and highest cost per FPS among playable cards, with duplicates removed. Price dates describe recorded snapshots, never live quotes.

### Tables and explanatory copy

Tables use fine row separators, muted headers, a subtle hovered row, and right-aligned monospaced numeric columns. Wide tables scroll within their region. Explanatory prose uses narrower measures and restrained section dividers.

## Do's and Don'ts

- Do preserve the semantic palette, keyboard focus, estimated-result labels, price dates, and source links.
- Do keep chart controls, shortlist, and supporting numbers tied to the same view.
- Do use the existing tonal surfaces and type hierarchy when adding screens.
- Don't substitute vendor branding colors for value ratings.
- Don't present price snapshots as live quotes or test averages as guaranteed gameplay results.
- Don't ship reference screenshots as product artwork; they are research evidence only.

