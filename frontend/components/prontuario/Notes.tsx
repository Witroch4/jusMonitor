'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { MessageSquare, User, Send, Eye, Edit2, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Note {
  id: string;
  content: string;
  author: {
    id: string;
    name: string;
  };
  mentions: string[];
  created_at: string;
  updated_at?: string;
}

interface NotesProps {
  clientId: string;
}

export default function Notes({ clientId }: NotesProps) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchNotes();
  }, [clientId]);

  const fetchNotes = async () => {
    try {
      const response = await apiClient.get(`/clients/${clientId}/notes`);
      setNotes(response.data.notes || []);
    } catch (error) {
      console.error('Error fetching notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNote = async () => {
    if (!newNote.trim()) return;

    try {
      const mentions = extractMentions(newNote);
      const response = await apiClient.post(`/clients/${clientId}/notes`, {
        content: newNote,
        mentions,
      });

      setNotes(prev => [response.data, ...prev]);
      setNewNote('');
      toast({
        title: 'Nota criada',
        description: 'A nota foi adicionada com sucesso',
      });
    } catch (error) {
      console.error('Error creating note:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível criar a nota',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateNote = async (noteId: string) => {
    if (!editContent.trim()) return;

    try {
      const mentions = extractMentions(editContent);
      const response = await apiClient.put(`/clients/${clientId}/notes/${noteId}`, {
        content: editContent,
        mentions,
      });

      setNotes(prev => prev.map(note => (note.id === noteId ? response.data : note)));
      setEditingId(null);
      setEditContent('');
      toast({
        title: 'Nota atualizada',
        description: 'As alterações foram salvas',
      });
    } catch (error) {
      console.error('Error updating note:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível atualizar a nota',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!confirm('Tem certeza que deseja excluir esta nota?')) return;

    try {
      await apiClient.delete(`/clients/${clientId}/notes/${noteId}`);
      setNotes(prev => prev.filter(note => note.id !== noteId));
      toast({
        title: 'Nota excluída',
        description: 'A nota foi removida com sucesso',
      });
    } catch (error) {
      console.error('Error deleting note:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível excluir a nota',
        variant: 'destructive',
      });
    }
  };

  const extractMentions = (text: string): string[] => {
    const mentionRegex = /@(\w+)/g;
    const matches = text.match(mentionRegex);
    return matches ? matches.map(m => m.substring(1)) : [];
  };

  const renderMarkdown = (text: string) => {
    // Simple markdown rendering - bold and mentions
    let rendered = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/@(\w+)/g, '<span class="text-blue-600 font-medium">@$1</span>');
    return rendered;
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

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Notas Internas</CardTitle>
          <CardDescription>Carregando...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2].map(i => (
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Nova Nota</CardTitle>
          <CardDescription>
            Use **texto** para negrito e @usuario para mencionar alguém
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2 mb-2">
              <Button
                variant={showPreview ? 'outline' : 'default'}
                size="sm"
                onClick={() => setShowPreview(false)}
              >
                <Edit2 className="h-4 w-4 mr-2" />
                Editar
              </Button>
              <Button
                variant={showPreview ? 'default' : 'outline'}
                size="sm"
                onClick={() => setShowPreview(true)}
              >
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </Button>
            </div>

            {showPreview ? (
              <div
                className="min-h-[120px] p-3 border rounded-md bg-muted"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(newNote || '_Nada para visualizar_') }}
              />
            ) : (
              <Textarea
                placeholder="Escreva sua nota aqui... Use @usuario para mencionar e **texto** para negrito"
                value={newNote}
                onChange={e => setNewNote(e.target.value)}
                rows={5}
              />
            )}

            <div className="flex justify-end">
              <Button onClick={handleCreateNote} disabled={!newNote.trim()}>
                <Send className="h-4 w-4 mr-2" />
                Adicionar Nota
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notas Anteriores</CardTitle>
          <CardDescription>
            {notes.length} {notes.length === 1 ? 'nota' : 'notas'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {notes.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhuma nota adicionada ainda</p>
            </div>
          ) : (
            <div className="space-y-4">
              {notes.map(note => (
                <div key={note.id} className="p-4 border rounded-lg">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-full bg-primary/10">
                        <User className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-sm">{note.author.name}</p>
                        <p className="text-xs text-muted-foreground">{formatDate(note.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingId(note.id);
                          setEditContent(note.content);
                        }}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteNote(note.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </div>
                  </div>

                  {editingId === note.id ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editContent}
                        onChange={e => setEditContent(e.target.value)}
                        rows={4}
                      />
                      <div className="flex gap-2 justify-end">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingId(null);
                            setEditContent('');
                          }}
                        >
                          Cancelar
                        </Button>
                        <Button size="sm" onClick={() => handleUpdateNote(note.id)}>
                          Salvar
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div
                        className="text-sm mb-2"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(note.content) }}
                      />
                      {note.mentions && note.mentions.length > 0 && (
                        <div className="flex gap-2 flex-wrap">
                          {note.mentions.map((mention, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              @{mention}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
