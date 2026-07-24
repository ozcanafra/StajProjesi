import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { askReportQuestion, downloadReportPdf, getChatHistory, getScan, getScanDiff } from '../api/endpoints'
import { SeverityBadge } from '../components/SeverityBadge'
import type { ChatMessage, ScanDetail, ScanDiff } from '../types'

const STATUS_LABELS: Record<string, string> = {
  pending: 'Beklemede',
  running: 'Calisiyor',
  completed: 'Tamamlandi',
  failed: 'Basarisiz',
}

function riskRingColor(score: number): string {
  if (score >= 60) return 'text-red-400 ring-red-500/30'
  if (score >= 30) return 'text-yellow-400 ring-yellow-500/30'
  return 'text-emerald-400 ring-emerald-500/30'
}

export function ScanPage() {
  const { scanId } = useParams()
  const id = Number(scanId)

  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [diff, setDiff] = useState<ScanDiff | null>(null)
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    const s = await getScan(id)
    setScan(s)
    if (s.status === 'completed') {
      setChat(await getChatHistory(id))
      setDiff(await getScanDiff(id))
    }
    if (s.status === 'completed' || s.status === 'failed') {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }

  useEffect(() => {
    refresh()
    pollRef.current = setInterval(refresh, 4000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [id])

  async function handleAsk(e: FormEvent) {
    e.preventDefault()
    if (!question.trim()) return
    setIsAsking(true)
    try {
      const userMsg: ChatMessage = {
        id: Date.now(),
        role: 'user',
        content: question,
        created_at: new Date().toISOString(),
      }
      setChat((prev) => [...prev, userMsg])
      setQuestion('')
      const answer = await askReportQuestion(id, userMsg.content)
      setChat((prev) => [...prev, answer])
    } finally {
      setIsAsking(false)
    }
  }

  async function handleDownload() {
    setIsDownloading(true)
    try {
      await downloadReportPdf(id)
    } finally {
      setIsDownloading(false)
    }
  }

  if (!scan) return <div className="p-8 text-slate-400">Yukleniyor...</div>

  return (
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 px-6 pt-8 pb-24">
        <div className="mx-auto max-w-4xl">
          <Link to={`/targets/${scan.target_id}`} className="text-sm text-slate-400 hover:text-slate-200">
            ← Hedefe don
          </Link>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-6">
            <div>
              <p className="text-sm font-medium tracking-wide text-purple-400 uppercase">Tarama Sonucu</p>
              <h1 className="text-3xl font-bold text-slate-50 sm:text-4xl">Tarama #{scan.id}</h1>
              <p className="mt-2 text-sm text-slate-400">
                {scan.modules.join(' · ')} — {STATUS_LABELS[scan.status]}
              </p>
            </div>
            {scan.report && (
              <div
                className={`flex h-24 w-24 shrink-0 flex-col items-center justify-center rounded-full ring-4 ${riskRingColor(
                  scan.report.risk_score,
                )}`}
              >
                <span className="text-2xl font-bold">{scan.report.risk_score.toFixed(0)}</span>
                <span className="text-[10px] text-slate-400">/100 risk</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mx-auto -mt-16 max-w-4xl px-6">
        {scan.status !== 'completed' && (
          <div className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-300 shadow-xl">
            {scan.status === 'failed' ? (
              <span className="text-red-400">Tarama basarisiz oldu: {scan.error_message}</span>
            ) : (
              <span>Tarama devam ediyor ({scan.status})... Bu sayfa otomatik guncellenir.</span>
            )}
          </div>
        )}

        {scan.report && (
          <div className="overflow-hidden rounded-2xl bg-slate-50 text-slate-900 shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-100 px-6 py-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-purple-500" />
                <h2 className="font-semibold">AI Risk Raporu</h2>
                {diff?.risk_score_delta != null && diff.risk_score_delta !== 0 && (
                  <span
                    className={`text-xs font-medium ${
                      diff.risk_score_delta > 0 ? 'text-red-600' : 'text-emerald-600'
                    }`}
                  >
                    ({diff.risk_score_delta > 0 ? '+' : ''}
                    {diff.risk_score_delta.toFixed(0)} onceki taramaya gore)
                  </span>
                )}
              </div>
              <button
                onClick={handleDownload}
                disabled={isDownloading}
                className="rounded-lg border border-slate-300 bg-white px-4 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-purple-400 hover:text-purple-700 disabled:opacity-50"
              >
                {isDownloading ? 'Hazirlaniyor...' : 'PDF indir'}
              </button>
            </div>
            <div className="p-6">
              <p className="mb-3 text-sm text-slate-700">{scan.report.executive_summary}</p>
              <p className="mb-6 text-sm text-slate-500">{scan.report.technical_summary}</p>

              <p className="mb-3 text-sm font-medium text-slate-500">Onceliklendirilmis bulgular</p>
              <div className="flex flex-col gap-3">
                {scan.report.prioritized_findings.map((pf, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="mb-1 flex items-center gap-2">
                      <SeverityBadge severity={pf.severity} />
                      <span className="font-medium">{pf.title}</span>
                    </div>
                    <p className="text-sm text-slate-500">{pf.business_impact}</p>
                    <p className="mt-1 text-sm text-emerald-700">Duzeltme: {pf.remediation}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Secondary content */}
      <div className="mx-auto max-w-4xl px-6 py-10">
        {diff && diff.previous_scan_id !== null && (
          <div className="mb-8 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <h2 className="mb-3 font-medium text-slate-200">
              Onceki taramaya gore degisim
              <span className="ml-2 text-sm font-normal text-slate-500">
                ({new Date(diff.previous_created_at!).toLocaleDateString('tr-TR')} tarihli tarama ile
                kiyaslandi)
              </span>
            </h2>
            <div className="mb-3 flex gap-4 text-sm">
              <span className="text-red-400">{diff.new_findings.length} yeni bulgu</span>
              <span className="text-emerald-400">{diff.resolved_findings.length} kapatilmis bulgu</span>
              <span className="text-slate-500">{diff.persisting_count} degismeden devam ediyor</span>
            </div>
            {diff.new_findings.length > 0 && (
              <div className="mb-3 flex flex-col gap-2">
                {diff.new_findings.map((f) => (
                  <div key={f.id} className="rounded-lg border border-red-900/50 bg-red-950/20 p-2 text-sm">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={f.severity} />
                      <span className="font-medium">Yeni: {f.title}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {diff.resolved_findings.length > 0 && (
              <div className="flex flex-col gap-2">
                {diff.resolved_findings.map((f) => (
                  <div
                    key={f.id}
                    className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={f.severity} />
                      <span className="font-medium">Kapatildi: {f.title}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {scan.findings.length > 0 && (
          <div className="mb-8">
            <h2 className="mb-3 font-medium text-slate-200">Ham bulgular ({scan.findings.length})</h2>
            <div className="flex flex-col gap-2">
              {scan.findings.map((f) => (
                <div key={f.id} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 text-sm">
                  <div className="mb-1 flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="font-medium">{f.title}</span>
                  </div>
                  <p className="text-slate-400">{f.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {scan.status === 'completed' && (
          <div>
            <h2 className="mb-3 font-medium text-slate-200">Rapor hakkinda soru sor</h2>
            <div className="mb-3 flex max-h-80 flex-col gap-2 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              {chat.length === 0 && <p className="text-sm text-slate-500">Henuz soru sorulmadi.</p>}
              {chat.map((m) => (
                <div
                  key={m.id}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    m.role === 'user' ? 'self-end bg-purple-900/40' : 'self-start bg-slate-800'
                  }`}
                >
                  {m.content}
                </div>
              ))}
            </div>
            <form onSubmit={handleAsk} className="flex gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ornek: en kritik bulguyu nasil duzeltirim?"
                className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-purple-500"
              />
              <button
                type="submit"
                disabled={isAsking}
                className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium hover:bg-purple-500 disabled:opacity-50"
              >
                Sor
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
