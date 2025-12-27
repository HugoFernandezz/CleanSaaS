import { useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { useVirtualizer } from "@tanstack/react-virtual"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { datasetsApi } from "@/lib/api"

interface DataPreviewProps {
  datasetId: number
  limit?: number
}

export function DataPreview({ datasetId, limit = 100 }: DataPreviewProps) {
  // Query real al endpoint de preview
  const { data: previewData, isLoading, error } = useQuery({
    queryKey: ["dataset-preview", datasetId, limit],
    queryFn: () => datasetsApi.getPreview(datasetId, limit),
    enabled: !!datasetId, // Solo ejecutar si hay datasetId válido
    retry: 2,
  })

  const parentRef = useRef<HTMLDivElement>(null)

  // Virtualización de filas
  const rowVirtualizer = useVirtualizer({
    count: previewData?.rows.length || 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40, // Altura estimada de cada fila
    overscan: 10, // Renderizar 10 filas extra fuera del viewport
  })

  // Virtualización de columnas (si hay muchas columnas)
  const tableColumns = previewData?.columns || []
  const columnVirtualizer = useVirtualizer({
    count: tableColumns.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      // Estimar tamaño según el tipo de columna (heurística simple)
      const colName = tableColumns[index]?.toLowerCase() || ""
      if (colName.includes("email") || colName.includes("mail") || colName.includes("url")) {
        return 250 // Columnas de email/URL necesitan más espacio
      } else if (colName.includes("id") || colName.includes("age") || colName.includes("count")) {
        return 100 // Números pequeños
      } else {
        return 180 // Texto general
      }
    },
    minSize: 100, // Tamaño mínimo para cualquier columna
    horizontal: true,
    overscan: 2,
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Vista Previa de Datos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <p className="text-gray-600">Cargando datos desde el archivo...</p>
            </div>
            {/* Skeleton de tabla */}
            <div className="border border-gray-200 rounded-md overflow-hidden">
              <div className="h-10 bg-gray-100 animate-pulse"></div>
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 border-t border-gray-200 bg-gray-50 animate-pulse"></div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    // Extraer mensaje de error más amigable
    let errorMessage = "Error desconocido al cargar los datos"
    
    // Manejar errores de axios
    if (error && typeof error === "object" && "response" in error) {
      const axiosError = error as { response?: { data?: { detail?: string }; status?: number } }
      if (axiosError.response?.data?.detail) {
        errorMessage = axiosError.response.data.detail
      } else if (axiosError.response?.status === 404) {
        errorMessage = "Dataset no encontrado"
      } else if (axiosError.response?.status === 500) {
        errorMessage = "Error interno del servidor. Por favor, intenta más tarde."
      }
    } else if (error instanceof Error) {
      errorMessage = error.message
    } else if (typeof error === "object" && error !== null && "message" in error) {
      errorMessage = String((error as { message: unknown }).message)
    }

    // Verificar si es un error de red o del servidor
    const isNetworkError = 
      errorMessage.includes("Network Error") || 
      errorMessage.includes("Failed to fetch") ||
      errorMessage.includes("ERR_NETWORK")
    const isNotFound = 
      errorMessage.includes("404") || 
      errorMessage.includes("not found") ||
      errorMessage.includes("no encontrado")

    return (
      <Card>
        <CardHeader>
          <CardTitle>Vista Previa de Datos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-center space-x-2">
              <svg
                className="w-5 h-5 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="font-semibold text-red-800">Error al cargar los datos</p>
            </div>
            <p className="text-sm text-red-700">
              {isNetworkError
                ? "No se pudo conectar con el servidor. Por favor, verifica tu conexión."
                : isNotFound
                ? "El dataset no fue encontrado. Por favor, intenta subir el archivo nuevamente."
                : errorMessage}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Recargar página
            </button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!previewData || !previewData.rows || previewData.rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Vista Previa de Datos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">No hay datos para mostrar</p>
        </CardContent>
      </Card>
    )
  }

  const totalHeight = rowVirtualizer.getTotalSize()
  const totalWidth = columnVirtualizer.getTotalSize()
  const columns = previewData.columns
  const rows = previewData.rows

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vista Previa de Datos</CardTitle>
        <p className="text-sm text-gray-600">
          Mostrando {rows.length} de {previewData.row_count} filas ({previewData.total_columns} columnas) - Virtualizado
        </p>
      </CardHeader>
      <CardContent>
        <div
          ref={parentRef}
          className="border border-gray-200 rounded-md overflow-auto"
          style={{ height: "500px", width: "100%" }}
        >
          <div
            style={{
              height: `${totalHeight}px`,
              width: `${totalWidth}px`,
              position: "relative",
            }}
          >
            {/* Header fijo */}
            <div
              className="sticky top-0 bg-gray-50 border-b border-gray-200 z-10 flex"
              style={{ height: "40px" }}
            >
              {columnVirtualizer.getVirtualItems().map((virtualColumn) => {
                const column = columns[virtualColumn.index]
                return (
                  <div
                    key={virtualColumn.key}
                    className="px-4 py-2 font-semibold text-sm text-gray-700 border-r border-gray-200 truncate overflow-hidden whitespace-nowrap"
                    title={column}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: `${virtualColumn.size}px`,
                      transform: `translateX(${virtualColumn.start}px)`,
                    }}
                  >
                    {column}
                  </div>
                )
              })}
            </div>

            {/* Filas virtualizadas */}
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const row = rows[virtualRow.index]

              return (
                <div
                  key={virtualRow.key}
                  className="flex border-b border-gray-100 hover:bg-gray-50"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start + 40}px)`, // +40 para el header
                  }}
                >
                  {columnVirtualizer.getVirtualItems().map((virtualColumn) => {
                    const column = columns[virtualColumn.index]
                    const value = row[column]
                    const cellValue = value !== null && value !== undefined ? String(value) : ""
                    const displayValue = cellValue || ""

                    return (
                      <div
                        key={virtualColumn.key}
                        className="px-4 py-2 text-sm text-gray-900 border-r border-gray-100 truncate overflow-hidden whitespace-nowrap"
                        title={displayValue}
                        style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          width: `${virtualColumn.size}px`,
                          transform: `translateX(${virtualColumn.start}px)`,
                        }}
                      >
                        {displayValue}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

