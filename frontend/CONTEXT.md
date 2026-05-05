# Frontend Context — frontend/

## App Structure
4-page SPA (React 19 + Vite):
- Home       → weekly top YouTube videos (from /get/homePage)
- Insights   → all weekly videos with category filter
- YouTube    → manual URL input + analysis display
- App Store  → manual URL input + analysis display

## Patterns (Follow These)
- State management via React hooks (useState, useEffect) — no Redux
- All API calls use Fetch API; backend base URL comes from a config constant (e.g. `import.meta.env.VITE_API_BASE`), never hardcoded
- Components are PascalCase.jsx
- Each page is a top-level component, shared UI in components/

## Patterns to Avoid
- Do NOT add a state management library (Zustand, Redux, etc.)
- Do NOT call the backend from inside child components — lift to page level
- Do NOT hardcode the backend URL — use an env variable or config constant

## Insight Display Rules
- Show severity as a visual scale (1–5)
- Show frequency as a visual scale (1–5)
- Group insights by problem type
- Color-code by type (feature_request, complaint, usability, etc.)