'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Send, Bot, User } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function CentralPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        'Olá! Sou o assistente jurídico do JusMonitor. Como posso ajudar você hoje? Posso ajudar com consultas sobre processos, clientes, prazos e muito mais.',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // TODO: Integrate with AI agent endpoint
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content:
          'Funcionalidade de IA em desenvolvimento. Em breve você poderá conversar com nossos agentes inteligentes para obter informações sobre processos, prazos e muito mais.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
      setIsLoading(false)
    }, 1000)
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex h-[calc(100vh-4rem)] flex-col bg-background">
        <div className="flex-none p-6 lg:px-10 border-b border-border/40 bg-muted/10">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-xl text-primary">
              <Bot className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-serif font-bold text-foreground">Central de IA</h1>
                <Badge variant="secondary" className="bg-primary/5 text-primary border-primary/20 tracking-wider">BETA</Badge>
              </div>
              <p className="mt-1.5 text-sm font-medium text-muted-foreground tracking-wide">
                Assistente jurídico inteligente treinado na base de conhecimento do escritório
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 lg:px-10 space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
                  <Bot className="h-5 w-5" />
                </div>
              )}
              <Card
                className={`max-w-[75%] p-5 shadow-sm border-0 ${message.role === 'user'
                  ? 'bg-foreground text-background rounded-2xl rounded-tr-none'
                  : 'bg-white border border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl rounded-tl-none'
                  }`}
              >
                <p className={`text-base leading-relaxed ${message.role === 'user' ? 'text-background/90' : 'text-foreground'}`}>
                  {message.content}
                </p>
                <p
                  className={`mt-3 text-xs font-medium w-full flex ${message.role === 'user' ? 'justify-end text-background/60' : 'justify-start text-muted-foreground'
                    }`}
                >
                  {message.timestamp.toLocaleTimeString('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </Card>
              {message.role === 'user' && (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted/60 text-muted-foreground shadow-sm">
                  <User className="h-5 w-5" />
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
                <Bot className="h-5 w-5" />
              </div>
              <Card className="p-5 border-0 bg-white border border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl rounded-tl-none">
                <div className="flex gap-1.5 items-center h-full">
                  <div className="h-2 w-2 rounded-full bg-primary/40 animate-bounce" />
                  <div className="h-2 w-2 rounded-full bg-primary/40 animate-bounce [animation-delay:0.2s]" />
                  <div className="h-2 w-2 rounded-full bg-primary/40 animate-bounce [animation-delay:0.4s]" />
                </div>
              </Card>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border/40 bg-white p-6 lg:px-10">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="flex gap-4 max-w-4xl mx-auto"
          >
            <Input
              placeholder="Digite sua dúvida ou solicitacão jurídica..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="flex-1 h-12 text-base rounded-xl border-border/60 bg-muted/10 focus-visible:ring-primary/20 transition-all shadow-sm"
            />
            <Button type="submit" disabled={isLoading || !input.trim()} className="h-12 px-6 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground shadow-md transition-all duration-300">
              <Send className="h-5 w-5 mr-2" />
              Enviar
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
