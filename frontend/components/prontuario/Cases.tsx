'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { FileText, ExternalLink, Calendar, AlertCircle } from 'lucide-react';
import Link from 'next/link';

interface LegalCase {
  id: string;
  cnj_number: string;
  court: string;
  case_type: string;
  status: string;
  last_movement_date: string;
  next_deadline?: string;
  monitoring_enabled: boolean;
}

interface CasesProps {
  clientId: string;
}

export default function Cases({ clientId }: CasesProps) {
  const [cases, setCases] = useState<LegalCase[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await apiClient.get(`/clients/${clientId}/cases`);
        setCases(response.data.cases || []);
      } catch (error) {
        console.error('Error fetching cases:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, [clientId]);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'ativo':
        return 'bg-green-500';
      case 'pending':
      case 'pendente':
        return 'bg-yellow-500';
      case 'closed':
      case 'encerrado':
        return 'bg-gray-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'Ativo';
      case 'pending':
        return 'Pendente';
      case 'closed':
        return 'Encerrado';
      default:
        return status;
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('pt-BR');
  };

  const isDeadlineNear = (deadline?: string) => {
    if (!deadline) return false;
    const deadlineDate = new Date(deadline);
    const now = new Date();
    const diffDays = Math.ceil((deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return diffDays <= 7 && diffDays >= 0;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processos do Cliente</CardTitle>
          <CardDescription>Carregando processos...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse p-4 border rounded-lg">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processos do Cliente</CardTitle>
        <CardDescription>
          {cases.length} {cases.length === 1 ? 'processo' : 'processos'} cadastrado
          {cases.length !== 1 ? 's' : ''}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Nenhum processo cadastrado para este cliente</p>
          </div>
        ) : (
          <div className="space-y-4">
            {cases.map(legalCase => (
              <div
                key={legalCase.id}
                className="p-4 border rounded-lg hover:bg-accent transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-mono text-sm font-medium">{legalCase.cnj_number}</span>
                      <Badge variant="secondary" className={getStatusColor(legalCase.status)}>
                        {getStatusLabel(legalCase.status)}
                      </Badge>
                      {!legalCase.monitoring_enabled && (
                        <Badge variant="outline">Monitoramento desativado</Badge>
                      )}
                    </div>

                    <div className="space-y-1 text-sm">
                      <p className="text-muted-foreground">
                        <span className="font-medium">Tribunal:</span> {legalCase.court || 'N/A'}
                      </p>
                      <p className="text-muted-foreground">
                        <span className="font-medium">Tipo:</span> {legalCase.case_type || 'N/A'}
                      </p>
                      <p className="text-muted-foreground">
                        <span className="font-medium">Última movimentação:</span>{' '}
                        {formatDate(legalCase.last_movement_date)}
                      </p>
                      {legalCase.next_deadline && (
                        <div className="flex items-center gap-2">
                          <Calendar className="h-3 w-3" />
                          <span className="font-medium">Próximo prazo:</span>
                          <span
                            className={
                              isDeadlineNear(legalCase.next_deadline)
                                ? 'text-red-600 font-medium'
                                : ''
                            }
                          >
                            {formatDate(legalCase.next_deadline)}
                          </span>
                          {isDeadlineNear(legalCase.next_deadline) && (
                            <AlertCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <Link href={`/processos/${legalCase.id}`}>
                    <Button variant="ghost" size="sm">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Ver detalhes
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
