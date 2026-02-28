'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, FileText, Download, CheckCircle, Clock } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';

export default function ContratoDetalhesPage() {
    const router = useRouter();
    const params = useParams();

    // Dados Mockados para o Contrato
    const contrato = {
        id: params.id || 'C-2023-089',
        titulo: 'Contrato de Prestação de Serviços Jurídicos - Compliance Empresarial',
        status: 'Ativo',
        cliente: 'Indústrias Matarazzo S/A',
        valorMensal: 'R$ 15.000,00',
        dataInicio: '15/01/2023',
        dataVencimento: '15/01/2025',
        reajuste: 'IGP-M',
        assinadoPor: 'Dr. Andrade',
        documentoUrl: '#',
        clausulasChave: [
            { titulo: 'Objeto do Contrato', descricao: 'Assessoria contínua em compliance trabalhista e tributário.' },
            { titulo: 'Honorários de Êxito', descricao: '15% sobre o proveito econômico em ações tributárias.' },
            { titulo: 'Rescisão', descricao: 'Aviso prévio de 60 dias sem multa.' }
        ]
    };

    return (
        <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
            <div className="mb-6 flex justify-between items-center">
                <button
                    onClick={() => router.back()}
                    className="inline-flex items-center text-accent hover:text-accent/80 text-sm font-medium transition-colors"
                >
                    <ChevronLeft className="w-4 h-4 mr-1" /> Voltar
                </button>
            </div>

            <header className="flex flex-col md:flex-row md:items-start justify-between mb-8 gap-4 border-b border-border/40 pb-6">
                <div>
                    <div className="flex items-center gap-4 mb-2">
                        <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">
                            {contrato.titulo}
                        </h1>
                    </div>
                    <div className="flex items-center gap-3 mt-3">
                        <Badge className="bg-green-500 hover:bg-green-600 text-white shadow-sm font-medium">
                            {contrato.status}
                        </Badge>
                        <span className="text-sm font-medium text-muted-foreground tracking-wide flex items-center gap-1.5">
                            <FileText className="w-4 h-4" /> {contrato.id}
                        </span>
                    </div>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" className="border-border/60 shadow-sm hover:bg-muted/30">
                        Editar Dados
                    </Button>
                    <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm transition-all duration-300">
                        <Download className="w-4 h-4 mr-2" />
                        Baixar PDF
                    </Button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Left Column: Metadata */}
                <div className="lg:col-span-4 space-y-6">
                    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
                        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                            <CardTitle className="font-serif text-xl tracking-tight text-primary">Resumo Financeiro</CardTitle>
                        </CardHeader>
                        <CardContent className="p-6">
                            <div className="space-y-6">
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Valor Mensal (Fee)</p>
                                    <p className="font-serif font-semibold text-3xl text-foreground">{contrato.valorMensal}</p>
                                </div>
                                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/40">
                                    <div>
                                        <p className="text-xs font-medium text-muted-foreground uppercase">Índice Reajuste</p>
                                        <p className="font-medium text-foreground mt-1">{contrato.reajuste}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs font-medium text-muted-foreground uppercase">Término/Renovação</p>
                                        <p className="font-medium text-foreground mt-1">{contrato.dataVencimento}</p>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
                        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                            <CardTitle className="font-serif text-xl tracking-tight text-primary">Partes do Contrato</CardTitle>
                        </CardHeader>
                        <CardContent className="p-6">
                            <div className="space-y-5">
                                <div>
                                    <p className="text-xs font-medium text-muted-foreground uppercase">Contratante</p>
                                    <p className="font-serif font-semibold text-lg text-foreground mt-1">{contrato.cliente}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-medium text-muted-foreground uppercase">Advogado Responsável (Contratada)</p>
                                    <p className="font-medium text-foreground mt-1">{contrato.assinadoPor}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-medium text-muted-foreground uppercase">Data de Assinatura</p>
                                    <p className="font-medium text-foreground mt-1 flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> {contrato.dataInicio}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Clauses & Details */}
                <div className="lg:col-span-8 space-y-6">
                    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300 h-full flex flex-col">
                        <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
                            <CardTitle className="font-serif text-xl tracking-tight text-primary">Termos e Cláusulas Chave</CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 flex-1">
                            <div className="space-y-6">
                                {contrato.clausulasChave.map((clausula, idx) => (
                                    <div key={idx} className="p-5 border border-border/40 rounded-xl bg-card hover:bg-muted/30 transition-all duration-300 group shadow-sm">
                                        <div className="flex items-start gap-4">
                                            <div className="mt-0.5">
                                                <CheckCircle className="w-5 h-5 text-accent" />
                                            </div>
                                            <div>
                                                <h3 className="font-serif font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{clausula.titulo}</h3>
                                                <p className="text-sm font-medium text-muted-foreground mt-2 leading-relaxed">
                                                    {clausula.descricao}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-8 p-6 bg-primary/5 rounded-xl border border-primary/20 flex items-center justify-between">
                                <div>
                                    <h4 className="font-serif font-semibold text-lg text-primary">Visualizar Documento Original</h4>
                                    <p className="text-sm font-medium text-muted-foreground mt-1">Acesse a via escaneada com assinaturas digitais validadas.</p>
                                </div>
                                <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm">
                                    Abrir Viewer
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>

            </div>
        </div>
    );
}
