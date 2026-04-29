---
name: react-scaffolding
description: Scaffold a complete Vite + React + TypeScript + Tailwind CSS 4 project with consistent patterns. Used by the react-developer subagent.
version: 2.0.0
---

# React Scaffolding

## CRITICAL: Available Tools

You ONLY have access to these filesystem tools:
- `write_file` — Create or overwrite a file (path + content as string)
- `edit_file` — Edit an existing file (find + replace)
- `read_file` — Read file contents
- `ls` — List directory contents
- `glob` — Find files by pattern
- `grep` — Search file contents
- `write_todos` — Update your todo list

You do **NOT** have access to:
- `bash` or shell commands — Do NOT attempt to run `npm`, `npx`, `mkdir`, or any shell command
- `execute` — Sandbox execution is NOT available. You CANNOT run `npm install`, `npm run dev`, or any command

**If you try to call `bash` or `execute`, it will fail with an error.** All project setup must be done via `write_file`.

## CRITICAL: Path Format

ALL file paths MUST use virtual absolute paths starting with `/`:
- CORRECT: `/pomodoro-timer/package.json`
- CORRECT: `/pomodoro-timer/src/App.tsx`
- WRONG: `/Users/scott/.../pomodoro-timer/package.json` (host path — will be sanitized)
- WRONG: `/tmp/pomodoro-timer/package.json` (host path — will be sanitized)
- WRONG: `./pomodoro-timer/package.json` (relative — unreliable)

## CRITICAL: File Rules

1. **JSON files must be valid JSON** — No `//` comments in `.json` files (they're invalid JSON)
2. **No unused imports/variables** — TypeScript strict mode rejects `noUnusedLocals`. Only import and destructure what you actually use
3. **No junk files** — Never create `test.txt`, `.gitkeep`, `test-file.txt`, `test-check.txt`, or any temporary scratch files

## Creating a New Project

Always scaffold into a virtual subdirectory: `/PROJECT-NAME/`.

### Step 1: Write all project files via write_file

Create these files in order:

#### `package.json`
```json
{
  "name": "PROJECT-NAME",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "~5.6.2",
    "vite": "^6.0.5",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0"
  }
}
```

#### `vite.config.ts`
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

#### `tsconfig.json`
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

#### `tsconfig.app.json`
```json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "moduleDetection": "force",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "noEmit": true,
    "skipLibCheck": true,
    "strict": true,
    "target": "ES2020",
    "useDefineForClassFields": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

#### `tsconfig.node.json`
```json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "moduleDetection": "force",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "noEmit": true,
    "skipLibCheck": true,
    "strict": true,
    "target": "ES2020"
  },
  "exclude": ["src"],
  "include": ["vite.config.ts"]
}
```

**IMPORTANT**: Both tsconfig files MUST include `"moduleResolution": "bundler"`. Without it, `tsc -b` will fail on `vite.config.ts` with "Cannot find module 'vite'" errors.

#### `index.html`
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PROJECT-NAME</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

#### `src/index.css`
```css
@import "tailwindcss";
```

#### `src/main.tsx`
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

#### `src/vite-env.d.ts`
```typescript
/// <reference types="vite/client" />
```

#### `src/App.tsx`
```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Components go here */}
    </div>
  )
}
```

### Step 2: Write your components and hooks

Using patterns from the react-component-patterns skill, write all component files.

**IMPORTANT**: When writing a file that already exists (e.g. editing `App.tsx`), use `edit_file` instead of `write_file`. The `write_file` tool will reject overwriting existing files — use `read_file` first, then `edit_file` to make targeted changes.

### Step 3: After all files are written

Report completion to the user with:
1. The project name and directory path
2. A tree of all files created
3. Instructions for the user to run:
   ```bash
   cd /path/to/output/PROJECT-NAME
   npm install
   npm run dev
   ```
4. The dev server URL (typically `http://localhost:5173`)

DO NOT attempt to run these commands yourself. You cannot execute shell commands.

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
    vite-env.d.ts   # Vite types
  index.html
  vite.config.ts
  package.json
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
```

## Common Additional Dependencies

Add these to `package.json` `dependencies` or `devDependencies` as needed:
| Purpose | Package | Section |
|---------|---------|---------|
| Icons | `lucide-react` | dependencies |
| Routing | `react-router-dom` | dependencies |
| State | `zustand` | dependencies |
| Forms | `react-hook-form` | dependencies |
| Date | `date-fns` | dependencies |
| Charts | `recharts` | dependencies |
| Animation | `framer-motion` | dependencies |

## Pitfalls

1. **Never call `bash` or `execute`** — These tools don't exist in your environment. All work is done via `write_file`, `edit_file`, `read_file`.
2. **Never create junk files** — No `test.txt`, `.gitkeep`, `test-check.txt`, scratch files.
3. **Use `edit_file` for modifications** — `write_file` will error on existing files. Read first, then edit.
4. **`moduleResolution: "bundler"`** — Required in both tsconfig files, or `tsc -b` fails.
5. **No unused imports/variables** — TypeScript strict mode with `noUnusedLocals` will reject them.
6. **No `//` comments in JSON** — `package.json` and `tsconfig.json` must be valid JSON.
7. **Tailwind CSS 4 uses `@import "tailwindcss"`** — Not the v3 `@tailwind` directives. No `tailwind.config.js` or `postcss.config.js` needed with v4.