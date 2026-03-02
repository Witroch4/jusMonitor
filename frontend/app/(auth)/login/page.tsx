'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

export default function LoginPage() {
  const router = useRouter()
  const { login, isLoading } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await login(email, password)
      router.push('/dashboard')
    } catch {
      setError('Credenciais inválidas. Verifique seus dados e tente novamente.')
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

        .login-root {
          display: flex;
          min-height: 100vh;
          background: #0B0F19;
          font-family: 'Inter', sans-serif;
        }

        /* ─── LEFT PANEL ─── */
        .login-left {
          display: none;
          position: relative;
          flex: 1;
          background: #121212;
          overflow: hidden;
        }

        @media (min-width: 1024px) {
          .login-left { display: flex; flex-direction: column; justify-content: space-between; padding: 3rem; }
        }

        .login-left-noise {
          position: absolute;
          inset: 0;
          background-image:
            radial-gradient(ellipse 80% 60% at 20% 40%, rgba(212,175,55,0.12) 0%, transparent 60%),
            radial-gradient(ellipse 60% 80% at 80% 80%, rgba(212,175,55,0.06) 0%, transparent 50%);
          pointer-events: none;
        }

        .login-left-grid {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(212,175,55,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(212,175,55,0.04) 1px, transparent 1px);
          background-size: 48px 48px;
          pointer-events: none;
        }

        .login-left-top {
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .login-logo-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          background: linear-gradient(135deg, #D4AF37, #B89650);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          font-weight: 700;
          color: #0B0F19;
          font-family: 'Playfair Display', serif;
          flex-shrink: 0;
        }

        .login-logo-name {
          font-family: 'Playfair Display', serif;
          font-size: 1.25rem;
          font-weight: 700;
          color: #E5E7EB;
          letter-spacing: 0.02em;
        }

        .login-left-center {
          position: relative;
          z-index: 1;
        }

        .login-left-eyebrow {
          font-size: 0.65rem;
          font-weight: 600;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          color: #D4AF37;
          margin-bottom: 1.5rem;
        }

        .login-left-headline {
          font-family: 'Playfair Display', serif;
          font-size: clamp(2rem, 3vw, 2.75rem);
          font-weight: 700;
          line-height: 1.2;
          color: #E5E7EB;
          margin-bottom: 1.5rem;
        }

        .login-left-headline span {
          color: #D4AF37;
        }

        .login-left-desc {
          font-size: 0.95rem;
          line-height: 1.7;
          color: #9CA3AF;
          max-width: 380px;
        }

        /* Metrics grid */
        .login-metrics {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
          margin-top: 3rem;
        }

        .login-metric-card {
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(212,175,55,0.15);
          border-radius: 12px;
          padding: 1.25rem;
          transition: border-color 0.3s ease;
        }

        .login-metric-card:hover {
          border-color: rgba(212,175,55,0.35);
        }

        .login-metric-number {
          font-family: 'Playfair Display', serif;
          font-size: 1.75rem;
          font-weight: 700;
          color: #D4AF37;
          line-height: 1;
        }

        .login-metric-label {
          font-size: 0.72rem;
          color: #6B7280;
          margin-top: 0.35rem;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }

        .login-left-footer {
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .login-left-footer-text {
          font-size: 0.75rem;
          color: #4B5563;
        }

        .login-left-footer-text a {
          color: #D4AF37;
          text-decoration: none;
        }

        .login-status-dot {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.72rem;
          color: #6B7280;
        }

        .login-status-dot::before {
          content: '';
          display: block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #22C55E;
          box-shadow: 0 0 8px rgba(34,197,94,0.6);
          animation: pulse-dot 2s ease-in-out infinite;
        }

        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        /* ─── RIGHT PANEL (FORM) ─── */
        .login-right {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          width: 100%;
          padding: 2rem 1.5rem;
          background: #0B0F19;
          position: relative;
        }

        @media (min-width: 1024px) {
          .login-right {
            width: 480px;
            flex-shrink: 0;
            padding: 3rem 4rem;
          }
        }

        .login-right-inner {
          width: 100%;
          max-width: 400px;
          animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes slide-up {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* Mobile logo (only shows on mobile) */
        .login-mobile-logo {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          margin-bottom: 2.5rem;
        }

        @media (min-width: 1024px) {
          .login-mobile-logo { display: none; }
        }

        .login-form-title {
          font-family: 'Playfair Display', serif;
          font-size: 1.75rem;
          font-weight: 700;
          color: #E5E7EB;
          margin-bottom: 0.5rem;
        }

        .login-form-subtitle {
          font-size: 0.875rem;
          color: #6B7280;
          margin-bottom: 2.5rem;
        }

        /* Error alert */
        .login-error {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.25);
          border-radius: 10px;
          padding: 0.875rem 1rem;
          margin-bottom: 1.5rem;
          font-size: 0.84rem;
          color: #FCA5A5;
          animation: fade-in 0.25s ease-out;
        }

        @keyframes fade-in {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .login-error-icon {
          flex-shrink: 0;
          width: 16px;
          height: 16px;
          margin-top: 1px;
          color: #EF4444;
        }

        /* Field */
        .login-field {
          margin-bottom: 1.25rem;
        }

        .login-label {
          display: block;
          font-size: 0.78rem;
          font-weight: 500;
          color: #9CA3AF;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-bottom: 0.5rem;
        }

        .login-input-wrap {
          position: relative;
        }

        .login-input-icon {
          position: absolute;
          left: 1rem;
          top: 50%;
          transform: translateY(-50%);
          width: 16px;
          height: 16px;
          color: #4B5563;
          pointer-events: none;
          transition: color 0.2s ease;
        }

        .login-input {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          padding: 0.75rem 1rem 0.75rem 2.75rem;
          font-size: 0.9rem;
          color: #E5E7EB;
          outline: none;
          transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
          font-family: 'Inter', sans-serif;
          box-sizing: border-box;
        }

        .login-input::placeholder {
          color: #374151;
        }

        .login-input:focus {
          border-color: rgba(212,175,55,0.5);
          background: rgba(212,175,55,0.04);
          box-shadow: 0 0 0 3px rgba(212,175,55,0.1);
        }

        .login-input:focus + .login-input-icon,
        .login-input-wrap:focus-within .login-input-icon {
          color: #D4AF37;
        }

        /* Password toggle */
        .login-pw-toggle {
          position: absolute;
          right: 1rem;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          cursor: pointer;
          color: #4B5563;
          display: flex;
          align-items: center;
          padding: 0;
          transition: color 0.2s ease;
        }

        .login-pw-toggle:hover { color: #9CA3AF; }

        /* Forgot */
        .login-forgot-row {
          display: flex;
          justify-content: flex-end;
          margin-top: -0.5rem;
          margin-bottom: 1.75rem;
        }

        .login-forgot {
          font-size: 0.78rem;
          color: #D4AF37;
          text-decoration: none;
          opacity: 0.8;
          transition: opacity 0.2s ease;
        }

        .login-forgot:hover { opacity: 1; }

        /* Submit button */
        .login-btn {
          width: 100%;
          padding: 0.875rem 1.5rem;
          border: none;
          border-radius: 10px;
          background: linear-gradient(135deg, #D4AF37 0%, #B89650 100%);
          color: #0B0F19;
          font-family: 'Inter', sans-serif;
          font-size: 0.9rem;
          font-weight: 600;
          letter-spacing: 0.04em;
          cursor: pointer;
          position: relative;
          overflow: hidden;
          transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          box-shadow: 0 4px 24px rgba(212,175,55,0.25);
        }

        .login-btn::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(255,255,255,0.15), transparent);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .login-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 32px rgba(212,175,55,0.4);
        }

        .login-btn:hover:not(:disabled)::before { opacity: 1; }
        .login-btn:active:not(:disabled) { transform: translateY(0); }
        .login-btn:disabled { opacity: 0.55; cursor: not-allowed; }

        /* Spinner */
        .login-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(11,15,25,0.3);
          border-top-color: #0B0F19;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* Divider */
        .login-divider {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin: 2rem 0 1.5rem;
        }

        .login-divider-line {
          flex: 1;
          height: 1px;
          background: rgba(255,255,255,0.06);
        }

        .login-divider-text {
          font-size: 0.72rem;
          color: #4B5563;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        /* Footer */
        .login-form-footer {
          margin-top: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.35rem;
          font-size: 0.75rem;
          color: #4B5563;
        }

        .login-form-footer a {
          color: #D4AF37;
          text-decoration: none;
          transition: opacity 0.2s ease;
        }

        .login-form-footer a:hover { opacity: 0.8; }

        /* Security badge */
        .login-security {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.4rem;
          margin-top: 1rem;
          font-size: 0.7rem;
          color: #374151;
          letter-spacing: 0.05em;
        }
      `}</style>

      <div className="login-root">
        {/* ─── LEFT PANEL ─── */}
        <div className="login-left">
          <div className="login-left-noise" aria-hidden="true" />
          <div className="login-left-grid" aria-hidden="true" />

          {/* Top */}
          <div className="login-left-top">
            <div className="login-logo-icon">J</div>
            <span className="login-logo-name">JusMonitorIA</span>
          </div>

          {/* Center */}
          <div className="login-left-center">
            <p className="login-left-eyebrow">Plataforma Jurídica Premium</p>
            <h2 className="login-left-headline">
              Inteligência artificial para o<br />
              <span>direito moderno</span>
            </h2>
            <p className="login-left-desc">
              Gerencie processos, monitore prazos críticos e obtenha insights
              estratégicos impulsionados por IA — tudo em uma plataforma segura
              e focada em resultados.
            </p>

            <div className="login-metrics">
              {[
                { number: '98%', label: 'Precisão de triagem' },
                { number: '<2s', label: 'Resposta em tempo real' },
                { number: '12k+', label: 'Processos monitorados' },
                { number: 'SOC 2', label: 'Certificação de segurança' },
              ].map((m) => (
                <div key={m.label} className="login-metric-card">
                  <div className="login-metric-number">{m.number}</div>
                  <div className="login-metric-label">{m.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="login-left-footer">
            <div className="login-left-footer-text">
              Powered by <a href="https://witdev.com" target="_blank" rel="noopener noreferrer">witdev.com</a>
            </div>
            <div className="login-status-dot">Todos os sistemas operacionais</div>
          </div>
        </div>

        {/* ─── RIGHT PANEL (FORM) ─── */}
        <div className="login-right">
          <div className="login-right-inner">
            {/* Mobile logo */}
            <div className="login-mobile-logo">
              <div className="login-logo-icon">J</div>
              <span className="login-logo-name">JusMonitorIA</span>
            </div>

            <h1 className="login-form-title">Bem-vindo de volta</h1>
            <p className="login-form-subtitle">
              Acesse sua conta para continuar
            </p>

            <form onSubmit={handleSubmit} noValidate>
              {error && (
                <div className="login-error" role="alert">
                  <svg className="login-error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {error}
                </div>
              )}

              {/* Email */}
              <div className="login-field">
                <label htmlFor="email" className="login-label">E-mail</label>
                <div className="login-input-wrap">
                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="login-input"
                    placeholder="seu@escritorio.com.br"
                  />
                  <svg className="login-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                  </svg>
                </div>
              </div>

              {/* Password */}
              <div className="login-field">
                <label htmlFor="password" className="login-label">Senha</label>
                <div className="login-input-wrap">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="login-input"
                    placeholder="••••••••••••"
                  />
                  <svg className="login-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <button
                    type="button"
                    className="login-pw-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showPassword ? (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Forgot link */}
              <div className="login-forgot-row">
                <a href="#" className="login-forgot">Esqueceu a senha?</a>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="login-btn"
              >
                {isLoading ? (
                  <>
                    <span className="login-spinner" aria-hidden="true" />
                    Autenticando...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" />
                    </svg>
                    Acessar plataforma
                  </>
                )}
              </button>
            </form>

            {/* Security badge */}
            <div className="login-security">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Conexão protegida por TLS 1.3 · SSL 256-bit
            </div>

            <div className="login-form-footer">
              <span>Powered by</span>
              <a href="https://witdev.com" target="_blank" rel="noopener noreferrer">witdev.com</a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
