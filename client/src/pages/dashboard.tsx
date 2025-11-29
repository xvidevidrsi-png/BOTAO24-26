import React, { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { 
  Terminal, 
  Server, 
  Shield, 
  Activity, 
  Play, 
  Square, 
  Wifi,
  Cpu,
  Lock,
  User,
  Globe,
  Settings
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Switch } from '@/components/ui/switch';

// --- Mock Data & Types ---

const botSchema = z.object({
  botName: z.string().min(1, "Bot Name is required"),
  serverAddress: z.string().min(1, "Server Address is required"),
  serverPort: z.string().default("19132"),
  version: z.string().default("Latest"),
  email: z.string().email("Invalid email").optional().or(z.literal('')),
  password: z.string().optional(),
  authType: z.enum(["microsoft", "offline"]),
  autoReconnect: z.boolean().default(true),
});

type BotConfig = z.infer<typeof botSchema>;

// --- Components ---

function StatusIndicator({ status }: { status: 'offline' | 'connecting' | 'online' | 'error' }) {
  const colors = {
    offline: "bg-zinc-600",
    connecting: "bg-yellow-500 animate-pulse",
    online: "bg-green-500 shadow-[0_0_10px_theme(colors.green.500)]",
    error: "bg-red-500"
  };

  const labels = {
    offline: "OFFLINE",
    connecting: "CONECTANDO...",
    online: "ONLINE (AFK)",
    error: "ERRO"
  };

  return (
    <div className="flex items-center gap-2 bg-secondary/50 px-3 py-1 rounded-full border border-border/50">
      <div className={`w-2 h-2 rounded-full ${colors[status]}`} />
      <span className="text-xs font-mono font-bold tracking-wider text-muted-foreground">{labels[status]}</span>
    </div>
  );
}

function LogLine({ timestamp, type, message }: { timestamp: string, type: 'info' | 'warn' | 'error' | 'success', message: string }) {
  const colors = {
    info: "text-blue-400",
    warn: "text-yellow-400",
    error: "text-red-500",
    success: "text-green-400"
  };

  return (
    <div className="font-mono text-xs py-0.5 border-l-2 border-transparent hover:bg-white/5 pl-2">
      <span className="text-zinc-500 mr-2">[{timestamp}]</span>
      <span className={colors[type]}>{message}</span>
    </div>
  );
}

export default function Dashboard() {
  const [status, setStatus] = useState<'offline' | 'connecting' | 'online' | 'error'>('offline');
  const [logs, setLogs] = useState<Array<{timestamp: string, type: 'info' | 'warn' | 'error' | 'success', message: string}>>([]);
  const [serverIp, setServerIp] = useState<string>("Desconhecido");
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const form = useForm<BotConfig>({
    resolver: zodResolver(botSchema),
    defaultValues: {
      botName: "boton",
      serverAddress: "Crias7.aternos.me",
      serverPort: "19132",
      version: "Mais Recente (Bedrock)",
      email: "emanoelfrancisco2706@gmail.com",
      password: "", // Intentionally empty for display security, mocked logic will use it
      authType: "microsoft",
      autoReconnect: true,
    }
  });

  // Auto-scroll logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (type: 'info' | 'warn' | 'error' | 'success', message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, type, message }]);
  };

  const handleStart = async (data: BotConfig) => {
    setStatus('connecting');
    setLogs([]); // Clear logs
    
    addLog('info', `Inicializando Bot: ${data.botName}`);
    addLog('info', `Alvo: ${data.serverAddress}:${data.serverPort}`);
    addLog('info', `Versão: ${data.version}`);
    
    // Simulate connection delay
    setTimeout(() => {
      addLog('info', 'Resolvendo DNS do servidor...');
    }, 800);

    setTimeout(() => {
      addLog('info', `Conectando a ${data.serverAddress}...`);
      setServerIp("192.168.1.105"); // Mock IP capture
      addLog('success', 'IP do Servidor Capturado: 192.168.1.105');
    }, 2000);

    setTimeout(() => {
      addLog('info', 'Autenticando com Microsoft...');
      // Don't actually log the password in a real app log, but mocked here
      addLog('success', 'Autenticação com Sucesso (Xbox Live)');
    }, 4000);

    setTimeout(() => {
      addLog('success', 'Entrou no Jogo com sucesso!');
      addLog('info', 'Gerando no mundo...');
      addLog('info', 'Módulo Anti-AFK ativado: Girando cabeça a cada 5s');
      setStatus('online');
    }, 6000);
  };

  const handleStop = () => {
    addLog('warn', 'Desconectando bot...');
    setStatus('offline');
    addLog('info', 'Bot desconectado.');
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col gap-6 max-w-7xl mx-auto text-foreground">
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Terminal className="w-8 h-8 text-primary" />
            Gerenciador de Bot AFK
          </h1>
          <p className="text-muted-foreground">Minecraft Bedrock Edition • Manutenção 24/7</p>
        </div>
        <div className="flex items-center gap-4">
          <StatusIndicator status={status} />
          <Button variant="outline" size="icon" className="h-9 w-9 rounded-full">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Config */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-primary" />
                Configuração
              </CardTitle>
              <CardDescription>Detalhes do Bot e Servidor</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={form.handleSubmit(handleStart)} className="space-y-4">
                
                <div className="space-y-2">
                  <Label htmlFor="botName">Nome do Bot</Label>
                  <Input 
                    id="botName" 
                    {...form.register("botName")} 
                    className="bg-secondary/50 border-border/50 font-mono text-sm"
                  />
                </div>

                <div className="grid grid-cols-3 gap-2">
                    <div className="col-span-2 space-y-2">
                      <Label htmlFor="serverAddress">Endereço do Servidor</Label>
                      <Input 
                        id="serverAddress" 
                        {...form.register("serverAddress")} 
                        className="bg-secondary/50 border-border/50 font-mono text-sm"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="serverPort">Porta</Label>
                      <Input 
                        id="serverPort" 
                        {...form.register("serverPort")} 
                        className="bg-secondary/50 border-border/50 font-mono text-sm"
                      />
                    </div>
                </div>

                <Separator className="bg-border/50" />

                <div className="space-y-2">
                  <Label htmlFor="email">Email Microsoft</Label>
                  <Input 
                    id="email" 
                    {...form.register("email")} 
                    className="bg-secondary/50 border-border/50 font-mono text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Senha</Label>
                  <Input 
                    id="password" 
                    type="password"
                    {...form.register("password")} 
                    placeholder="••••••••"
                    className="bg-secondary/50 border-border/50 font-mono text-sm"
                  />
                </div>

                 <div className="flex items-center justify-between pt-2">
                  <Label htmlFor="autoReconnect" className="cursor-pointer">Reconexão Automática</Label>
                  <Switch 
                    id="autoReconnect" 
                    checked={form.watch("autoReconnect")}
                    onCheckedChange={(val) => form.setValue("autoReconnect", val)}
                  />
                </div>

                <div className="pt-4 flex gap-2">
                   {status === 'offline' || status === 'error' ? (
                      <Button type="submit" className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-bold">
                        <Play className="w-4 h-4 mr-2" /> INICIAR BOT
                      </Button>
                   ) : (
                      <Button type="button" onClick={handleStop} variant="destructive" className="w-full font-bold">
                        <Square className="w-4 h-4 mr-2" /> PARAR BOT
                      </Button>
                   )}
                </div>

              </form>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
             <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-400" />
                Serviço de Uptime
              </CardTitle>
             </CardHeader>
             <CardContent>
               <div className="flex items-center justify-between bg-secondary/30 p-3 rounded-md border border-border/50">
                  <div className="flex flex-col">
                    <span className="text-xs font-medium">Ping de Manutenção</span>
                    <span className="text-[10px] text-muted-foreground">Ping interno a cada 5 min</span>
                  </div>
                  <Badge variant="secondary" className="text-green-400 bg-green-400/10 border-green-400/20">ATIVO</Badge>
               </div>
               <p className="text-[10px] text-muted-foreground mt-2 text-center">
                 Evita modo de suspensão da plataforma
               </p>
             </CardContent>
          </Card>
        </div>

        {/* Right Column: Status & Logs */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
             <Card className="bg-card/50 border-border/50">
                <CardContent className="p-4 flex flex-col items-center justify-center text-center">
                   <span className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Status</span>
                   <span className={`font-mono font-bold text-lg ${status === 'online' ? 'text-green-400' : 'text-zinc-500'}`}>
                     {status === 'online' ? 'CONECTADO' : 'DESCONECTADO'}
                   </span>
                </CardContent>
             </Card>
             <Card className="bg-card/50 border-border/50">
                <CardContent className="p-4 flex flex-col items-center justify-center text-center">
                   <span className="text-xs text-muted-foreground uppercase tracking-wider mb-1">IP do Servidor</span>
                   <span className="font-mono font-bold text-lg text-foreground">{serverIp}</span>
                </CardContent>
             </Card>
             <Card className="bg-card/50 border-border/50">
                <CardContent className="p-4 flex flex-col items-center justify-center text-center">
                   <span className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Ping</span>
                   <span className="font-mono font-bold text-lg text-blue-400">
                     {status === 'online' ? '45ms' : '--'}
                   </span>
                </CardContent>
             </Card>
             <Card className="bg-card/50 border-border/50">
                <CardContent className="p-4 flex flex-col items-center justify-center text-center">
                   <span className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Edição</span>
                   <span className="font-mono font-bold text-lg text-purple-400">Bedrock</span>
                </CardContent>
             </Card>
          </div>

          {/* Console */}
          <Card className="flex-1 border-border/50 bg-black/40 backdrop-blur-md flex flex-col min-h-[400px]">
            <CardHeader className="border-b border-border/50 py-3">
              <div className="flex items-center justify-between">
                 <div className="flex items-center gap-2">
                   <Terminal className="w-4 h-4 text-muted-foreground" />
                   <span className="text-sm font-mono text-muted-foreground">Saída do Console</span>
                 </div>
                 <Badge variant="outline" className="font-mono text-[10px]">v1.2.0</Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 relative overflow-hidden">
               <div 
                  ref={scrollRef}
                  className="absolute inset-0 overflow-y-auto p-4 font-mono text-sm space-y-1"
               >
                  {logs.length === 0 && (
                    <div className="text-muted-foreground/30 italic text-center mt-20">
                      Pronto para conectar. Aguardando comando...
                    </div>
                  )}
                  {logs.map((log, i) => (
                    <LogLine key={i} {...log} />
                  ))}
               </div>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
