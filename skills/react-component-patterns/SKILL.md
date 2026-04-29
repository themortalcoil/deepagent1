---
name: react-component-patterns
description: Production-quality React component patterns using Tailwind CSS 4 and TypeScript strict mode. Follow these patterns when generating UI components.
version: 2.0.0
---

# React Component Patterns

## CRITICAL: TypeScript Strictness

All components must compile cleanly under TypeScript strict mode with `noUnusedLocals`. This means:
- **No unused imports** — Remove any import that isn't referenced in the code
- **No unused destructured variables** — If you destructure `{ foo, bar }` from a hook and only use `foo`, remove `bar`
- **No unused function parameters** — Either use them or prefix with `_` (e.g., `_event`)

Violating these causes `tsc -b` to fail and the entire build breaks.

## CRITICAL: Tool Constraints

You only have filesystem tools (`write_file`, `edit_file`, `read_file`, `ls`, `glob`, `grep`). You CANNOT run shell commands. Do not attempt `bash`, `execute`, `npm`, or any command-line tool.

## CRITICAL: File Rules

- **JSON files must be valid JSON** — No `//` comments in `.json` files
- **No junk files** — Never create `test.txt`, `.gitkeep`, scratch files
- **Use `edit_file` for existing files** — `write_file` will reject overwriting

## Design Principles

1. **Tailwind-first** — Use utility classes with Tailwind CSS 4 (`@import "tailwindcss"` in index.css)
2. **Composition over configuration** — Small components, composed in pages
3. **TypeScript strict** — Props interfaces for every component, no unused variables
4. **Realistic data** — Never use "Lorem ipsum" or placeholder text
5. **Working interactions** — Every button, toggle, and form must do something (even if mocked with `useState`)
6. **Mobile-first** — Start with mobile layout, add `md:` and `lg:` breakpoints
7. **Accessible** — Use semantic HTML, `aria-*` where needed
8. **No external icon libraries by default** — Use inline SVG for icons (keeps dependency count low). Add `lucide-react` only if the project explicitly needs many icons.

## Base Components

### Button

```tsx
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

const variants = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm',
  secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
  ghost: 'text-gray-600 hover:bg-gray-100',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
```

### Card

```tsx
interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: CardProps) {
  return <div className={`p-6 pb-0 ${className}`}>{children}</div>
}

export function CardContent({ children, className = '' }: CardProps) {
  return <div className={`p-6 pt-0 ${className}`}>{children}</div>
}
```

### Input

```tsx
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function Input({ label, error, className = '', id, ...props }: InputProps) {
  return (
    <div className="space-y-1">
      {label && <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>}
      <input
        id={id}
        className={`block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500 ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''} ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
```

### Badge

```tsx
interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  children: React.ReactNode
}

const badgeVariants = {
  default: 'bg-gray-100 text-gray-700',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  error: 'bg-red-50 text-red-700',
  info: 'bg-blue-50 text-blue-700',
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeVariants[variant]}`}>
      {children}
    </span>
  )
}
```

## Layout Patterns

### App Shell (Sidebar + Main)

```tsx
export function AppShell({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-gray-200 md:bg-white">
        {sidebar}
      </aside>
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
```

### Page Header

```tsx
interface PageHeaderProps {
  title: string
  description?: string
  action?: React.ReactNode
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
```

## Hook Patterns

### Timer Hook Example (shows strict TS compliance)

```tsx
import { useState, useEffect, useRef, useCallback } from 'react'

export function useTimer(initialSeconds: number) {
  const [timeRemaining, setTimeRemaining] = useState(initialSeconds)
  const [isRunning, setIsRunning] = useState(false)

  const start = useCallback(() => setIsRunning(true), [])
  const pause = useCallback(() => setIsRunning(false), [])
  const reset = useCallback(() => {
    setIsRunning(false)
    setTimeRemaining(initialSeconds)
  }, [initialSeconds])

  useEffect(() => {
    if (!isRunning || timeRemaining <= 0) return
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsRunning(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [isRunning, timeRemaining])

  const progress = initialSeconds > 0 ? timeRemaining / initialSeconds : 0

  return { timeRemaining, isRunning, progress, start, pause, reset }
}
```

**NOTE**: Only export and destructure what you actually use in the component. If the hook exports `toggleMode` but the component doesn't use it, DON'T destructure it.

## Mock Data Pattern

Always create a `src/data/mock.ts` file with realistic data:

```typescript
// src/data/mock.ts

export interface User {
  id: string
  name: string
  email: string
  avatar: string
  role: 'admin' | 'member' | 'viewer'
  status: 'active' | 'inactive'
  lastSeen: string
}

export const users: User[] = [
  {
    id: '1',
    name: 'Sarah Chen',
    email: 'sarah@example.com',
    avatar: '',
    role: 'admin',
    status: 'active',
    lastSeen: '2 minutes ago',
  },
  // ... more items
]
```

## Icon Usage

Prefer inline SVG for a small number of icons (keeps dependencies minimal):

```tsx
// Inline SVG (preferred for 1-3 icons)
<button className="...">
  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" />
  </svg>
  Play
</button>
```

Use `lucide-react` only when the project needs many different icons:

```tsx
import { Plus, Search, Settings } from 'lucide-react'

<Plus className="h-4 w-4" />
```

## Pitfalls

1. **No unused destructured variables** — `const { foo, bar } = useHook()` where `bar` is never used will break `tsc -b`. Only destructure what you use.
2. **No unused imports** — `import { Foo } from './Foo'` where Foo is never used breaks the build.
3. **`moduleResolution: "bundler"`** — Required in tsconfig for `tsc -b` to resolve `vite.config.ts` modules.
4. **Tailwind v4 uses `@import "tailwindcss"`** — Not `@tailwind base/components/utilities`. No `tailwind.config.js` or `postcss.config.js` needed.