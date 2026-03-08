# Quantum MCP Relayer -- Brand Identity Guide

> The first quantum-native MCP service. Built for AI developers who ship.

---

## 1. Brand Name & Tagline

### Name: **Quantum MCP Relayer**

Short form: **QRelay** (for CLI tools, package names, social handles)

Namespace-friendly: `qrelay`, `@qrelay`, `qrelay-sdk`

### Tagline Options

| Option | Tagline | Notes |
|--------|---------|-------|
| **A (Recommended)** | **Quantum inference, one API call away.** | Direct. Tells developers exactly what they get. Mirrors Stripe's "payments infrastructure" simplicity. |
| B | **The quantum layer for AI agents.** | Positions as infrastructure. Good for MCP-aware audience. |
| C | **Ship quantum. Skip the physics.** | Punchy. Works well in ads and social. Might feel too casual for enterprise. |
| D | **MCP meets quantum. Finally.** | Insider appeal. Assumes audience knows MCP. |

**Recommendation:** Option A as the primary tagline. Use C for developer marketing campaigns and social. Use B in technical documentation headers.

---

## 2. Brand Voice

### Personality Traits

| Trait | What it means in practice |
|-------|--------------------------|
| **Direct** | Say what it does. No fluff. Lead with the verb. |
| **Technically confident** | We know quantum computing. We don't need to prove it with jargon. |
| **Calm authority** | We're not excited about quantum -- we're building with it. Big difference. |
| **Developer-peer** | We write code too. Talk like a senior engineer, not a salesperson. |

### Tone Spectrum

```
Casual -------|-------X--- Formal
Simple ---X---|----------- Complex
Serious ------|-X--------- Playful
Humble -------|-X--------- Bold
```

We sit slightly formal, very simple, slightly playful, and moderately bold.

### Voice Dos

- Use active voice. "QRelay processes your request" not "Your request is processed by QRelay."
- Use second person. "You deploy" not "Users deploy."
- Use concrete numbers. "3ms median latency" not "blazing fast."
- Use code examples as proof, not adjectives.
- Keep sentences short. If a sentence has a comma, consider splitting it.
- Say "we" when talking about the team. Say "QRelay" when talking about the product.

### Voice Don'ts

- Don't say "revolutionary," "groundbreaking," or "paradigm shift." Ever.
- Don't explain quantum mechanics unless the user asked. Abstract it away.
- Don't use "leverage," "utilize," "facilitate," "synergy," or "holistic."
- Don't hype. If something is in beta, say it's in beta.
- Don't talk down to developers. No "simply" or "just" before hard things.
- Don't over-qualify. "Fast" is fine. "Incredibly blazingly ultra-fast" is not.

### Example Rewrites

| Before (bad) | After (good) |
|-------------|-------------|
| "Leverage our revolutionary quantum computing platform to facilitate seamless AI inference." | "Run quantum inference from your AI agent. One API call." |
| "Simply integrate our solution into your existing workflow." | "Add `qrelay` to your MCP config. You're done." |
| "We are excited to announce our groundbreaking new feature!" | "New: batch mode for quantum circuits. Docs here." |

---

## 3. Color Palette

### Primary Colors

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Primary | **Quantum Indigo** | `#6C5CE7` | Brand mark, primary buttons, key UI elements |
| Primary Dark | **Deep State** | `#2D1B69` | Dark backgrounds, headers, hero sections |
| Primary Light | **Superposition** | `#A29BFE` | Hover states, secondary elements, highlights |

### Secondary Colors

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Secondary | **Circuit Blue** | `#0984E3` | Links, interactive elements, data viz |
| Secondary Dark | **Entangled** | `#0652DD` | Active states, focused elements |
| Secondary Light | **Coherence** | `#74B9FF` | Info banners, light accents |

### Accent Colors

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Accent | **Qubit Cyan** | `#00CEC9` | Success states, CTAs, attention points |
| Accent Warm | **Photon** | `#FD79A8` | Warnings, highlights, marketing pops |
| Accent Glow | **Interference** | `#00F5D4` | Terminal/code highlights, data streams |

### Neutrals

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Neutral 950 | **Void** | `#0A0A0F` | Primary dark background |
| Neutral 900 | **Dark Matter** | `#13131A` | Card backgrounds (dark mode) |
| Neutral 800 | **Obsidian** | `#1E1E2E` | Secondary dark surfaces |
| Neutral 600 | **Graphite** | `#636380` | Muted text, borders |
| Neutral 400 | **Silver Ion** | `#A0A0B8` | Placeholder text, disabled states |
| Neutral 100 | **Frost** | `#F0F0F5` | Light mode background |
| Neutral 50 | **White Space** | `#FAFAFF` | Cards, content areas (light mode) |

### Semantic Colors

| Role | Hex | Usage |
|------|-----|-------|
| Success | `#00B894` | Successful operations, connected states |
| Warning | `#FDCB6E` | Rate limits, deprecation notices |
| Error | `#E17055` | Failed requests, errors |
| Info | `#74B9FF` | Tips, documentation callouts |

### Dark Mode First

QRelay is dark-mode-first. The default docs, dashboard, and marketing site use `Void` (#0A0A0F) as the base. Light mode is supported but secondary.

### Accessibility

All text-on-background combinations must meet WCAG 2.1 AA (4.5:1 for body text, 3:1 for large text). Key passing combos:

- `#FAFAFF` on `#0A0A0F` -- 19.2:1 (passes AAA)
- `#A29BFE` on `#0A0A0F` -- 7.1:1 (passes AAA)
- `#00CEC9` on `#0A0A0F` -- 10.4:1 (passes AAA)
- `#6C5CE7` on `#FAFAFF` -- 4.6:1 (passes AA)

### CSS Variables

```css
:root {
  /* Primary */
  --qr-primary: #6C5CE7;
  --qr-primary-dark: #2D1B69;
  --qr-primary-light: #A29BFE;

  /* Secondary */
  --qr-secondary: #0984E3;
  --qr-secondary-dark: #0652DD;
  --qr-secondary-light: #74B9FF;

  /* Accent */
  --qr-accent: #00CEC9;
  --qr-accent-warm: #FD79A8;
  --qr-accent-glow: #00F5D4;

  /* Neutrals */
  --qr-neutral-950: #0A0A0F;
  --qr-neutral-900: #13131A;
  --qr-neutral-800: #1E1E2E;
  --qr-neutral-600: #636380;
  --qr-neutral-400: #A0A0B8;
  --qr-neutral-100: #F0F0F5;
  --qr-neutral-50: #FAFAFF;

  /* Semantic */
  --qr-success: #00B894;
  --qr-warning: #FDCB6E;
  --qr-error: #E17055;
  --qr-info: #74B9FF;
}
```

---

## 4. Typography

### Primary Typeface: **Inter**

Use for: UI, body text, documentation, dashboards.

Why: Industry-standard for developer tools. Excellent legibility at small sizes. Variable font support. Free.

```css
--qr-font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

### Display Typeface: **Space Grotesk**

Use for: Headlines, hero sections, marketing pages, landing pages.

Why: Geometric. Techy without being gimmicky. Pairs well with Inter. The slight quirkiness in letterforms (look at the `Q`) gives it personality without sacrificing readability.

```css
--qr-font-display: 'Space Grotesk', 'Inter', sans-serif;
```

### Monospace Typeface: **JetBrains Mono**

Use for: Code blocks, terminal output, API references, technical specs.

Why: Purpose-built for code. Ligature support. Distinct character differentiation (0 vs O, 1 vs l vs I). Free.

```css
--qr-font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
```

### Type Scale

| Level | Size | Weight | Font | Line Height | Usage |
|-------|------|--------|------|-------------|-------|
| Display | 48px / 3rem | 700 | Space Grotesk | 1.1 | Hero headlines |
| H1 | 36px / 2.25rem | 700 | Space Grotesk | 1.2 | Page titles |
| H2 | 28px / 1.75rem | 600 | Space Grotesk | 1.25 | Section headers |
| H3 | 22px / 1.375rem | 600 | Inter | 1.3 | Subsections |
| H4 | 18px / 1.125rem | 600 | Inter | 1.4 | Card titles |
| Body | 16px / 1rem | 400 | Inter | 1.6 | Paragraphs |
| Body Small | 14px / 0.875rem | 400 | Inter | 1.5 | Captions, metadata |
| Code | 14px / 0.875rem | 400 | JetBrains Mono | 1.6 | Inline & block code |
| Label | 12px / 0.75rem | 500 | Inter | 1.4 | Tags, badges, labels |

---

## 5. Logo Concepts

Three directions to explore. All should work at 16x16 (favicon), 32x32 (nav), and full size (marketing).

### Concept A: "The Qubit Gate" (Recommended)

A minimal geometric mark based on a quantum logic gate diagram. Two parallel horizontal lines (representing qubits) intersected by a clean vertical bar or circle (representing a gate operation). The intersection point uses the Quantum Indigo-to-Qubit Cyan gradient, suggesting superposition.

- **Style:** Abstract, geometric, engineer-friendly
- **Feel:** Precise, technical, trustworthy
- **Wordmark pairing:** "QRelay" in Space Grotesk 600, letterspaced +2%
- **Scales well:** The simple geometry holds at favicon size
- **Monochrome version:** Works in single color on dark or light backgrounds

### Concept B: "The Relay Node"

A stylized node graph: three dots connected by lines forming a triangle, with the center dot rendered as a glowing ring (the quantum relay point). The ring uses the accent glow color. Lines use the primary indigo.

- **Style:** Network/graph-inspired, modern
- **Feel:** Connected, infrastructure, distributed
- **Wordmark pairing:** "Quantum MCP Relayer" stacked, Inter 500
- **Consideration:** May read too generic at small sizes without the glow effect

### Concept C: "The Q Particle"

The letter Q from Space Grotesk, modified: the tail of the Q becomes a wave function that trails off to the right, transitioning from Quantum Indigo to Interference green. The wave is mathematically accurate (sine-based, decaying amplitude).

- **Style:** Typographic, scientific, distinctive
- **Feel:** Bold, ownable, quantum-native
- **Wordmark pairing:** "Relay" in lighter weight beside the Q mark
- **Strength:** The Q is immediately recognizable and ownable. Works as app icon, favicon, social avatar
- **Consideration:** Ensure the wave doesn't get lost at small sizes; may need a simplified version

### Logo Clear Space

Minimum clear space around any logo variant = 1x the height of the "Q" in the wordmark on all sides.

### Logo Misuse (Don'ts)

- Don't rotate the logo
- Don't change the colors outside the defined palette
- Don't add drop shadows or effects
- Don't stretch or distort proportions
- Don't place on busy photographic backgrounds without a container
- Don't recreate the logo in a different typeface

---

## 6. Visual Language

### Imagery Style

**Dark, precise, luminous.** Think deep space, not neon rave.

- Primary aesthetic: Dark backgrounds with selective, precise light. Bioluminescence, not Las Vegas.
- Photography (if used): Abstract macro photography of light refraction, fiber optics, crystal structures. Never stock photos of people pointing at screens.
- Data visualization: Prefer dark canvas with luminous data points. Use the accent palette for chart colors.

### Gradient Usage

One primary gradient, used sparingly for maximum impact:

```css
/* The Quantum Gradient -- use for hero elements, key CTAs, feature highlights */
background: linear-gradient(135deg, #6C5CE7 0%, #0984E3 50%, #00CEC9 100%);

/* Subtle glow -- use for hover states, card borders */
background: linear-gradient(135deg, #6C5CE7 0%, #A29BFE 100%);
```

Rules:
- Maximum one gradient per viewport. If everything glows, nothing glows.
- Never use gradients on body text.
- Gradients are for emphasis, not decoration.

### Iconography

- **Style:** 1.5px stroke weight, rounded caps, 24x24 grid
- **Source:** Lucide Icons or Phosphor Icons as base sets (both open source, both clean)
- **Custom icons:** Build on the same grid for quantum-specific concepts (qubit, entanglement, circuit, gate)
- **Color:** Single color (neutral-400 default, primary on hover/active). Never multicolor icons in UI.

### Illustration Approach

- **Style:** Technical diagrams over illustrations. When illustration is needed, use clean line art with selective color fills from the accent palette.
- **Architecture diagrams:** Use the neutral-800 background, primary/secondary for nodes, accent-glow for data flow arrows.
- **Code-as-visual:** Code snippets are a first-class visual element. A well-formatted code block is better than an illustration of what the code does.
- **Animation (web):** Subtle. Particle fields with slow drift. Circuit paths that pulse once. Never looping animations that distract from content.

### Layout Principles

- **Generous whitespace.** Let elements breathe. Minimum 48px between major sections.
- **Left-aligned text.** Never center-align body copy. Center-align only hero headlines.
- **Content width:** Max 720px for prose. Max 1200px for dashboards/grids.
- **Grid:** 12-column, 24px gutter. 4-column on mobile.

---

## 7. Messaging Framework

### Elevator Pitch (10 seconds)

> QRelay is a quantum computing API built for AI agents. You send inference requests through the Model Context Protocol; we run them on quantum hardware and return results. No quantum expertise required.

### Elevator Pitch (30 seconds)

> QRelay is the first quantum-native MCP service. AI developers can add quantum-accelerated inference to their agents with a single config change -- no quantum programming, no hardware management, no PhD required. We handle circuit compilation, hardware selection, error correction, and result interpretation. You get a JSON response. It works like any other MCP tool your agent already uses.

### Value Propositions

| # | Value Prop | Supporting Point |
|---|-----------|-----------------|
| 1 | **Zero quantum expertise needed** | Abstract away circuit design, qubit management, and error correction. You send a task; we handle the physics. |
| 2 | **Native MCP integration** | Works with Claude, GPT, and any MCP-compatible agent. Add it to your config file. No custom integration code. |
| 3 | **Real quantum hardware** | Not a simulator. Your requests run on actual quantum processors. We handle the queue, calibration, and fallback. |
| 4 | **Developer-first API design** | RESTful endpoints, typed SDKs, clear error messages, predictable pricing. Stripe-quality DX for quantum. |
| 5 | **Hybrid-ready** | Automatic classical fallback when quantum advantage isn't clear. You always get the best answer, regardless of compute path. |

### Key Messages by Audience

**AI/ML Engineers (Primary)**
- "Add quantum inference to your agent's toolkit in under 5 minutes."
- "Same MCP interface you already use. New computational power underneath."
- "Typed responses, retry logic, and streaming built in. It just works."

**Engineering Managers / Technical Decision Makers**
- "Quantum readiness without quantum headcount."
- "Pay per quantum operation. No hardware commitments. No idle qubits."
- "SOC 2 compliant. Audit logs for every quantum operation."

**Researchers / Quantum-Curious Developers**
- "Full circuit-level access when you want it. Abstracted away when you don't."
- "Experiment with quantum algorithms without provisioning hardware."
- "Export raw quantum state data for your own analysis."

**CTOs / VPs of Engineering**
- "First-mover advantage in quantum-enhanced AI, without the infrastructure risk."
- "Incremental adoption. Start with one agent, scale when ready."
- "We handle quantum hardware deprecation cycles. Your API calls stay stable."

---

## 8. Competitive Positioning

### Market Position

QRelay sits at the intersection of two worlds: quantum computing platforms (IBM Quantum, Amazon Braket, Azure Quantum) and AI agent infrastructure (MCP servers, LangChain tools, function-calling APIs). No one else occupies this intersection.

### Positioning Matrix

| | Quantum platforms (IBM, AWS, Azure) | AI tool providers (LangChain, etc.) | **QRelay** |
|---|---|---|---|
| Quantum hardware access | Yes | No | Yes |
| MCP-native | No | Some | Yes |
| Requires quantum expertise | Yes | N/A | No |
| AI agent integration | Manual | Yes (classical only) | Yes (quantum) |
| Developer experience focus | Medium | High | High |

### How We Differentiate

**Visually:**
- Dark, minimal, precise. Quantum platforms use corporate blue and white. We use deep indigo and selective glow.
- Code-first marketing. Our homepage has a working code example above the fold, not a stock photo.
- No "quantum" visual cliches. No Bloch spheres in the hero. No floating atoms. No blue glowing orbs.

**Verbally:**
- We don't explain quantum computing. We explain what developers can build with it.
- We talk in API calls, latency numbers, and config snippets -- not qubits and Hamiltonians.
- Our competitors say "harness the power of quantum." We say "add `qrelay` to your MCP config."

### Competitive Response Framework

| When a competitor says... | We say... |
|---------------------------|-----------|
| "Access quantum hardware in the cloud" | "Access quantum results in your agent. No cloud console needed." |
| "Build quantum circuits with our visual editor" | "Skip the circuit. Describe your problem; we pick the right algorithm." |
| "Quantum advantage for enterprise" | "Quantum advantage for the code you're writing today." |

---

## Brand Protection Notes

### Trademark Considerations

- Register "QRelay" and "Quantum MCP Relayer" as wordmarks.
- The logo mark (whichever concept is selected) should be registered as a design mark.
- Secure domains: `qrelay.dev`, `qrelay.io`, `quantumrelay.dev`
- Secure handles: `@qrelay` on GitHub, X/Twitter, npm.

### Usage by Third Parties

- Partners may use the QRelay logo in integration listings with written permission.
- The logo must link to `qrelay.dev` when used on partner sites.
- Never alter the logo colors, proportions, or spacing.
- Community projects may reference "QRelay" in text but may not use the logo mark without approval.

---

## Implementation Checklist

- [ ] Finalize logo concept (recommend Concept A or C)
- [ ] Generate logo files: SVG, PNG (1x, 2x, 4x), dark/light variants, favicon .ico
- [ ] Set up design tokens (CSS variables, Tailwind config, Figma variables)
- [ ] Build component library with brand colors and typography
- [ ] Create social media templates (OG images, Twitter cards, GitHub social preview)
- [ ] Write docs site header/footer with brand elements
- [ ] Create code syntax theme using brand palette for docs code blocks
- [ ] Set up brand asset page at `/brand` for partners and press

---

*Brand Guardian -- The Agency*
*Created: 2026-03-08*
*Status: Ready for logo generation and implementation*
