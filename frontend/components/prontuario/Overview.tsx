'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useClient } from '@/hooks/api/useClients';
import { AlertCircle, TrendingUp, FileText, Clock } from 'lucide-react';

interface OverviewProps {
  clientId: string;
}

export default function Overview({ clientId }: OverviewProps) {
  const { data: client, isLoading: loading } = useClient(clientId);

  if (loading) {
    return (
      <div className="grid gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!client) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Cliente não encontrado</p>
        </CardContent>
      </Card>
    );
  }

  const healthScore = client.health_score || 75;
  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="grid gap-6">
      {/* Client Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>{client.full_name}</CardTitle>
          <CardDescription>
            {client.cpf_cnpj && `CPF/CNPJ: ${client.cpf_cnpj}`}
            {client.email && ` • ${client.email}`}
            {client.phone && ` • ${client.phone}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Health Score</p>
              <p className={`text-3xl font-bold ${getHealthColor(healthScore)}`}>
                {healthScore}%
              </p>
            </div>
            <div className="flex-1">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    healthScore >= 80
                      ? 'bg-green-600'
                      : healthScore >= 60
                      ? 'bg-yellow-600'
                      : 'bg-red-600'
                  }`}
                  style={{ width: `${healthScore}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processos Ativos</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{client.active_cases_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              {client.total_cases_count || 0} no total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Última Interação</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {client.last_interaction ? new Date(client.last_interaction).toLocaleDateString() : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {client.last_interaction_type || 'Nenhuma interação'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tendência</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">+12%</div>
            <p className="text-xs text-muted-foreground">vs. mês anterior</p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts and Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Alertas e Recomendações</CardTitle>
          <CardDescription>Ações sugeridas para este cliente</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {client.alerts && client.alerts.length > 0 ? (
              client.alerts.map((alert: any, index: number) => (
                <div key={index} className="flex items-start gap-3 p-3 border rounded-lg">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium">{alert.title}</p>
                    <p className="text-sm text-muted-foreground">{alert.description}</p>
                  </div>
                  <Badge variant={alert.priority === 'high' ? 'destructive' : 'secondary'}>
                    {alert.priority}
                  </Badge>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-3 p-3 border rounded-lg">
                <AlertCircle className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-medium">Tudo em ordem</p>
                  <p className="text-sm text-muted-foreground">
                    Não há alertas ou recomendações no momento
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
