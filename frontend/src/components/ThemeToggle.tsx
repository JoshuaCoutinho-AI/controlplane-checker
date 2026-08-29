import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'

const STORAGE_KEY = 'cpc-theme'

function getInitialIsLight(): boolean {
  if (typeof document === 'undefined') return false
  // index.html's inline script already set this class before paint —
  // just read it back so React's state matches what's on screen.
  return document.documentElement.classList.contains('light')
}

export default function ThemeToggle() {
  const [isLight, setIsLight] = useState(getInitialIsLight)

  useEffect(() => {
    document.documentElement.classList.toggle('light', isLight)
    localStorage.setItem(STORAGE_KEY, isLight ? 'light' : 'dark')
  }, [isLight])

  return (
    <button
      type="button"
      onClick={() => setIsLight((v) => !v)}
      aria-label={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
      title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-hairline bg-panel text-muted transition-all hover:border-brass/50 hover:text-brass hover:shadow-glow active:scale-95"
    >
      {isLight ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  )
}
