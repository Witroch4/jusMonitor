'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

export default function RegisterPage() {
  const router = useRouter()
  const { register, isLoading } = useAuth()
  
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    firm_name: '',
    oab_number: '',
    oab_state: ''
  })
  
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    try {
      const resp = await register(formData)
      setSuccess(resp?.message || 'Cadastro realizado. Verifique seu e-mail para confirmar a conta.')
      // Optional: automatically redirect to login after some seconds, or leave success message on screen
      setTimeout(() => router.push('/login'), 5000)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ocorreu um erro ao criar a conta. Verifique os dados.')
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
            width: 520px;
            flex-shrink: 0;
            padding: 3rem 4rem;
          }
        }

        .login-right-inner {
          width: 100%;
          max-width: 440px;
          animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes slide-up {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* Mobile logo */
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

        /* Alerts */
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
        }
        
        .login-success {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          background: rgba(34,197,94,0.08);
          border: 1px solid rgba(34,197,94,0.25);
          border-radius: 10px;
          padding: 0.875rem 1rem;
          margin-bottom: 1.5rem;
          font-size: 0.84rem;
          color: #86EFAC;
        }

        .alert-icon {
          flex-shrink: 0;
          width: 18px;
          height: 18px;
          margin-top: 1px;
        }

        /* Field */
        .login-field {
          margin-bottom: 1.25rem;
        }
        
        .login-field-row {
            display: flex;
            gap: 1rem;
        }

        .login-label {
          display: flex;
          justify-content: space-between;
          font-size: 0.78rem;
          font-weight: 500;
          color: #9CA3AF;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-bottom: 0.5rem;
        }
        
        .login-label-optional {
            color: #4B5563;
            text-transform: none;
            letter-spacing: normal;
            font-size: 0.7rem;
        }

        .login-input-wrap {
          position: relative;
        }

        .login-input {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          padding: 0.75rem 1rem;
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
          margin-top: 1rem;
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

        /* Footer */
        .login-form-footer {
          margin-top: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.35rem;
          font-size: 0.85rem;
          color: #6B7280;
        }

        .login-form-footer a {
          color: #D4AF37;
          text-decoration: none;
          transition: opacity 0.2s ease;
          font-weight: 500;
        }

        .login-form-footer a:hover { opacity: 0.8; }
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
            <p className="login-left-eyebrow">Acesso Exclusivo</p>
            <h2 className="login-left-headline">
              Eleve sua prática com<br />
              <span>a plataforma do futuro</span>
            </h2>
            <p className="login-left-desc">
              Junte-se à nova era da advocacia. Automatize demandas repetitivas e foque 
              no que realmente importa: a estratégia jurídica do seu escritório.
            </p>
          </div>

          {/* Footer */}
          <div className="login-left-footer">
            <div className="login-left-footer-text">
              Ambiente 100% seguro
            </div>
            <div className="login-status-dot">Disponibilidade 99.9%</div>
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

            <h1 className="login-form-title">Crie sua conta</h1>
            <p className="login-form-subtitle">
              Cadastre seu escritório e comece a testar
            </p>

            <form onSubmit={handleSubmit} noValidate>
              {error && (
                <div className="login-error" role="alert">
                  <svg className="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {error}
                </div>
              )}
              
              {success && (
                <div className="login-success" role="alert">
                  <svg className="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                     <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                     <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  {success}
                </div>
              )}

              <div className="login-field-row">
                {/* Full Name */}
                <div className="login-field" style={{ flex: 1 }}>
                  <label htmlFor="full_name" className="login-label">Nome Completo</label>
                  <div className="login-input-wrap">
                    <input
                      id="full_name"
                      name="full_name"
                      type="text"
                      required
                      value={formData.full_name}
                      onChange={handleChange}
                      className="login-input"
                      placeholder="João da Silva"
                    />
                  </div>
                </div>
                
                {/* Email */}
                <div className="login-field" style={{ flex: 1 }}>
                  <label htmlFor="email" className="login-label">E-mail</label>
                  <div className="login-input-wrap">
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      autoComplete="email"
                      value={formData.email}
                      onChange={handleChange}
                      className="login-input"
                      placeholder="seu@email.com.br"
                    />
                  </div>
                </div>
              </div>

              {/* Password */}
              <div className="login-field">
                <label htmlFor="password" className="login-label">Senha</label>
                <div className="login-input-wrap">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="new-password"
                    value={formData.password}
                    onChange={handleChange}
                    className="login-input"
                    placeholder="Mínimo de 8 caracteres"
                    minLength={8}
                  />
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

              {/* Firm Name */}
              <div className="login-field">
                <label htmlFor="firm_name" className="login-label">Nome do Escritório</label>
                <div className="login-input-wrap">
                  <input
                    id="firm_name"
                    name="firm_name"
                    type="text"
                    required
                    value={formData.firm_name}
                    onChange={handleChange}
                    className="login-input"
                    placeholder="Silva & Advogados Associados"
                  />
                </div>
              </div>

              <div className="login-field-row">
                {/* OAB */}
                <div className="login-field" style={{ flex: 1.5 }}>
                  <label htmlFor="oab_number" className="login-label">
                    Nº da OAB <span className="login-label-optional">(Opcional)</span>
                  </label>
                  <div className="login-input-wrap">
                    <input
                      id="oab_number"
                      name="oab_number"
                      type="text"
                      value={formData.oab_number}
                      onChange={handleChange}
                      className="login-input"
                      placeholder="Somente N°s"
                    />
                  </div>
                </div>

                {/* OAB State */}
                <div className="login-field" style={{ flex: 1 }}>
                  <label htmlFor="oab_state" className="login-label">
                    Estado <span className="login-label-optional">(UF)</span>
                  </label>
                  <div className="login-input-wrap">
                    <input
                      id="oab_state"
                      name="oab_state"
                      type="text"
                      maxLength={2}
                      value={formData.oab_state}
                      onChange={handleChange}
                      className="login-input"
                      placeholder="SP, RJ..."
                      style={{ textTransform: 'uppercase' }}
                    />
                  </div>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading || !!success}
                className="login-btn"
              >
                {isLoading ? (
                  <>
                    <span className="login-spinner" aria-hidden="true" />
                    Processando...
                  </>
                ) : (
                  <>
                    Criar Conta
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true" style={{marginLeft: '2px'}}>
                      <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            <div className="login-form-footer">
              <span style={{ color: '#9CA3AF'}}>Já possui uma conta?</span>
              <a href="/login">Faça Login</a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
