import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createTarget, deleteTarget, listTargets } from '../api/endpoints'
import type { Target } from '../types'

export function DashboardPage() {
  const [targets, setTargets] = useState<Target[]>([])
  const [domain, setDomain] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  async function refresh() {
    setIsLoading(true)
    try {
      setTargets(await listTargets())
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleAdd(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createTarget(domain.trim())
      setDomain('')
      await refresh()
    } catch {
      setError('Hedef eklenemedi. Domain formatini kontrol edin.')
    }
  }

  async function handleDelete(id: number) {
    await deleteTarget(id)
    await refresh()
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-semibold">Hedefler</h1>

      <form onSubmit={handleAdd} className="mb-8 flex gap-2">
        <input
          required
          placeholder="ornek.com"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-purple-500"
        />
        <button type="submit" className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium hover:bg-purple-500">
          Hedef ekle
        </button>
      </form>
      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {isLoading ? (
        <p className="text-slate-400">Yukleniyor...</p>
      ) : targets.length === 0 ? (
        <p className="text-slate-400">Henuz hedef eklenmedi.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {targets.map((target) => (
            <li
              key={target.id}
              className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/50 px-4 py-3"
            >
              <Link to={`/targets/${target.id}`} className="flex items-center gap-3">
                <span className="font-medium">{target.domain}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    target.is_verified
                      ? 'bg-emerald-950 text-emerald-300'
                      : 'bg-yellow-950 text-yellow-300'
                  }`}
                >
                  {target.is_verified ? 'Dogrulandi' : 'Dogrulama bekliyor'}
                </span>
              </Link>
              <button
                onClick={() => handleDelete(target.id)}
                className="text-sm text-slate-500 hover:text-red-400"
              >
                Sil
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
