'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

export default function VerifyEmailPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const { verifyEmail, isLoading } = useAuth()

    const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')
    const [errorMessage, setErrorMessage] = useState('')

    useEffect(() => {
        const token = searchParams.get('token')

        if (!token) {
            setStatus('error')
            setErrorMessage('Token de verificação inválido ou ausente da URL.')
            return
        }

        const verify = async () => {
            try {
                await verifyEmail(token)
                setStatus('success')
                setTimeout(() => router.push('/login'), 3000)
            } catch (err: any) {
                setStatus('error')
                setErrorMessage(err?.response?.data?.detail || 'Erro ao verificar o e-mail. O token pode ser inválido ou expirado.')
            }
        }

        verify()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams])

    return (
        <>
            <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

        .verify-root {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          background: #0B0F19;
          font-family: 'Inter', sans-serif;
          position: relative;
          overflow: hidden;
        }

        .verify-bg-elements {
          position: absolute;
          inset: 0;
          pointer-events: none;
        }

        .verify-bg-blur {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 80vw;
          height: 80vh;
          background: radial-gradient(circle, rgba(212,175,55,0.08) 0%, transparent 70%);
          filter: blur(60px);
        }

        .verify-card {
          position: relative;
          z-index: 10;
          background: rgba(18,18,18,0.6);
          border: 1px solid rgba(255,255,255,0.05);
          backdrop-filter: blur(12px);
          border-radius: 16px;
          padding: 3rem;
          width: 100%;
          max-width: 420px;
          text-align: center;
          animation: fade-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          box-shadow: 0 24px 48px rgba(0,0,0,0.4);
        }

        @keyframes fade-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .verify-icon-wrapper {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 1.5rem;
        }

        .verify-icon-wrapper.success {
          background: rgba(34,197,94,0.1);
          border-color: rgba(34,197,94,0.3);
          color: #4ADE80;
        }

        .verify-icon-wrapper.error {
          background: rgba(239,68,68,0.1);
          border-color: rgba(239,68,68,0.3);
          color: #F87171;
        }

        .verify-icon {
          width: 28px;
          height: 28px;
        }

        .verify-title {
          font-family: 'Playfair Display', serif;
          font-size: 1.5rem;
          font-weight: 700;
          color: #E5E7EB;
          margin-bottom: 0.75rem;
        }

        .verify-desc {
          font-size: 0.95rem;
          line-height: 1.6;
          color: #9CA3AF;
          margin-bottom: 2rem;
        }

        /* Spinner inside wrapper */
        .verify-spinner {
          width: 28px;
          height: 28px;
          border: 3px solid rgba(212,175,55,0.2);
          border-top-color: #D4AF37;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .verify-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.875rem 1.5rem;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 10px;
          background: rgba(255,255,255,0.05);
          color: #E5E7EB;
          font-family: 'Inter', sans-serif;
          font-size: 0.9rem;
          font-weight: 500;
          text-decoration: none;
          transition: all 0.2s ease;
          width: 100%;
          cursor: pointer;
        }

        .verify-btn:hover {
          background: rgba(255,255,255,0.08);
          border-color: rgba(255,255,255,0.15);
        }

        .verify-btn-primary {
          background: linear-gradient(135deg, #D4AF37 0%, #B89650 100%);
          border: none;
          color: #0B0F19;
          font-weight: 600;
        }

        .verify-btn-primary:hover {
          background: linear-gradient(135deg, #E6C24C 0%, #CCAA66 100%);
        }
      `}</style>

            <div className="verify-root">
                <div className="verify-bg-elements">
                    <div className="verify-bg-blur" aria-hidden="true" />
                </div>

                <div className="verify-card">
                    {status === 'verifying' && (
                        <>
                            <div className="verify-icon-wrapper" style={{ borderColor: 'transparent', background: 'transparent' }}>
                                <div className="verify-spinner" />
                            </div>
                            <h1 className="verify-title">Verificando e-mail</h1>
                            <p className="verify-desc">Aguarde um momento enquanto validamos seu cadastro...</p>
                        </>
                    )}

                    {status === 'success' && (
                        <>
                            <div className="verify-icon-wrapper success" style={{ animation: 'fade-up 0.5s ease forwards' }}>
                                <svg className="verify-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                    <polyline points="22 4 12 14.01 9 11.01" />
                                </svg>
                            </div>
                            <h1 className="verify-title">E-mail verificado!</h1>
                            <p className="verify-desc">Sua conta foi ativada com sucesso. Você será redirecionado para o login em instantes.</p>

                            <button onClick={() => router.push('/login')} className="verify-btn verify-btn-primary">
                                Ir para o login
                            </button>
                        </>
                    )}

                    {status === 'error' && (
                        <>
                            <div className="verify-icon-wrapper error">
                                <svg className="verify-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <circle cx="12" cy="12" r="10" />
                                    <line x1="12" y1="8" x2="12" y2="12" />
                                    <line x1="12" y1="16" x2="12.01" y2="16" />
                                </svg>
                            </div>
                            <h1 className="verify-title">Ops! Algo deu errado</h1>
                            <p className="verify-desc">{errorMessage}</p>

                            <button onClick={() => router.push('/login')} className="verify-btn">
                                Voltar para o login
                            </button>
                        </>
                    )}
                </div>
            </div>
        </>
    )
}
