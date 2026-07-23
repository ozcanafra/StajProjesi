import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  createScan,
  getTarget,
  getVerifyInstructions,
  listScans,
  verifyTarget,
} from '../api/endpoints'
import { AVAILABLE_MODULES, type Scan, type Target, type VerifyInstructions } from '../types'

const MODULE_LABELS: Record<string, string> = {
  recon: 'Recon (subdomain + port)',
  headers_tls: 'HTTP Header / TLS analiz',
  webvuln: 'Pasif web-vuln (eski JS kutuphanesi, acik dizin, guvensiz form)',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Beklemede',
  running: 'Calisiyor',
  completed: 'Tamamlandi',
  failed: 'Basarisiz',
}

export function TargetPage() {
  const { targetId } = useParams()
  const id = Number(targetId)

  const [target, setTarget] = useState<Target | null>(null)
  const [instructions, setInstructions] = useState<VerifyInstructions | null>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedModules, setSelectedModules] = useState<string[]>([...AVAILABLE_MODULES])
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [isVerifying, setIsVerifying] = useState(false)
  const [isScanning, setIsScanning] = useState(false)

  async function refresh() {
    const [t, s] = await Promise.all([getTarget(id), listScans(id)])
    setTarget(t)
    setScans(s)
    if (!t.is_verified) {
      setInstructions(await getVerifyInstructions(id))
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(() => {
      listScans(id).then(setScans)
    }, 5000)
    return () => clearInterval(interval)
  }, [id])

  async function handleVerify() {
    setIsVerifying(true)
    setVerifyError(null)
    try {
      const t = await verifyTarget(id)
      setTarget(t)
    } catch {
      setVerifyError('TXT kaydi henuz bulunamadi. DNS yayilmasi birkac dakika surebilir.')
    } finally {
      setIsVerifying(false)
    }
  }

  function toggleModule(module: string) {
    setSelectedModules((prev) =>
      prev.includes(module) ? prev.filter((m) => m !== module) : [...prev, module],
    )
  }

  async function handleScan() {
    setIsScanning(true)
    try {
      await createScan(id, selectedModules)
      setScans(await listScans(id))
    } finally {
      setIsScanning(false)
    }
  }

  if (!target) return <div className="p-8 text-slate-400">Yukleniyor...</div>

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">
        ← Hedefler
      </Link>
      <h1 className="mt-2 mb-6 text-2xl font-semibold">{target.domain}</h1>

      {!target.is_verified && instructions && (
        <div className="mb-8 rounded-md border border-yellow-900 bg-yellow-950/30 p-4">
          <h2 className="mb-2 font-medium text-yellow-300">Sahiplik dogrulamasi gerekli</h2>
          <p className="mb-3 text-sm text-slate-300">{instructions.instructions}</p>
          <div className="mb-3 rounded bg-slate-900 p-3 font-mono text-xs">
            <div>Kayit adi: {instructions.record_name}</div>
            <div>Kayit degeri: {instructions.record_value}</div>
          </div>
          {verifyError && <p className="mb-2 text-sm text-red-400">{verifyError}</p>}
          <button
            onClick={handleVerify}
            disabled={isVerifying}
            className="rounded-md bg-yellow-600 px-3 py-1.5 text-sm font-medium hover:bg-yellow-500 disabled:opacity-50"
          >
            {isVerifying ? 'Kontrol ediliyor...' : 'Dogrulamayi kontrol et'}
          </button>
        </div>
      )}

      {target.is_verified && (
        <div className="mb-8 rounded-md border border-slate-800 bg-slate-900/50 p-4">
          <h2 className="mb-3 font-medium">Yeni tarama baslat</h2>
          <div className="mb-3 flex flex-col gap-2">
            {AVAILABLE_MODULES.map((module) => (
              <label key={module} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedModules.includes(module)}
                  onChange={() => toggleModule(module)}
                />
                {MODULE_LABELS[module] ?? module}
              </label>
            ))}
          </div>
          <button
            onClick={handleScan}
            disabled={isScanning || selectedModules.length === 0}
            className="rounded-md bg-purple-600 px-3 py-1.5 text-sm font-medium hover:bg-purple-500 disabled:opacity-50"
          >
            {isScanning ? 'Baslatiliyor...' : 'Tarama baslat'}
          </button>
        </div>
      )}

      <h2 className="mb-3 font-medium">Tarama gecmisi</h2>
      {scans.length === 0 ? (
        <p className="text-slate-400">Henuz tarama yapilmadi.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {scans.map((scan) => (
            <li key={scan.id}>
              <Link
                to={`/scans/${scan.id}`}
                className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/50 px-4 py-3 hover:border-purple-700"
              >
                <span className="text-sm text-slate-300">
                  #{scan.id} · {scan.modules.join(', ')}
                </span>
                <span className="flex items-center gap-3 text-sm">
                  {scan.risk_score !== null && (
                    <span className="text-slate-400">Risk: {scan.risk_score.toFixed(0)}</span>
                  )}
                  <span
                    className={
                      scan.status === 'completed'
                        ? 'text-emerald-400'
                        : scan.status === 'failed'
                          ? 'text-red-400'
                          : 'text-yellow-400'
                    }
                  >
                    {STATUS_LABELS[scan.status]}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
