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
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Prontuário 360º</h1>
        <p className="text-muted-foreground">Visão completa do cliente</p>
      </div>

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
