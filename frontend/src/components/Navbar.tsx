import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2.5 text-lg font-semibold text-slate-100">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-600 text-sm font-bold text-white">
            S
          </span>
          Sentra<span className="text-purple-400">Scan</span>
        </Link>
        {user && (
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span>{user.email}</span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800"
            >
              Cikis yap
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
