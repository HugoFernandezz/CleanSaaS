import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { filesApi, type PresignedUrlRequest } from "@/lib/api"

interface FileUploaderProps {
  projectId?: number | null
  onUploadComplete?: (datasetId: number) => void
}

export function FileUploader({ projectId, onUploadComplete }: FileUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle")

  // Mutación para obtener presigned URL
  const presignedUrlMutation = useMutation({
    mutationFn: (data: PresignedUrlRequest) => filesApi.getPresignedUrl(data),
  })

  // Función para subir archivo directamente a S3
  const uploadToS3 = async (file: File, url: string, fields: Record<string, string>) => {
    return new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      // Trackear progreso
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100
          setUploadProgress(percentComplete)
        }
      })

      xhr.addEventListener("load", () => {
        console.log("XHR load event - Status:", xhr.status, "Response:", xhr.responseText)
        if (xhr.status === 200 || xhr.status === 204) {
          resolve()
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`))
        }
      })

      xhr.addEventListener("error", (e) => {
        console.error("XHR error event:", e)
        reject(new Error(`Network error during upload: ${xhr.statusText || "Unknown error"}`))
      })

      xhr.addEventListener("abort", () => {
        reject(new Error("Upload was aborted"))
      })

      // Construir FormData con campos del presigned POST
      // IMPORTANTE: El orden importa. Los campos del presigned POST deben ir primero,
      // y el archivo debe ser el último campo.
      const formData = new FormData()
      
      // Añadir todos los campos del presigned POST primero
      Object.entries(fields).forEach(([key, value]) => {
        formData.append(key, value)
      })
      
      // El archivo debe ser el último campo
      formData.append("file", file)

      xhr.open("POST", url)
      // No establecer Content-Type manualmente, el navegador lo hará con el boundary correcto
      xhr.send(formData)
    })
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Validar extensión .csv
      if (!file.name.toLowerCase().endsWith(".csv")) {
        alert("Solo se permiten archivos CSV")
        return
      }
      setSelectedFile(file)
      setUploadStatus("idle")
      setUploadProgress(0)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploadStatus("uploading")
    setUploadProgress(0)

    try {
      // 1. Solicitar presigned URL al backend
      console.log("Requesting presigned URL...")
      const presignedData = await presignedUrlMutation.mutateAsync({
        filename: selectedFile.name,
        project_id: projectId,
      })
      console.log("Presigned URL received:", presignedData)

      // 2. Parchear URL: reemplazar minio:9000 por localhost:9000 para acceso desde el navegador
      const patchedUrl = presignedData.url.replace("minio:9000", "localhost:9000")
      console.log("Patched URL:", patchedUrl)
      console.log("Fields:", presignedData.fields)
      
      // 3. Subir archivo directamente a S3
      console.log("Uploading file to S3...")
      await uploadToS3(selectedFile, patchedUrl, presignedData.fields)
      console.log("File uploaded successfully")

      // 4. Notificar al backend que la subida completó
      console.log("Notifying backend...")
      const uploadResponse = await filesApi.notifyUploadComplete({
        key: presignedData.key,
        project_id: projectId,
        file_size: selectedFile.size,
      })
      console.log("Backend notified:", uploadResponse)

      setUploadStatus("success")
      // Pasar el dataset_id al callback
      onUploadComplete?.(uploadResponse.dataset_id)
    } catch (error: any) {
      console.error("Upload error:", error)
      console.error("Error details:", {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
      })
      setUploadStatus("error")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subir Archivo CSV</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        {selectedFile && (
          <div className="space-y-2">
            <p className="text-sm text-gray-600">
              Archivo seleccionado: <strong>{selectedFile.name}</strong> (
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </p>

            {uploadStatus === "uploading" && (
              <div className="space-y-2">
                <Progress value={uploadProgress} />
                <p className="text-sm text-gray-600">
                  Subiendo... {uploadProgress.toFixed(1)}%
                </p>
              </div>
            )}

            {uploadStatus === "success" && (
              <p className="text-sm text-green-600">✓ Archivo subido exitosamente</p>
            )}

            {uploadStatus === "error" && (
              <div className="space-y-2">
                <p className="text-sm text-red-600">
                  ✗ Error al subir el archivo. Por favor, intenta de nuevo.
                </p>
                <p className="text-xs text-gray-500">
                  Revisa la consola del navegador (F12) para más detalles del error.
                </p>
              </div>
            )}

            {uploadStatus === "idle" && (
              <Button onClick={handleUpload} disabled={presignedUrlMutation.isPending}>
                {presignedUrlMutation.isPending ? "Preparando..." : "Subir Archivo"}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

