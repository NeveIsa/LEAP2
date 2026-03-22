---
name: talk
display_name: "LEAP2 Lightning Talk"
description: "Lightning talk slides — SIGCSE TS 2026"
author: "Sampad Mohanty"
organization: "University of Southern California"
tags: [talk, slides, demo]
entry_point: slides.html
require_registration: false
pages:
  - {name: "Interact", file: "interact.html"}
  - {name: "Live", file: "live.html"}
---

# LEAP2 Lightning Talk

Slides for the 19th CCSC Southwestern conference lightning talk at UC Riverside (March 28, 2026).

## Features

### Live Audience Demo

The talk itself is a LEAP experiment. During the presentation:

1. **QR slide** — audience scans to open `interact.html` on their phones
2. **Interact page** — audience picks a starting point (x, y) on a 2D plane
3. **Live dashboard** — presenter shows `live.html` with all points appearing in real-time

### Slide Sync

The presenter (admin) controls audience slides. Non-admin viewers who open `slides.html` automatically follow along:

- **Admin**: every slide change pushes the current slide number to the server
- **Audience**: polls every 2 seconds and navigates to the presenter's slide

### Theme Toggle

Press `t` during the presentation to switch between dark and light themes. The theme choice persists in `localStorage` and syncs into embedded iframes (e.g. `live.html`).

### KaTeX Math Rendering

Slides support inline (`$...$`) and display (`$$...$$`) math via KaTeX, rendered automatically on each slide transition.

## Pages

| Page | Description |
|------|-------------|
| `slides.html` | Remark-based slide deck (entry point) |
| `interact.html` | Audience interaction page (pick a point) |
| `live.html` | Real-time dashboard of audience submissions |

## Functions

| Function | Decorators | Description |
|----------|------------|-------------|
| `pick_start(x, y)` | `@noregcheck` | Record a starting point on the 2D plane |
| `set_slide(n)` | `@adminonly @nolog @noregcheck` | Set the current slide number (presenter only) |
| `get_slide()` | `@nolog @noregcheck` | Get the current slide number |

## Setup (day-of)

The QR code URL defaults to `window.location.origin + "/exp/talk/ui/interact.html"`. If running behind a reverse proxy or custom domain, set `INTERACT_URL` in `slides.html` before presenting.
