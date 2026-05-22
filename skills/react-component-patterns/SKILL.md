---
name: react-component-patterns
description: Production-quality React component patterns using Tailwind CSS. Follow these patterns when generating UI components.
version: 1.0.0
---

# React Component Patterns

## Design Principles

1. **Tailwind-first** — Use utility classes, not custom CSS
2. **Composition over configuration** — Small components, composed in pages
3. **TypeScript strict** — Props interfaces for every component
4. **Realistic data** — Never use "Lorem ipsum" or placeholder text
5. **Working interactions** — Every button, toggle, and form must do something (even if mocked with `useState`)
6. **Mobile-first** — Start with mobile layout, add `md:` and `lg:` breakpoints
7. **Accessible** — Use semantic HTML, `aria-*` where needed

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

### Data Table (Simple)

```tsx
interface Column<T> {
  header: string
  accessor: keyof T | ((row: T) => React.ReactNode)
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyFn: (row: T) => string | number
}

export function DataTable<T>({ columns, data, keyFn }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={col.header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {data.map((row) => (
            <tr key={keyFn(row)} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col.header} className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                  {typeof col.accessor === 'function' ? col.accessor(row) : String(row[col.accessor] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

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

Use `lucide-react` for all icons:

```tsx
import { Plus, Search, Settings, ChevronRight } from 'lucide-react'

// Inline
<Plus className="h-4 w-4" />

// With text
<button className="..."><Plus className="mr-2 h-4 w-4" /> Add Item</button>
```