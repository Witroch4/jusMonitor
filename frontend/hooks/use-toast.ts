import { useState } from 'react';

interface Toast {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = (toast: Toast) => {
    setToasts(prev => [...prev, toast]);
    // Simple console log for now - in production, this would show a toast UI
    console.log('Toast:', toast);
    setTimeout(() => {
      setToasts(prev => prev.slice(1));
    }, 3000);
  };

  return { toast, toasts };
}
