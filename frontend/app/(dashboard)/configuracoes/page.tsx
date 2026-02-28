'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { User, Bell, Shield, Database, Smartphone } from 'lucide-react';

export default function ConfiguracoesPage() {
    return (
        <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
            <header className="mb-8 border-b border-border/40 pb-6">
                <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">Configurações</h1>
                <p className="mt-2 text-sm font-medium text-muted-foreground tracking-wide">
                    Gerencie suas preferências de conta, segurança e integrações.
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                {/* Sidebar Menu */}
                <div className="lg:col-span-1 space-y-2">
                    <Button variant="ghost" className="w-full justify-start font-serif font-semibold text-lg hover:bg-muted/40 transition-colors bg-muted/20">
                        <User className="mr-3 w-5 h-5 text-primary" /> Perfil
                    </Button>
                    <Button variant="ghost" className="w-full justify-start font-serif font-medium text-lg hover:bg-muted/40 transition-colors text-muted-foreground hover:text-foreground">
                        <Shield className="mr-3 w-5 h-5" /> Segurança
                    </Button>
                    <Button variant="ghost" className="w-full justify-start font-serif font-medium text-lg hover:bg-muted/40 transition-colors text-muted-foreground hover:text-foreground">
                        <Bell className="mr-3 w-5 h-5" /> Notificações
                    </Button>
                    <Button variant="ghost" className="w-full justify-start font-serif font-medium text-lg hover:bg-muted/40 transition-colors text-muted-foreground hover:text-foreground">
                        <Database className="mr-3 w-5 h-5" /> Integrações
                    </Button>
                </div>

                {/* Content Area */}
                <div className="lg:col-span-3 space-y-8">
                    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
                        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                            <CardTitle className="font-serif text-xl tracking-tight text-primary">Informações Pessoais</CardTitle>
                            <CardDescription className="text-sm font-medium">Atualize sua foto e detalhes pessoais aqui.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8">
                            <div className="flex flex-col md:flex-row gap-8 items-start">
                                <div className="flex-none">
                                    <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center border-2 border-primary/20">
                                        <span className="font-serif font-bold text-3xl text-primary">OA</span>
                                    </div>
                                    <Button variant="outline" size="sm" className="mt-4 w-full text-xs font-semibold uppercase tracking-wider shadow-sm">
                                        Alterar Foto
                                    </Button>
                                </div>
                                <div className="flex-1 w-full space-y-5">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Nome Completo</label>
                                            <Input defaultValue="Dr. Otávio de Almeida" className="border-border/60 bg-white shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium" />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">E-mail Corporativo</label>
                                            <Input defaultValue="otavio.almeida@jusmonitor.com.br" type="email" className="border-border/60 bg-white shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium" />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">OAB / Documento</label>
                                            <Input defaultValue="OAB/SP 123.456" className="border-border/60 bg-muted/30 shadow-sm cursor-not-allowed text-muted-foreground font-medium" disabled />
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Telefone</label>
                                            <Input defaultValue="(11) 98765-4321" className="border-border/60 bg-white shadow-sm focus-visible:ring-primary/20 rounded-lg text-foreground font-medium" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden bg-card">
                        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                            <CardTitle className="font-serif text-xl tracking-tight text-primary">Preferências de Visualização</CardTitle>
                        </CardHeader>
                        <CardContent className="p-8">
                            <div className="flex items-center justify-between p-4 border border-border/40 rounded-xl bg-muted/5">
                                <div className="space-y-1">
                                    <h4 className="font-serif font-semibold text-lg text-foreground">Tema Escuro (Dark Mode)</h4>
                                    <p className="text-sm font-medium text-muted-foreground">Ative para uma experiência mais confortável em ambientes de baixa luminosidade.</p>
                                </div>
                                <div className="relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full bg-muted transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                                    {/* Decorative Mock Toggle */}
                                    <span className="pointer-events-none absolute mx-auto h-4 w-9 rounded-full bg-muted-foreground transition-colors duration-200 ease-in-out" />
                                    <span className="pointer-events-none absolute left-0 inline-block h-5 w-5 translate-x-0 transform rounded-full border border-gray-200 bg-white shadow ring-0 transition-transform duration-200 ease-in-out" />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="flex justify-end gap-4 mt-8">
                        <Button variant="ghost" className="font-semibold text-muted-foreground hover:text-foreground">
                            Cancelar
                        </Button>
                        <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm px-8">
                            Salvar Alterações
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
