import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../api/errors'
import { useAuth } from '../context/AuthContext'

export function RegisterPage() {
  const { register } = useAuth()
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
      await register(email, password)
      navigate('/')
    } catch (err) {
      setError(getErrorMessage(err, 'Kayit basarisiz. Bu e-posta zaten kullaniliyor olabilir.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-65px)] items-center justify-center bg-gradient-to-b from-slate-900 to-slate-950 px-6 py-16">
      <div className="w-full max-w-sm overflow-hidden rounded-2xl bg-slate-50 text-slate-900 shadow-2xl">
        <div className="border-b border-slate-200 bg-slate-100 px-6 py-5">
          <h1 className="text-lg font-semibold">Kayit ol</h1>
          <p className="text-sm text-slate-500">Ucretsiz bir SentraScan hesabi olustur</p>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 p-6">
          <input
            type="email"
            required
            placeholder="E-posta"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Sifre (en az 8 karakter)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-1 rounded-xl bg-purple-600 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-600/30 transition hover:bg-purple-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Kayit olunuyor...' : 'Kayit ol'}
          </button>
          <p className="mt-1 text-center text-sm text-slate-500">
            Zaten hesabin var mi?{' '}
            <Link to="/login" className="font-medium text-purple-600 hover:underline">
              Giris yap
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
