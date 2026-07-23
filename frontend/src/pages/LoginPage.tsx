import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Giris basarisiz. E-posta veya sifre hatali.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold">Giris yap</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          type="email"
          required
          placeholder="E-posta"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-purple-500"
        />
        <input
          type="password"
          required
          placeholder="Sifre"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-purple-500"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-purple-600 px-3 py-2 text-sm font-medium hover:bg-purple-500 disabled:opacity-50"
        >
          {isSubmitting ? 'Giris yapiliyor...' : 'Giris yap'}
        </button>
      </form>
      <p className="text-sm text-slate-400">
        Hesabin yok mu?{' '}
        <Link to="/register" className="text-purple-400 hover:underline">
          Kayit ol
        </Link>
      </p>
    </div>
  )
}
