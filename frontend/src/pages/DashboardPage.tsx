import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../api/errors'
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
    } catch (err) {
      setError(getErrorMessage(err, 'Hedef eklenemedi. Domain formatini kontrol edin.'))
    }
  }

  async function handleDelete(id: number) {
    await deleteTarget(id)
    await refresh()
  }

  return (
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 px-6 pt-12 pb-24">
        <div className="mx-auto max-w-4xl">
          <p className="text-sm font-medium tracking-wide text-purple-400 uppercase">SentraScan</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-50 sm:text-4xl">Hedeflerin</h1>
          <p className="mt-3 max-w-2xl text-slate-400">
            Bir domain ekle, sahiplik dogrulamasini tamamla, sonra AI destekli risk raporu ureten
            pasif taramalari baslat.
          </p>
        </div>
      </div>

      {/* Add-target card - overlaps the hero */}
      <div className="mx-auto -mt-16 max-w-4xl px-6">
        <div className="overflow-hidden rounded-2xl bg-slate-50 text-slate-900 shadow-2xl">
          <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-6 py-4">
            <span className="h-2 w-2 rounded-full bg-purple-500" />
            <h2 className="font-semibold">Yeni hedef ekle</h2>
          </div>
          <form onSubmit={handleAdd} className="flex flex-col gap-2 p-6">
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                required
                placeholder="ornek.com"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
              />
              <button
                type="submit"
                className="rounded-xl bg-purple-600 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-600/30 transition hover:bg-purple-500"
              >
                Hedef ekle
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Sadece domain adini yaz (orn. <code className="text-slate-500">ornek.com</code>), basina
              "https://" eklemene gerek yok - eklesen de otomatik temizlenir.
            </p>
          </form>
          {error && <p className="px-6 pb-4 text-sm text-red-600">{error}</p>}
        </div>
      </div>

      {/* Target list */}
      <div className="mx-auto max-w-4xl px-6 py-10">
        <h2 className="mb-4 font-medium text-slate-200">Tum hedefler</h2>
        {isLoading ? (
          <p className="text-slate-400">Yukleniyor...</p>
        ) : targets.length === 0 ? (
          <p className="text-slate-400">Henuz hedef eklenmedi.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {targets.map((target) => (
              <li
                key={target.id}
                className="group relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50 transition hover:border-purple-700 hover:bg-slate-900"
              >
                <Link to={`/targets/${target.id}`} className="block p-5">
                  <div className="mb-2 flex items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-purple-600/20 text-sm font-bold text-purple-300">
                      {target.domain.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate font-medium text-slate-100">{target.domain}</span>
                  </div>
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
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
                  className="absolute top-4 right-4 text-xs text-slate-600 opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                >
                  Sil
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
