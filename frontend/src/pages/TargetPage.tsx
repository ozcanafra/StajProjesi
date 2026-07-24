import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  createScan,
  getPublicConfig,
  getTarget,
  getVerifyInstructions,
  listScans,
  verifyTarget,
} from '../api/endpoints'
import { AVAILABLE_MODULES, type Scan, type Target, type VerifyInstructions } from '../types'

const MODULE_INFO: Record<string, { label: string; description: string }> = {
  recon: {
    label: 'Recon',
    description: 'Alt alan adi kesfi + acik port taramasi',
  },
  headers_tls: {
    label: 'Header / TLS',
    description: "Guvenlik header'lari, cookie ve sertifika kontrolu",
  },
  webvuln: {
    label: 'Web-Vuln',
    description: 'Eski kutuphane, acik dizin, guvensiz form kontrolu',
  },
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Beklemede',
  running: 'Calisiyor',
  completed: 'Tamamlandi',
  failed: 'Basarisiz',
}

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-yellow-400',
  running: 'bg-yellow-400 animate-pulse',
  completed: 'bg-emerald-400',
  failed: 'bg-red-400',
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
  const [skipVerification, setSkipVerification] = useState(false)

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
    getPublicConfig().then((c) => setSkipVerification(c.skip_target_verification))
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
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 px-6 pt-8 pb-24">
        <div className="mx-auto max-w-4xl">
          <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">
            ← Hedefler
          </Link>
          <div className="mt-4 flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-purple-600/20 text-xl font-bold text-purple-300 ring-1 ring-purple-700/50">
              {target.domain.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-medium tracking-wide text-purple-400 uppercase">Hedef</p>
              <h1 className="text-3xl font-bold text-slate-50 sm:text-4xl">{target.domain}</h1>
            </div>
          </div>
          <p className="mt-4 max-w-2xl text-slate-400">
            Bu hedef icin pasif recon, HTTP guvenlik header/TLS analizi ve web-vuln kontrollerini
            calistirip bulgulari AI ile onceliklendirilmis, remediation onerili bir risk raporuna
            donusturuyoruz.
          </p>
        </div>
      </div>

      {/* Scan card - overlaps the hero */}
      <div className="mx-auto -mt-16 max-w-4xl px-6">
        {!target.is_verified && instructions && (
          <div className="overflow-hidden rounded-2xl bg-slate-50 text-slate-900 shadow-2xl">
            <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-6 py-4">
              <span className="h-2 w-2 rounded-full bg-yellow-500" />
              <h2 className="font-semibold">Sahiplik dogrulamasi gerekli</h2>
            </div>
            <div className="p-6">
              {skipVerification && (
                <div className="mb-4 rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-900">
                  <span className="font-medium">Demo modu aktif.</span> DNS TXT kontrolu atlaniyor,
                  asagidaki butona basman yeterli. Gercek bir domain'in yoksa deneme icin{' '}
                  <code className="rounded bg-white px-1.5 py-0.5 ring-1 ring-purple-200">
                    scanme.nmap.org
                  </code>{' '}
                  kullanabilirsin (Nmap projesinin tarama testleri icin acikca izin verdigi resmi
                  test hedefi).
                </div>
              )}
              <p className="mb-4 text-sm text-slate-600">{instructions.instructions}</p>
              <div className="mb-4 space-y-1 rounded-lg bg-slate-100 p-4 font-mono text-xs text-slate-700">
                <div>
                  <span className="text-slate-400">Kayit adi:</span> {instructions.record_name}
                </div>
                <div>
                  <span className="text-slate-400">Kayit degeri:</span> {instructions.record_value}
                </div>
              </div>
              {verifyError && <p className="mb-3 text-sm text-red-600">{verifyError}</p>}
              <button
                onClick={handleVerify}
                disabled={isVerifying}
                className="w-full rounded-xl bg-slate-900 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50 sm:w-auto sm:px-8"
              >
                {isVerifying ? 'Kontrol ediliyor...' : 'Dogrulamayi kontrol et'}
              </button>
            </div>
          </div>
        )}

        {target.is_verified && (
          <div className="overflow-hidden rounded-2xl bg-slate-50 text-slate-900 shadow-2xl">
            <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-6 py-4">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <h2 className="font-semibold">Yeni tarama baslat</h2>
            </div>
            <div className="p-6">
              <p className="mb-4 text-sm font-medium text-slate-500">Modulleri sec</p>
              <div className="mb-6 grid gap-3 sm:grid-cols-3">
                {AVAILABLE_MODULES.map((module) => {
                  const info = MODULE_INFO[module] ?? { label: module, description: '' }
                  const isSelected = selectedModules.includes(module)
                  return (
                    <button
                      key={module}
                      type="button"
                      onClick={() => toggleModule(module)}
                      className={`rounded-xl border p-4 text-left transition ${
                        isSelected
                          ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-500'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-semibold">{info.label}</span>
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                            isSelected ? 'bg-purple-600 text-white' : 'bg-slate-200 text-transparent'
                          }`}
                        >
                          ✓
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">{info.description}</p>
                    </button>
                  )
                })}
              </div>
              <button
                onClick={handleScan}
                disabled={isScanning || selectedModules.length === 0}
                className="w-full rounded-xl bg-purple-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-purple-600/30 transition hover:bg-purple-500 disabled:opacity-50 sm:w-auto sm:px-8"
              >
                {isScanning ? 'Baslatiliyor...' : 'Taramayi baslat'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Scan history */}
      <div className="mx-auto max-w-4xl px-6 py-10">
        <h2 className="mb-4 font-medium text-slate-200">Tarama gecmisi</h2>
        {scans.length === 0 ? (
          <p className="text-slate-400">Henuz tarama yapilmadi.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {scans.map((scan) => (
              <li key={scan.id}>
                <Link
                  to={`/scans/${scan.id}`}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/50 px-5 py-4 transition hover:border-purple-700 hover:bg-slate-900"
                >
                  <div>
                    <span className="text-sm font-medium text-slate-200">Tarama #{scan.id}</span>
                    <p className="text-xs text-slate-500">
                      {scan.modules.map((m) => MODULE_INFO[m]?.label ?? m).join(' · ')}
                    </p>
                  </div>
                  <span className="flex items-center gap-3 text-sm">
                    {scan.risk_score !== null && (
                      <span className="text-slate-400">Risk: {scan.risk_score.toFixed(0)}</span>
                    )}
                    <span className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${STATUS_DOT[scan.status]}`} />
                      <span className="text-slate-300">{STATUS_LABELS[scan.status]}</span>
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
