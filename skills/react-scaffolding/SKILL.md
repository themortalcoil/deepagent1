---
name: react-scaffolding
description: Scaffold a complete Vite + React + TypeScript + Tailwind CSS 4 project with consistent patterns.
version: 1.0.0
---

# React Scaffolding

## Creating a New Project

Always scaffold into a subdirectory under `/workspace/` (or the current working directory).

### Step 1: Create Vite project

```bash
npm create vite@latest PROJECT_NAME -- --template react-ts
cd PROJECT_NAME
```

### Step 2: Install core dependencies

```bash
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### Step 3: Configure Tailwind CSS 4

In `vite.config.ts`, add the Tailwind plugin:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['all'],
  },
})
```

In `src/index.css`, replace all content with:

```css
@import "tailwindcss";
```

### Step 4: Clean up template files

Remove:
- `src/App.css`
- `src/assets/` (if empty)
- `public/vite.svg`

Update `src/App.tsx` to a minimal shell:

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Components go here */}
    </div>
  )
}
```

### Step 5: Common additional dependencies

Install as needed based on the app requirements:

| Purpose | Package | Install |
|---------|---------|---------|
| Icons | `lucide-react` | `npm install lucide-react` |
| Routing | `react-router-dom` | `npm install react-router-dom` |
| State | `zustand` | `npm install zustand` |
| Forms | `react-hook-form` | `npm install react-hook-form` |
| Date | `date-fns` | `npm install date-fns` |
| Charts | `recharts` | `npm install recharts` |
| Animation | `framer-motion` | `npm install framer-motion` |

### Step 6: Start dev server

```bash
npm run dev -- --host 0.0.0.0
```

This starts on `http://localhost:5173` (or next available port). The `--host 0.0.0.0` makes it accessible on the network.

## Project Structure Convention

```
project-name/
  src/
    components/     # Reusable UI components
      ui/           # Base primitives (Button, Card, Input, etc.)
    hooks/          # Custom React hooks
    lib/            # Utility functions
    data/           # Mock data files
    App.tsx          # Root component
    main.tsx        # Entry point
    index.css       # Tailwind imports
  index.html
  vite.config.ts
  tailwind.config.ts  # Only needed for Tailwind v3; v4 uses CSS config
  package.json
```