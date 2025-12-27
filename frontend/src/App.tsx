import { useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { FileUploader } from "@/components/FileUploader"
import { DataPreview } from "@/components/DataPreview"
import { CleaningRules } from "@/components/CleaningRules"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  // Estado para orquestar el flujo
  const [datasetId, setDatasetId] = useState<number | null>(null)

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <header className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">CleanSaaS</h1>
            <p className="text-gray-600">
              Data Cleaning SaaS MVP - Limpieza de datos basada en reglas
            </p>
          </header>

          <div className="space-y-8">
            {/* Sección de Subida */}
            <section>
              <FileUploader
                onUploadComplete={(datasetId) => {
                  // El callback ahora recibe el datasetId directamente
                  setDatasetId(datasetId)
                }}
              />
            </section>

            {/* Sección de Preview - Solo visible si hay datasetId */}
            {datasetId && (
              <section>
                <DataPreview datasetId={datasetId} limit={100} />
              </section>
            )}

            {/* Sección de Reglas - Solo visible si hay datasetId */}
            {datasetId && (
              <section>
                <CleaningRules
                  datasetId={datasetId}
                  onExport={(rules) => {
                    console.log("Rules exported:", rules)
                  }}
                />
              </section>
            )}
          </div>
        </div>
      </div>
    </QueryClientProvider>
  )
}

export default App