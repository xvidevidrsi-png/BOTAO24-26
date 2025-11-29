import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md mx-4">
        <CardContent className="pt-6 flex flex-col items-center text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-gray-100 flex items-center justify-center">
            <div className="h-6 w-6 rounded bg-gray-300" />
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-semibold">Novo Projeto</h1>
            <p className="text-sm text-muted-foreground">
              Ambiente limpo e pronto para começar.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
