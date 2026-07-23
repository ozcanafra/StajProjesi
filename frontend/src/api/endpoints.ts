import { apiClient } from './client'
import type {
  ChatMessage,
  Scan,
  ScanDetail,
  ScanDiff,
  Target,
  User,
  VerifyInstructions,
} from '../types'

export async function getPublicConfig(): Promise<{ skip_target_verification: boolean }> {
  const { data } = await apiClient.get<{ skip_target_verification: boolean }>('/api/config')
  return data
}

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams()
  form.set('username', email)
  form.set('password', password)
  const { data } = await apiClient.post<{ access_token: string }>('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data.access_token
}

export async function register(email: string, password: string): Promise<User> {
  const { data } = await apiClient.post<User>('/api/auth/register', { email, password })
  return data
}

export async function fetchMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/api/auth/me')
  return data
}

export async function listTargets(): Promise<Target[]> {
  const { data } = await apiClient.get<Target[]>('/api/targets')
  return data
}

export async function createTarget(domain: string): Promise<Target> {
  const { data } = await apiClient.post<Target>('/api/targets', { domain })
  return data
}

export async function getTarget(targetId: number): Promise<Target> {
  const { data } = await apiClient.get<Target>(`/api/targets/${targetId}`)
  return data
}

export async function getVerifyInstructions(targetId: number): Promise<VerifyInstructions> {
  const { data } = await apiClient.get<VerifyInstructions>(`/api/targets/${targetId}/verify-instructions`)
  return data
}

export async function verifyTarget(targetId: number): Promise<Target> {
  const { data } = await apiClient.post<Target>(`/api/targets/${targetId}/verify`)
  return data
}

export async function deleteTarget(targetId: number): Promise<void> {
  await apiClient.delete(`/api/targets/${targetId}`)
}

export async function listScans(targetId: number): Promise<Scan[]> {
  const { data } = await apiClient.get<Scan[]>(`/api/targets/${targetId}/scans`)
  return data
}

export async function createScan(targetId: number, modules: string[]): Promise<Scan> {
  const { data } = await apiClient.post<Scan>(`/api/targets/${targetId}/scans`, { modules })
  return data
}

export async function getScan(scanId: number): Promise<ScanDetail> {
  const { data } = await apiClient.get<ScanDetail>(`/api/scans/${scanId}`)
  return data
}

export async function getScanDiff(scanId: number): Promise<ScanDiff> {
  const { data } = await apiClient.get<ScanDiff>(`/api/scans/${scanId}/diff`)
  return data
}

export async function downloadReportPdf(scanId: number): Promise<void> {
  const response = await apiClient.get(`/api/scans/${scanId}/report.pdf`, { responseType: 'blob' })
  const disposition = response.headers['content-disposition'] as string | undefined
  const match = disposition?.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? `sentrascan-scan-${scanId}.pdf`

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function getChatHistory(scanId: number): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessage[]>(`/api/reports/${scanId}/chat`)
  return data
}

export async function askReportQuestion(scanId: number, question: string): Promise<ChatMessage> {
  const { data } = await apiClient.post<ChatMessage>(`/api/reports/${scanId}/chat`, { question })
  return data
}
