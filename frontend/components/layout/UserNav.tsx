'use client'

import Link from 'next/link'
import { User, Settings, CreditCard, Bell, LogOut } from 'lucide-react'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useAuth } from '@/hooks/useAuth'
import { useProfile } from '@/hooks/api/useProfile'
import { useInstagramIntegration } from '@/hooks/api/useIntegrations'

export function UserNav() {
  const { user, logout } = useAuth()
  const { data: profile } = useProfile()
  const { data: instagram } = useInstagramIntegration()

  const displayName = profile?.full_name || user?.full_name || 'Usuário'
  const email = profile?.email || user?.email || ''

  // Avatar priority: custom upload > Instagram profile pic > initials
  const avatarSrc =
    profile?.avatar_url ||
    (instagram?.connected ? instagram.profile_picture_url : undefined) ||
    undefined

  const initials = displayName
    .split(' ')
    .map((w: string) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative h-10 w-10 rounded-full border-2 border-primary ring-offset-background transition-all hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 overflow-hidden flex items-center justify-center">
          <Avatar className="h-full w-full">
            <AvatarImage src={avatarSrc} alt={displayName} />
            <AvatarFallback className="font-serif font-bold text-sm text-primary bg-primary/10">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{displayName}</p>
            <p className="text-xs leading-none text-muted-foreground">{email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild className="cursor-pointer">
            <Link href="/configuracoes?tab=perfil">
              <User className="mr-2 h-4 w-4" />
              <span>Meu Perfil</span>
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild className="cursor-pointer">
            <Link href="/configuracoes?tab=seguranca">
              <Settings className="mr-2 h-4 w-4" />
              <span>Configurações</span>
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild className="cursor-pointer">
            <Link href="/configuracoes?tab=notificacoes">
              <Bell className="mr-2 h-4 w-4" />
              <span>Notificações</span>
            </Link>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={logout}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Sair</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
