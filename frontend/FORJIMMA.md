# Agent Mission Control — The Full Story

## What Is This Thing?

Imagine you're sitting in a dimly-lit operations room, surrounded by screens showing blinking dots across a map of Europe. Each dot is a surveillance or communications node — some on the ground in major cities, some on ships patrolling sea corridors, some orbiting the Earth. Your job: keep them all talking to each other, spot coverage gaps before they become blind spots, and make split-second decisions when something goes wrong.

That's Agent Mission Control. It's a React-based dashboard that simulates a **G-TT&C (Global Tracking, Telemetry & Command)** system — a military/intelligence-style network operations center. Think of it as a video game HUD for managing a European surveillance network.

---

## The Technical Architecture

### The Stack
- **React 19** + **TypeScript** — the UI framework
- **Vite 6** — blazing-fast bundler (way faster than Webpack)
- **D3.js** + **TopoJSON** — for the geographic map (renders actual world borders from GeoJSON data)
- **Recharts** — for telemetry charts and graphs
- **Tailwind CSS v4** — utility-first styling with the new Vite plugin
- **Lucide React** — clean icon library
- **Motion** (Framer Motion successor) — animations
- **DeepSeek API** — AI chat analyst powered by DeepSeek's `deepseek-chat` model

### How the Pieces Connect

```
App.tsx (root)
├── Sidebar.tsx — navigation between segments + chat toggle
├── Header.tsx — top bar with system status
├── Main content area (switches based on activeSegment):
│   ├── TelemetryGrid.tsx — per-node telemetry cards (DOMESTIC/OVERSEAS/MARITIME/SPACE views)
│   ├── NetworkMap.tsx — node connection visualization
│   ├── GeographicCoverageMap.tsx — D3 Mercator map of Europe with nodes
│   ├── AgentOrchestrator.tsx — AI agent hierarchy view
│   └── SigintPanel.tsx — signals intelligence panel
└── ChatPanel.tsx — slide-out AI analyst chat (right side)
```

**Data flows from `constants.ts`** → all components read from `INITIAL_NODES` (25 network nodes) and `INITIAL_AGENTS` (8 AI agents). There's no backend or database — it's all static data rendered beautifully. The chat panel is the one piece that reaches out to an external API (DeepSeek).

### The Four Segments
The network is divided into military-style segments:
1. **DOMESTIC** — Core Western Europe ground stations (London, Paris, Berlin, etc.)
2. **OVERSEAS** — Extended reach posts at Europe's edges (Warsaw, Istanbul, Athens)
3. **MARITIME** — Ship-based and buoy nodes in sea corridors (North Sea, Mediterranean, Baltic)
4. **SPACE** — Geostationary satellites, polar relays, Arctic ground stations

Each segment has its own sidebar tab, showing filtered telemetry for just those nodes.

---

## Key Technical Decisions & Why

### Why D3 + Mercator (not Leaflet, not Mapbox)?
We needed a map that looks like it belongs in a sci-fi operations center — dark, minimal, no Google Maps chrome. D3 gives us total control over rendering. We fetch world borders from `world-atlas` (TopoJSON) and draw them ourselves. Mercator projection was chosen because it looks "normal" for Europe (Equirectangular was distorting things badly at high zoom).

### Why DeepSeek instead of Gemini?
The project originally had `@google/genai` as a dependency but it was never wired up. DeepSeek was chosen because:
- Their API is OpenAI-compatible (simple `fetch` call, no SDK needed)
- The `deepseek-chat` model is cheap and fast
- No heavy client library — just a 50-line utility file

### Why no backend?
This is a **demo/portfolio piece** deployed to GitHub Pages (static hosting). All "data" is hardcoded in `constants.ts`. The only external call is the optional DeepSeek chat. This keeps deployment dead simple — just `npm run build` and serve the `dist/` folder.

---

## The Bugs We Ran Into (and How We Fixed Them)

### Bug #1: The Map Was Zoomed Into Edinburgh's Backyard
**What happened:** The original map used `geoEquirectangular` projection with `scale(width * 20)` centered on Edinburgh coordinates. This made the map show a ~20km patch of Scotland — completely unrecognizable as a map.

**The fix:** Switched to `geoMercator()`, centered on `[10, 50]` (Central Europe), scale `width * 0.8`. Also had to recalculate coverage circle radii from the old km-to-pixel formula that assumed the insane zoom level.

**Lesson:** When working with D3 geo projections, always start with a sane scale and center, then adjust. A scale of `width * 0.8` with Mercator gives you roughly continent-level view. The scale value is in *pixels per radian* — multiplying by 20 was giving us street-level zoom.

### Bug #2: Coverage Circles Were Invisible at EU Scale
**What happened:** The old nodes had coverage radii of 5-50km, designed for Edinburgh scale. At EU scale, those rendered as sub-pixel dots.

**The fix:** Bumped radii to 80-500km depending on segment type, and adjusted the pixel conversion formula.

### Bug #3: Gemini Dependency Was Dead Weight
**What happened:** `@google/genai` was in `package.json` but never imported anywhere. The Vite config was injecting `GEMINI_API_KEY` into the build but nothing consumed it.

**The fix:** Removed the dependency entirely, replaced the env var with `DEEPSEEK_API_KEY`, and built a lightweight fetch-based client instead of pulling in another SDK.

---

## Lessons for You (The Engineer)

### 1. Projection Math Matters
If you're building anything with maps, spend 30 minutes understanding map projections. Mercator distorts area (Greenland looks huge), but it's intuitive for regional views. Equirectangular is good for global views. The `center` and `scale` parameters are the two knobs you'll tune most.

### 2. Don't Add SDKs When `fetch` Will Do
The DeepSeek integration is literally a single `fetch` call. No SDK, no client library, no abstraction layers. For simple API calls, raw `fetch` is:
- Smaller bundle size
- No version compatibility headaches
- Easier to debug (you can see exactly what's going over the wire)

### 3. Inject Context, Not Just Questions
The chat panel doesn't just send the user's message to DeepSeek — it auto-injects the current dashboard state (how many nodes are online, which ones are degraded, etc.). This is a pattern called **context injection** and it's what makes the AI responses actually useful. Without it, the AI would just give generic answers.

### 4. Static Data is Fine for Demos
Don't over-engineer. This dashboard has no WebSocket feeds, no database, no real-time updates. It's hardcoded data that *looks* real. For a portfolio piece or demo, this is the right call — it deploys anywhere, never breaks because a server went down, and you can iterate on the UI without worrying about backend changes.

### 5. How Good Engineers Think About Scale Changes
When we went from Edinburgh → Europe, we didn't just change the center coordinates. We had to cascade the change through: projection type, scale factor, coverage radii, blind spot locations, node coordinates, and pixel conversion formulas. **A "simple" change in one parameter often requires coordinated changes across 5-6 places.** Good engineers trace the impact of a change before making it.

---

## Deployment

The app deploys to GitHub Pages via a GitHub Actions workflow (`.github/workflows/deploy.yml`):
1. Push to `main` triggers the workflow
2. It runs `npm ci` → `npm run build` (with `DEEPSEEK_API_KEY` from repo secrets)
3. Uploads `dist/` as a Pages artifact
4. Deploys to `https://jreubenim.github.io/Agent-Mission-Control/`

**To enable:**
1. Go to repo Settings → Pages → Source: **GitHub Actions**
2. Go to repo Settings → Secrets → Actions → Add `DEEPSEEK_API_KEY`
3. Push any change (or manually trigger the workflow)

---

## File Map (Quick Reference)

| File | What it does |
|------|-------------|
| `src/constants.ts` | All 25 node definitions + 8 agent definitions |
| `src/types.ts` | TypeScript interfaces (NetworkNode, Agent, SigintEvent) |
| `src/App.tsx` | Root layout — sidebar, header, content switching, chat panel |
| `src/components/GeographicCoverageMap.tsx` | D3 Mercator map of Europe with coverage circles |
| `src/components/ChatPanel.tsx` | AI analyst chat panel (DeepSeek integration) |
| `src/utils/deepseek.ts` | DeepSeek API client (lightweight fetch wrapper) |
| `src/components/Sidebar.tsx` | Navigation sidebar with segment tabs + AI Analyst toggle |
| `src/components/TelemetryGrid.tsx` | Per-node telemetry cards |
| `src/components/NetworkMap.tsx` | Node connection topology visualization |
| `src/components/AgentOrchestrator.tsx` | AI agent hierarchy view |
| `src/components/SigintPanel.tsx` | Signals intelligence panel |
| `vite.config.ts` | Build config (base path, DeepSeek env injection) |
