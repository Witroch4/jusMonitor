'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import Overview from '@/components/prontuario/Overview';
import Timeline from '@/components/prontuario/Timeline';
import Cases from '@/components/prontuario/Cases';
import Automations from '@/components/prontuario/Automations';
import Notes from '@/components/prontuario/Notes';

export default function ProntuarioPage() {
  const params = useParams();
  const clientId = params.id as string;
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="flex-1 p-8 lg:p-12 overflow-y-auto bg-background transition-colors duration-300">
      <div className="mb-6 flex justify-between items-center">
        <button
          onClick={() => window.history.back()}
          className="inline-flex items-center text-accent hover:text-accent/80 text-sm font-medium transition-colors"
        >
          &larr; Voltar
        </button>
      </div>

      <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground tracking-tight">
              Prontuário 360º
            </h1>
            <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider rounded border border-primary/20">
              Visão Completa
            </span>
          </div>
          <p className="text-sm font-medium text-muted-foreground tracking-wide">
            Análise detalhada do cliente e processos
          </p>
        </div>
        <button className="inline-flex items-center px-4 py-2 bg-transparent border border-border/60 shadow-sm rounded-lg hover:bg-muted/30 transition text-sm font-medium text-foreground">
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
          Gerar Relatório / PDF
        </button>
      </header>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Visão Geral</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="cases">Processos</TabsTrigger>
          <TabsTrigger value="automations">Automações</TabsTrigger>
          <TabsTrigger value="notes">Notas</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <Overview clientId={clientId} />
        </TabsContent>

        <TabsContent value="timeline" className="mt-6">
          <Timeline clientId={clientId} />
        </TabsContent>

        <TabsContent value="cases" className="mt-6">
          <Cases clientId={clientId} />
        </TabsContent>

        <TabsContent value="automations" className="mt-6">
          <Automations clientId={clientId} />
        </TabsContent>

        <TabsContent value="notes" className="mt-6">
          <Notes clientId={clientId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
