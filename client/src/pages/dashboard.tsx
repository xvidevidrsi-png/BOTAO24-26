import React from 'react';
import { Card, CardContent } from '@/components/ui/card';

export default function Dashboard() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-border/50 bg-card/50">
        <CardContent className="p-12 flex flex-col items-center justify-center text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center">
            <div className="w-8 h-8 rounded-md border-2 border-dashed border-muted-foreground/50" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold tracking-tight">Projeto Limpo</h2>
            <p className="text-sm text-muted-foreground">
              O painel do bot foi removido. O projeto está pronto para uma nova ideia.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
