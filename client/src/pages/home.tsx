export default function Home() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md mx-4 bg-white rounded-lg shadow p-6 text-center">
        <div className="h-12 w-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
          <div className="h-6 w-6 rounded bg-gray-300" />
        </div>
        <h1 className="text-xl font-semibold">Novo Projeto</h1>
        <p className="text-sm text-muted-foreground mt-2">
          Ambiente limpo e pronto para começar.
        </p>
      </div>
    </div>
  );
}
