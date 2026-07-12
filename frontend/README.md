# WealthMitra frontend

Vite + React + TypeScript (strict) + Tailwind CSS v4 + shadcn/ui.

Design tokens live in `src/styles/tokens.css` — the single source of truth
for color, spacing, and typography across every surface.

Routes: `/` command center · `/app` customer · `/rm` RM desk · `/channels` omni-channels · `/present` presenter.

- `npm run dev` — dev server; proxies `/api` and `/ws` to `http://localhost:8000`.
- `npm run build` — typecheck (`tsc -b`) + production build to `dist/` (served by the FastAPI backend).
