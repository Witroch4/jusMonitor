'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { MessageSquare, FileText, Bell, User, Filter } from 'lucide-react';

interface TimelineEvent {
  id: string;
  event_type: string;
  title: string;
  description: string;
  created_at: string;
  metadata?: any;
}

interface TimelineProps {
  clientId: string;
}

export default function Timeline({ clientId }: TimelineProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<string>('all');
  const observerTarget = useRef(null);

  const fetchEvents = useCallback(async (pageNum: number, filterType: string) => {
    try {
      const response = await apiClient.get(`/clients/${clientId}/timeline`, {
        params: {
          page: pageNum,
          limit: 20,
          event_type: filterType !== 'all' ? filterType : undefined,
        },
      });
      
      if (pageNum === 1) {
        setEvents(response.data.events || []);
      } else {
        setEvents(prev => [...prev, ...(response.data.events || [])]);
      }
      
      setHasMore(response.data.has_more || false);
    } catch (error) {
      console.error('Error fetching timeline:', error);
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    setLoading(true);
    setPage(1);
    fetchEvents(1, filter);
  }, [filter, fetchEvents]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          setPage(prev => prev + 1);
          fetchEvents(page + 1, filter);
        }
      },
      { threshold: 1 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current);
      }
    };
  }, [hasMore, loading, page, filter, fetchEvents]);

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'message':
        return <MessageSquare className="h-4 w-4" />;
      case 'case_update':
        return <FileText className="h-4 w-4" />;
      case 'notification':
        return <Bell className="h-4 w-4" />;
      default:
        return <User className="h-4 w-4" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'message':
        return 'bg-blue-500';
      case 'case_update':
        return 'bg-green-500';
      case 'notification':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays < 7) return `${diffDays}d atrás`;
    return date.toLocaleDateString('pt-BR');
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Timeline de Eventos</CardTitle>
              <CardDescription>Histórico cronológico de todas as interações</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant={filter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                Todos
              </Button>
              <Button
                variant={filter === 'message' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('message')}
              >
                Mensagens
              </Button>
              <Button
                variant={filter === 'case_update' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('case_update')}
              >
                Processos
              </Button>
              <Button
                variant={filter === 'notification' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('notification')}
              >
                Notificações
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading && events.length === 0 ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse flex gap-4">
                  <div className="h-10 w-10 bg-gray-200 rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Filter className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhum evento encontrado</p>
            </div>
          ) : (
            <div className="relative">
              <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200"></div>
              <div className="space-y-6">
                {events.map((event, index) => (
                  <div key={event.id} className="relative flex gap-4">
                    <div
                      className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full ${getEventColor(
                        event.event_type
                      )} text-white`}
                    >
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 pb-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium">{event.title}</p>
                          <p className="text-sm text-muted-foreground mt-1">{event.description}</p>
                        </div>
                        <span className="text-xs text-muted-foreground whitespace-nowrap ml-4">
                          {formatDate(event.created_at)}
                        </span>
                      </div>
                      {event.metadata && Object.keys(event.metadata).length > 0 && (
                        <div className="mt-2 flex gap-2">
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <Badge key={key} variant="secondary" className="text-xs">
                              {key}: {String(value)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {hasMore && (
                <div ref={observerTarget} className="py-4 text-center">
                  <div className="animate-pulse text-sm text-muted-foreground">
                    Carregando mais eventos...
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
