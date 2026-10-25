---
name: ClickCraft
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#ca8100'
  on-tertiary-container: '#3e2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.025em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 1rem
    fontWeight: '500'
    lineHeight: 1.5rem
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Geist
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: -0.005em
  body-sm:
    fontFamily: Geist
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: '0'
  label-md:
    fontFamily: Geist
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
  tabular-data:
    fontFamily: Geist
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 0.75rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system establishes a high-performance, distraction-free environment tailored for power users, developers, and automation specialists. Drawing direct inspiration from macOS desktop utilities and modern productivity suites like Linear and Raycast, the aesthetic balances utilitarian engineering with polished industrial precision.

### Character & Tone
- **Technical Rigor:** Monoline micro-borders, dense information hierarchy, and exact alignment reflect precision execution.
- **Low Fatigue:** Deep slate backdrops replace absolute blacks, softening luminance contrast during extended usage.
- **Tactile Restraint:** Transitions are immediate (sub-150ms) and linear-feel, avoiding superfluous bounce or decorative playfulness.
- **Visual Stance:** Monochromatic slate canvas elevated by high-potency indigo interactive cues and translucent squircle panels.

## Colors

The palette is engineered around dark-mode workflows where foreground instrumentation needs to pop without causing screen glare.

### Surface Tiers & Containers
- **Canvas Base (`#0F172A`):** The master canvas, providing a rich, non-fatiguing baseline.
- **Container Panel (`#1E293B`):** Base structural panels, sidebars, and inactive tab groups.
- **Elevated Interactive (`#334155`):** Raised states, active segmented options, and hover surfaces.
- **Ghost Boundary (`rgba(255, 255, 255, 0.08)` / `#475569`): Subtle structural dividers ensuring crisp edge definition.

### Accents & Signal Matrix
- **Primary Indigo (`#6366F1`):** Applied to active toggles, primary triggers, and focused inputs.
- **Execution Emerald (`#10B981`):** Reserved strictly for active automation loops, running states, and verified triggers.
- **Macro Amber (`#F59E0B`):** Designated for keystroke capture, recording sequences, and warning states.
- **Muted Signal (`#94A3B8`):** Unfocused labels, idle badges, and secondary metadata.

## Typography

Typography prioritizes legibility at compact scales and high numeric stability. 

- **Display & Headings:** `Hanken Grotesk` introduces modern geometric poise for window headers, macro section titles, and modal sheets.
- **Interface & Data:** `Geist` drives all interactive elements, numeric readouts, and hotkey sequences.
- **Tabular Figures:** All numeric fields (interval timers, iteration counters, coordinate monitors) must enable `font-variant-numeric: tabular-nums` to eliminate layout shift during active continuous clicking.

## Layout & Spacing

The layout is anchored in an immutable desktop tool philosophy: high spatial efficiency, compact component density, and structured module grids.

### Desktop-First Shell
- **Primary Grid:** Built on an 8-column layout for utility windows, collapsing into a clean single-column or stacked 2-column view on compact widgets.
- **Density:** Baseline spacing follows a rigid 4px metric grid (`space-xs` = 4px, `space-sm` = 8px, `space-md` = 12px, `space-lg` = 16px, `space-xl` = 24px).
- **Toolbars & Panels:** Fixed sidebars measure 220px, maintaining full fluid horizontal flexibility for the core configuration panel.

## Elevation & Depth

Depth is defined via surface tone shifting combined with monoline borders rather than heavy atmospheric dropshadows, ensuring crisp execution in dark environments.

### The Stack Model
- **Base Layer (Elevation 0):** Canvas `#0F172A` with no shadow.
- **Panel Inset (Elevation 1):** Background `#1E293B`, framed by a single 1px outline of `rgba(255, 255, 255, 0.08)`. 
- **Interactive Elevated (Elevation 2):** Background `#334155`, soft perimeter boundary `rgba(255, 255, 255, 0.12)`, supported by an ambient drop shadow: `0 4px 12px rgba(0, 0, 0, 0.35)`.
- **Floating Modals / Flyouts (Elevation 3):** Background `#1E293B` backed by an ultra-thin highlight ring `rgba(255, 255, 255, 0.15)` and soft occlusion: `0 12px 32px rgba(0, 0, 0, 0.5)`.

## Shapes

The interface embraces modern macOS squircle geometry (Level 2 Roundedness), maintaining sharp structural clarity without harsh corners.

- **Standard Elements (0.5rem / 8px):** Primary buttons, text input fields, segmented control pills, and dropdown triggers.
- **Cards & Panes (1rem / 16px):** Macro blocks, monitor cards, and parameter groupings.
- **Pill Badges (9999px):** Hotkey identifiers, status indicators, and unit tags (e.g., `ms`, `px`).

## Components

### Buttons & Action Bars
- **Primary Action (Execute/Start):** Background `#6366F1` with white text. On click execution, transforms into running state with `#10B981`. Inset highlight `1px inset rgba(255, 255, 255, 0.2)` on top edge.
- **Secondary / Stop:** Background `#1E293B`, border `1px solid rgba(255, 255, 255, 0.12)`, hover `#334155`.
- **Icon Buttons:** Fixed 28x28px or 32x32px squircle targets with centered 14px iconography.

### Numeric Stepper Inputs
- Composed of an input shell, numerical Geist monospace typography, up/down micro-chevrons, and an integrated trailing unit pill (`ms`, `s`, `mins`).
- Integrated boundary checks: Focused state emits a clean `0 0 0 1px #6366F1` ring.

### Hotkey Badges
- Modeled as physical key caps: Background `#0F172A`, border `1px solid rgba(255, 255, 255, 0.14)`, shadow `0 1px 0 rgba(255, 255, 255, 0.08)`. Text rendered in `Geist` semibold uppercase.

### Segmented Controls
- Encased in a sunken track (`#0F172A`, 4px padding). Active segment transitions horizontally with a 120ms ease, taking surface `#334155` and a 1px border `rgba(255, 255, 255, 0.08)`.

### Coordinate Pickers
- Split controls containing `X` and `Y` coordinate inputs paired with an interactive crosshair target icon button that triggers screen-space inspection.

### Toggle Switches
- Track dimension: 36x20px with `#334155` idle fill, switching to `#6366F1` when active.
- Thumb: 16x16px solid `#FFFFFF` circular knob with a slight 1px bottom shadow.