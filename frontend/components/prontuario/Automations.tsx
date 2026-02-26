'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { Bell, Mail, FileText, Clock, CheckCircle2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Automation {
  id: string;
  type: string;
  enabled: boolean;
  description: string;
}

interface AutomationHistory {
  id: string;
  automation_type: string;
  executed_at: string;
  status: string;
  details?: string;
}

interface AutomationsProps {
  clientId: string;
}

export default function Automations({ clientId }: AutomationsProps) {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [history, setHistory] = useState<AutomationHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchAutomations = async () => {
      try {
        const response = await apiClient.get(`/clients/${clientId}/automations`);
        setAutomations(response.data.automations || []);
        setHistory(response.data.history || []);
      } catch (error) {
        console.error('Error fetching automations:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAutomations();
  }, [clientId]);

  const handleToggle = async (automationType: string, currentValue: boolean) => {
    try {
      await apiClient.put(`/clients/${clientId}/automations`, {
        automation_type: automationType,
        enabled: !currentValue,
      });

      setAutomations(prev =>
        prev.map(auto =>
          auto.type === automationType ? { ...auto, enabled: !currentValue } : auto
        )
      );

      toast({
        title: 'Automação atualizada',
        description: `${!currentValue ? 'Ativada' : 'Desativada'} com sucesso`,
      });
    } catch (error) {
      console.error('Error updating automation:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível atualizar a automação',
        variant: 'destructive',
      });
    }
  };

  const getAutomationIcon = (type: string) => {
    switch (type) {
      case 'briefing_matinal':
        return <Mail className="h-5 w-5" />;
      case 'alertas_urgentes':
        return <Bell className="h-5 w-5" />;
      case 'resumo_semanal':
        return <FileText className="h-5 w-5" />;
      default:
        return <Clock className="h-5 w-5" />;
    }
  };

  const getAutomationTitle = (type: string) => {
    switch (type) {
      case 'briefing_matinal':
        return 'Briefing Matinal';
      case 'alertas_urgentes':
        return 'Alertas Urgentes';
      case 'resumo_semanal':
        return 'Resumo Semanal';
      default:
        return type;
    }
  };

  const getAutomationDescription = (type: string) => {
    switch (type) {
      case 'briefing_matinal':
        return 'Receba um resumo diário das movimentações e atualizações importantes';
      case 'alertas_urgentes':
        return 'Notificações imediatas para movimentações críticas e prazos próximos';
      case 'resumo_semanal':
        return 'Relatório semanal consolidado de todas as atividades do cliente';
      default:
        return 'Automação personalizada';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Automações</CardTitle>
            <CardDescription>Carregando...</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                  <div className="h-6 w-11 bg-gray-200 rounded-full"></div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Default automations if none exist
  const defaultAutomations: Automation[] = [
    {
      id: '1',
      type: 'briefing_matinal',
      enabled: false,
      description: getAutomationDescription('briefing_matinal'),
    },
    {
      id: '2',
      type: 'alertas_urgentes',
      enabled: false,
      description: getAutomationDescription('alertas_urgentes'),
    },
    {
      id: '3',
      type: 'resumo_semanal',
      enabled: false,
      description: getAutomationDescription('resumo_semanal'),
    },
  ];

  const displayAutomations = automations.length > 0 ? automations : defaultAutomations;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Configurar Automações</CardTitle>
          <CardDescription>
            Ative ou desative automações específicas para este cliente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {displayAutomations.map(automation => (
              <div
                key={automation.id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
              >
                <div className="flex items-start gap-4 flex-1">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    {getAutomationIcon(automation.type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium">{getAutomationTitle(automation.type)}</h3>
                      {automation.enabled && (
                        <Badge variant="secondary" className="bg-green-100 text-green-800">
                          Ativo
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {automation.description || getAutomationDescription(automation.type)}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={automation.enabled}
                  onCheckedChange={() => handleToggle(automation.type, automation.enabled)}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Histórico de Automações</CardTitle>
          <CardDescription>Últimas execuções de automações para este cliente</CardDescription>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhuma automação executada ainda</p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map(item => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 border rounded-lg"
                >
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    {item.status === 'success' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      getAutomationIcon(item.automation_type)
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">
                        {getAutomationTitle(item.automation_type)}
                      </span>
                      <Badge
                        variant={item.status === 'success' ? 'secondary' : 'destructive'}
                        className="text-xs"
                      >
                        {item.status === 'success' ? 'Sucesso' : 'Falha'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(item.executed_at)}
                    </p>
                    {item.details && (
                      <p className="text-xs text-muted-foreground mt-1">{item.details}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
