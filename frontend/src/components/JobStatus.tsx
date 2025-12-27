import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { jobsApi, type JobStatusResponse } from "@/lib/api"

interface JobStatusProps {
  jobId: number
  onComplete?: (downloadUrl: string) => void
  onError?: (errorMessage: string) => void
}

export function JobStatus({ jobId, onComplete, onError }: JobStatusProps) {
  // Polling cada 2 segundos mientras el job esté running
  const { data: jobStatus, isLoading, error } = useQuery<JobStatusResponse>({
    queryKey: ["job-status", jobId],
    queryFn: () => jobsApi.getJobStatus(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Hacer polling solo si está running o pending
      return status === "running" || status === "pending" ? 2000 : false
    },
    retry: 3,
  })

  useEffect(() => {
    if (jobStatus?.status === "completed" && jobStatus.download_url) {
      // La URL ya viene correcta del backend con el endpoint público
      onComplete?.(jobStatus.download_url)
    }
    if (jobStatus?.status === "failed") {
      onError?.(jobStatus.error_message || "El procesamiento falló")
    }
  }, [jobStatus, onComplete, onError])

  if (isLoading && !jobStatus) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-gray-600">Cargando estado del job...</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-red-600">Error al obtener el estado del job</p>
        </CardContent>
      </Card>
    )
  }

  if (!jobStatus) {
    return null
  }

  const statusMessages = {
    pending: "Esperando para procesar...",
    running: "Procesando datos...",
    completed: "Procesamiento completado",
    failed: "Procesamiento fallido",
    cancelled: "Procesamiento cancelado",
  }

  const isProcessing = jobStatus.status === "pending" || jobStatus.status === "running"

  return (
    <Card>
      <CardHeader>
        <CardTitle>Estado del Procesamiento</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">
            {statusMessages[jobStatus.status as keyof typeof statusMessages] || jobStatus.status}
          </p>

          {isProcessing && (
            <div className="space-y-2">
              <Progress value={jobStatus.status === "running" ? 50 : 10} />
              <p className="text-xs text-gray-500">
                {jobStatus.status === "pending"
                  ? "El job está en cola..."
                  : "Procesando con Polars (streaming)..."}
              </p>
            </div>
          )}

          {jobStatus.status === "completed" && jobStatus.download_url && (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-800 mb-3">
                  ✓ Los datos han sido limpiados exitosamente
                </p>
                <Button
                  onClick={() => {
                    window.open(jobStatus.download_url!, "_blank")
                  }}
                  size="lg"
                  className="w-full"
                >
                  Descargar Archivo Limpio
                </Button>
              </div>
            </div>
          )}

          {jobStatus.status === "failed" && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800 font-medium mb-1">Error en el procesamiento</p>
              {jobStatus.error_message && (
                <p className="text-xs text-red-600">{jobStatus.error_message}</p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

