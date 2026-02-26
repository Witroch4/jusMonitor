'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import * as auth from '@/lib/auth'
import type { AuthResponse } from '@/lib/auth'

export function useAuth() {
  const router = useRouter()
  const [user, setUser] = useState<AuthResponse['user'] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const storedUser = auth.getUser()
    const token = auth.getToken()
    
    if (storedUser && token) {
      setUser(storedUser)
      setIsAuthenticated(true)
    }
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await auth.login({ email, password })
      setUser(response.user)
      setIsAuthenticated(true)
      
      // Set cookie for middleware
      document.cookie = `auth_token=${response.access_token}; path=/; max-age=86400`
      
      return response
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    auth.logout()
    setUser(null)
    setIsAuthenticated(false)
    
    // Remove cookie
    document.cookie = 'auth_token=; path=/; max-age=0'
    
    router.push('/login')
  }

  return {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
  }
}
