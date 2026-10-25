---
name: Swiss Precision Utility
colors:
  surface: '#fff8f5'
  surface-dim: '#e2d8d2'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fcf2eb'
  surface-container: '#f6ece6'
  surface-container-high: '#f0e6e0'
  surface-container-highest: '#eae1da'
  on-surface: '#1f1b17'
  on-surface-variant: '#3d4a42'
  inverse-surface: '#342f2b'
  inverse-on-surface: '#f9efe8'
  outline: '#6d7a72'
  outline-variant: '#bccac0'
  surface-tint: '#006c4a'
  primary: '#006948'
  on-primary: '#ffffff'
  primary-container: '#00855d'
  on-primary-container: '#f5fff7'
  inverse-primary: '#68dba9'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fd'
  on-secondary-container: '#57657b'
  tertiary: '#006194'
  on-tertiary: '#ffffff'
  tertiary-container: '#007bb9'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f8c4'
  primary-fixed-dim: '#68dba9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#005137'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#93ccff'
  on-tertiary-fixed: '#001d31'
  on-tertiary-fixed-variant: '#004b73'
  background: '#fff8f5'
  on-background: '#1f1b17'
  surface-variant: '#eae1da'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.75rem
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 1.375rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.375rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.125rem
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.05em
  telemetry-mono:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers a high-precision, utilitarian aesthetic inspired by classic Swiss rationalism and industrial instrumentation. Designed for a high-performance desktop workflow, the interface prioritizes immediate legibility, functional hierarchy, and disciplined restraint over decorative trends.

### Visual Character
- **Disciplined Precision:** Architectural structure anchored by structural rules, exact alignments, and crisp hair-width micro-borders.
- **Warm Industrial Surfaces:** Neutral foundations derived from warm titanium and fine sandstone slate, avoiding sterile laboratory whites or eye-straining high-contrast starkness.
- **Engineered Accents:** Focused application of engineered emerald green (`#059669`) solely for active states, operational indicators, and critical metrics.
- **Understated Craft:** Subtle mechanical affordances, tactile feedback states, and compact telemetry-inspired data layouts.

## Colors

The palette establishes an ergonomic, daylight-optimized desktop environment with warm slate and titanium base surfaces, punctuated by an unmistakable engineered emerald accent.

### Color Roles
- **Primary (`#059669`):** Engineered Emerald. Reserved strictly for primary confirmation actions, running engine statuses, toggled-on switches, and real-time triggers.
- **Secondary (`#334155`):** Slate Iron. Used for secondary tool buttons, structural frame headers, inactive mechanical tab switches, and prominent structural iconography.
- **Tertiary (`#0284c7`):** Precision Cerulean. Dedicated to readouts requiring distinct semantic divergence from the primary engine (e.g., cursor coordinates, target locks, and hotkey bindings).
- **Neutral (`#78716c`):** Sandstone Stone. Forms the tint foundation for surface backgrounds (`#FBFBFA`), secondary panel insets (`#F4F3F0`), subtle borders (`#E7E5E0`), and structural dividers (`#D6D3CC`).
- **Foreground Contrast:** Primary text rests at deep charcoal (`#1C1917`), secondary at muted slate (`#57534E`), and disabled or metadata labels at stone gray (`#A8A29E`).

## Typography

The typographic hierarchy pairs the architectural clarity of **Hanken Grotesk** for headings and high-level counters with the clinical legibility of **Inter** for dense interface controls, parameters, and telemetry readouts.

### Usage Standards
- **Headlines (`Hanken Grotesk`):** Track tightly to maintain dense visual gravity. Used for window headers, pane identifiers, and key quantitative status dashboards.
- **Body & Controls (`Inter`):** Renders all parameter titles, contextual hints, and configuration matrices. Numerical values and milliseconds use tabular lining figures (`font-feature-settings: 'tnum' 1`) to eliminate jitter during active auto-click loops.
- **Micro Labels (`label-sm`):** Rendered in small-caps or uppercase with widened tracking (`0.05em`) for grouping labels, unit notations (`MS`, `CPS`, `X/Y`), and status tags.

## Layout & Spacing

This design system uses a modular grid designed specifically for compact desktop panels and precision tools.

### Grid & Density
- **Desktop Form Factor:** Default 12-column layout or asymmetrical split-pane system (Fixed sidebar: 280px, primary workbench: flexible minimum 540px).
- **Rhythm:** An ultra-compact 4px baseline sub-grid (`0.25rem` intervals) governs element packing. Density is prioritized so power users can monitor all trigger sequences without vertical viewport scrolling.
- **Structural Insets:** Windows and elevated inspector panels use `margin-desktop` (24px) from outer boundaries, with `gutter-desktop` (16px) isolating modular parameter cards.

## Elevation & Depth

Visual hierarchy is communicated through structural layering, hairline borders, and subdued ambient contact shadows rather than high-elevation blur stacks.

### Layering Philosophy
- **Base Canvas:** Tinted sandstone titanium surface (`#FBFBFA`).
- **Surface Insets (Recessed Level):** Sub-panels and numeric input wells use `#F4F3F0` with a 1px solid inset border (`#E7E5E0`), conveying mechanical precision and tactile depth.
- **Elevated Controls & Floating Windows:** Floating status HUDs and flyout menus rely on crisp 1px borders (`#D6D3CC`) backed by an ultra-subtle contact shadow: `0 1px 3px rgba(28, 25, 23, 0.05), 0 4px 12px rgba(28, 25, 23, 0.04)`.
- **Active State Highlighting:** Active elements receive a sharp 1px outer ring in `#059669` or a low-intensity green glow (`0 0 0 1px #059669, 0 1px 4px rgba(5, 150, 105, 0.15)`).

## Shapes

The shape geometry follows an engineered aesthetic characterized by tight, controlled corner radiuses (`roundedness: 1`).

### Radius Tokens
- **Base Component (`0.25rem` / 4px):** Applied to buttons, numeric inputs, chips, segmented toggles, and dropdown triggers.
- **Containers & Panels (`rounded-lg` / 0.5rem / 8px):** Applied to parameter cards, telemetry grouping boxes, and popover panels.
- **Structural Windows (`rounded-xl` / 0.75rem / 12px):** Applied exclusively to top-level desktop windows and modal dialogues.
- **Precision Circles:** Applied solely to state indicators, radio selectors, and coordinate crosshair markers. Full pills are restricted to telemetry status indicators.

## Components

### Buttons
- **Primary (Engine Run / Activate):** Solid `#059669` background with white text, tight font weight (`600`), 0.25rem border radius, and a subtle top-edge inner highlight. In hover, transitions to `#047857`. Active press introduces a 1px physical press down-shift.
- **Secondary (Configuration / Reset):** Sandstone slate surface (`#FFFFFF`) with a 1px solid border (`#D6D3CC`), slate charcoal text (`#334155`), and subtle hover darkening (`#F4F3F0`).
- **Ghost Utility:** Borderless with slate text, used for compact icon controls in the utility toolbar.

### Tactile Switches & Toggles
- **Mechanical Toggle Track:** Recessed 36px x 20px pill with a 1px inner border. Inactive state: `#E7E5E0`. Active state: `#059669`.
- **Thumb:** 16px solid white disc with a micro-drop shadow (`0 1px 2px rgba(0,0,0,0.15)`). Glides linearly across a 16px throw.

### Inputs & Number Steppers
- **Text & Numeric Fields:** Recessed light sandstone field (`#F4F3F0`), 1px structural border (`#D6D3CC`), sharp 4px corners, and monospaced numeric figures (`Inter` tnum).
- **Embedded Unit Badges:** Fixed labels (e.g., `ms`, `CPS`, `px`) right-aligned inside the input field in stone gray (`#78716c`).
- **Focus State:** 1px border shift to `#059669` with a subtle 2px soft green shadow buffer.

### Telemetry Status Badges & Chips
- **Idle / Standby Badge:** Sandstone background (`#E7E5E0`), muted slate text (`#57534E`), and a neutral 6px circular dot.
- **Running / Armed Badge:** Light emerald-tinted surface (`#ECFDF5`), bold emerald border (`#A7F3D0`), dark emerald text (`#065F46`), and a pulsing green indicator beacon (`#059669`).
- **Compact Segmented Chips:** Clustered selector tabs for trigger methods (Single, Double, Hold) styled as flat segmented toggles with a distinct 1px border separation.

### Cards & Grouping Surfaces
- **Section Enclosures:** Built with flat white tiles (`#FFFFFF`) enclosed by a strict 1px border (`#E7E5E0`).
- **Card Headers:** Monospaced label-sm categorization banner featuring a subtle border divider underneath, dividing structural controls from operational metrics.