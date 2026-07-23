import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { askReportQuestion, downloadReportPdf, getChatHistory, getScan, getScanDiff } from '../api/endpoints'
import { SeverityBadge } from '../components/SeverityBadge'
import type { ChatMessage, ScanDetail, ScanDiff } from '../types'

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
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link to={`/targets/${scan.target_id}`} className="text-sm text-slate-400 hover:text-slate-200">
        ← Hedefe don
      </Link>
      <h1 className="mt-2 mb-6 text-2xl font-semibold">Tarama #{scan.id}</h1>

      {scan.status !== 'completed' && (
        <div className="mb-8 rounded-md border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-300">
          {scan.status === 'failed' ? (
            <span className="text-red-400">Tarama basarisiz oldu: {scan.error_message}</span>
          ) : (
            <span>Tarama devam ediyor ({scan.status})... Bu sayfa otomatik guncellenir.</span>
          )}
        </div>
      )}

      {scan.report && (
        <div className="mb-8 rounded-md border border-purple-900 bg-purple-950/20 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium text-purple-300">AI Risk Raporu</h2>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-2 text-xl font-semibold">
                {scan.report.risk_score.toFixed(0)}/100
                {diff?.risk_score_delta != null && diff.risk_score_delta !== 0 && (
                  <span
                    className={`text-sm font-normal ${
                      diff.risk_score_delta > 0 ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    ({diff.risk_score_delta > 0 ? '+' : ''}
                    {diff.risk_score_delta.toFixed(0)})
                  </span>
                )}
              </span>
              <button
                onClick={handleDownload}
                disabled={isDownloading}
                className="rounded-md border border-purple-700 px-3 py-1.5 text-xs font-medium text-purple-300 hover:bg-purple-900/30 disabled:opacity-50"
              >
                {isDownloading ? 'Hazirlaniyor...' : 'PDF indir'}
              </button>
            </div>
          </div>
          <p className="mb-3 text-sm text-slate-200">{scan.report.executive_summary}</p>
          <p className="mb-4 text-sm text-slate-400">{scan.report.technical_summary}</p>

          <div className="flex flex-col gap-3">
            {scan.report.prioritized_findings.map((pf, idx) => (
              <div key={idx} className="rounded-md border border-slate-800 bg-slate-900/60 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <SeverityBadge severity={pf.severity} />
                  <span className="font-medium">{pf.title}</span>
                </div>
                <p className="text-sm text-slate-400">{pf.business_impact}</p>
                <p className="mt-1 text-sm text-emerald-400">Duzeltme: {pf.remediation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {diff && diff.previous_scan_id !== null && (
        <div className="mb-8 rounded-md border border-slate-800 bg-slate-900/50 p-4">
          <h2 className="mb-3 font-medium">
            Onceki taramaya gore degisim
            <span className="ml-2 text-sm font-normal text-slate-500">
              ({new Date(diff.previous_created_at!).toLocaleDateString('tr-TR')} tarihli tarama ile kiyaslandi)
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
                <div key={f.id} className="rounded-md border border-red-900/50 bg-red-950/20 p-2 text-sm">
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
                <div key={f.id} className="rounded-md border border-emerald-900/50 bg-emerald-950/20 p-2 text-sm">
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
          <h2 className="mb-3 font-medium">Ham bulgular ({scan.findings.length})</h2>
          <div className="flex flex-col gap-2">
            {scan.findings.map((f) => (
              <div key={f.id} className="rounded-md border border-slate-800 bg-slate-900/40 p-3 text-sm">
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
          <h2 className="mb-3 font-medium">Rapor hakkinda soru sor</h2>
          <div className="mb-3 flex max-h-80 flex-col gap-2 overflow-y-auto rounded-md border border-slate-800 bg-slate-900/40 p-3">
            {chat.length === 0 && <p className="text-sm text-slate-500">Henuz soru sorulmadi.</p>}
            {chat.map((m) => (
              <div
                key={m.id}
                className={`rounded-md px-3 py-2 text-sm ${
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
              className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-purple-500"
            />
            <button
              type="submit"
              disabled={isAsking}
              className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium hover:bg-purple-500 disabled:opacity-50"
            >
              Sor
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
