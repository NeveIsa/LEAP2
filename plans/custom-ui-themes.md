# Custom UI Themes

## Context

LEAP2 ships a default theme (`leap/ui/shared/theme.css`) with the "Laboratory Editorial" aesthetic — warm academic tones, DM Sans / Fraunces typography, and a fixed set of CSS custom properties. All built-in pages (landing, 404, readme, logs, students, functions) consume this theme via `/static/` served from `leap/ui/shared/`.

Instructors and lab authors currently have no way to customize the look and feel of LEAP's built-in dashboard pages. Supporting custom themes would let labs match institutional branding or experiment-specific visual identities without forking the LEAP codebase.

## Design

### Convention

If a `ui/` folder exists at the root of a lab directory, its files serve as the lab's custom theme. Files inside the lab's `ui/` folder override the corresponding files in LEAP's built-in `leap/ui/shared/` directory by filename. Any file not overridden falls back to the default.

```
my-lab/
├── README.md
├── ui/                    # ← custom theme folder
│   ├── theme.css          # overrides leap/ui/shared/theme.css
│   ├── navbar.js          # overrides leap/ui/shared/navbar.js
│   ├── footer.js          # overrides leap/ui/shared/footer.js
│   └── logo.svg           # additional asset (served alongside defaults)
├── experiment-1/
│   └── ...
└── experiment-2/
    └── ...
```

### Resolution order

When serving a static asset from `/static/<filename>`:

1. **Lab-level `ui/` folder** (`<lab_root>/ui/<filename>`) — highest priority
2. **Package default** (`leap/ui/shared/<filename>`) — fallback

This mirrors the existing `ui_dir()` resolution in `config.py`, which already checks for a project-level `ui/` directory before falling back to the package default.

### What can be customized

- **`theme.css`** — CSS custom properties (colors, fonts, radii, shadows), additional styles
- **`navbar.js`** / **`footer.js`** — custom navigation and footer components
- **`landing/index.html`** — custom landing page (already supported via `ui_dir()`)
- **`404.html`** — custom error page (already supported)
- **Any additional assets** — images, fonts, extra JS/CSS files referenced by custom overrides

### Theme CSS contract

Custom `theme.css` files should define the same CSS custom properties as the default theme to ensure built-in pages render correctly:

```css
:root {
  --color-bg: ...;
  --color-surface: ...;
  --color-primary: ...;
  --color-primary-hover: ...;
  --color-primary-light: ...;
  --color-primary-rgb: ...;
  --color-accent: ...;
  --color-accent-light: ...;
  --color-text: ...;
  --color-text-muted: ...;
  --color-border: ...;
  --color-success: ...;
  --color-error: ...;
  --color-error-bg: ...;
  --color-warning: ...;
  --color-warning-bg: ...;
  --radius: ...;
  --radius-lg: ...;
  --shadow-sm: ...;
  --shadow: ...;
  --shadow-md: ...;
  --shadow-lg: ...;
  --font-sans: ...;
  --font-display: ...;
}
```

Omitting a variable is safe — the browser will use the property's fallback or inherited value — but may produce visual inconsistencies.

## Changes

### 1. `leap/main.py` — layered static file mounting

Currently, `/static` is mounted directly to `leap/ui/shared/`. Change this to serve from the lab's `ui/` folder first, falling back to the package default. Two approaches:

**Option A — mount order**: Mount the lab `ui/` folder on `/static` *before* the package `shared/` mount. Starlette's `StaticFiles` returns 404 for missing files, so a catch-all fallback mount handles the rest. This requires a custom ASGI middleware or a merged static handler.

**Option B — merged directory** (preferred): Create a lightweight `MergedStaticFiles` class that checks the lab `ui/` directory first, then falls back to `leap/ui/shared/`. This keeps a single `/static` mount point and avoids path conflicts.

```python
class MergedStaticFiles:
    """Serve static files from multiple directories with priority ordering."""

    def __init__(self, directories: list[Path]):
        self.directories = directories

    async def __call__(self, scope, receive, send):
        path = scope["path"].lstrip("/")
        for directory in self.directories:
            candidate = directory / path
            if candidate.is_file():
                # serve from this directory
                ...
```

### 2. `leap/main.py` — detect lab `ui/` folder at startup

At startup, check if `<lab_root>/ui/` exists. If it does, log that a custom theme was detected and use it as the primary static directory.

```python
lab_ui = resolved_root / "ui"
if lab_ui.is_dir():
    logger.info("Custom UI theme detected at %s", lab_ui)
```

### 3. `leap/config.py` — no changes needed

`ui_dir()` already resolves project-level `ui/` over the package default. The static serving changes in `main.py` will leverage this existing logic.

### 4. Documentation

Add a section to the lab authoring guide explaining:
- How to create a `ui/` folder in the lab root
- Which files can be overridden
- The CSS custom property contract
- Examples of common customizations (school colors, logo swap)

## Files

- `leap/main.py` — layered static file serving with lab `ui/` priority
- `leap/ui/shared/theme.css` — document the CSS custom property contract (comments)

## Verification

1. **No custom theme**: Lab without a `ui/` folder → default theme served as before
2. **CSS-only override**: Lab with `ui/theme.css` → custom colors/fonts apply, all other shared assets fall back to defaults
3. **Full override**: Lab with `ui/theme.css`, `ui/navbar.js`, `ui/footer.js` → all three customized
4. **Additional assets**: Lab with `ui/logo.svg` → accessible at `/static/logo.svg`
5. **Missing variable**: Custom `theme.css` omits `--color-accent` → pages degrade gracefully
6. **Hot reload**: Changing a file in `ui/` reflects on next page load (no server restart needed, since `StaticFiles` reads from disk)
