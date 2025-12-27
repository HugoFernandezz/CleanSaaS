import { useState, useEffect } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, type SelectOption } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { jobsApi, datasetsApi } from "@/lib/api"
import { JobStatus } from "./JobStatus"
import {
  Trash2,
  Edit2,
  Plus,
  X,
  Type,
  Hash,
  Calendar,
  Mail,
  ArrowRight,
} from "lucide-react"

interface CleaningRulesProps {
  datasetId: number
  onRulesChange?: (rules: Record<string, unknown>) => void
  onExport?: (json: Record<string, unknown>) => void
}

// Tipo de regla individual
interface CleaningRule {
  id: string
  field: string
  operator: string
  value: string | number | null
}

// Operadores disponibles según tipo de dato
const OPERATORS_BY_TYPE: Record<string, SelectOption[]> = {
  text: [
    { value: "equals", label: "Igual a" },
    { value: "not_equals", label: "Diferente de" },
    { value: "contains", label: "Contiene" },
    { value: "not_contains", label: "No contiene" },
    { value: "starts_with", label: "Comienza con" },
    { value: "ends_with", label: "Termina con" },
    { value: "is_null", label: "Es nulo" },
    { value: "is_not_null", label: "No es nulo" },
  ],
  number: [
    { value: "equals", label: "Igual a" },
    { value: "not_equals", label: "Diferente de" },
    { value: "greater_than", label: "Mayor que" },
    { value: "greater_than_or_equal", label: "Mayor o igual que" },
    { value: "less_than", label: "Menor que" },
    { value: "less_than_or_equal", label: "Menor o igual que" },
    { value: "is_null", label: "Es nulo" },
    { value: "is_not_null", label: "No es nulo" },
  ],
  date: [
    { value: "equals", label: "Igual a" },
    { value: "not_equals", label: "Diferente de" },
    { value: "greater_than", label: "Después de" },
    { value: "less_than", label: "Antes de" },
    { value: "is_null", label: "Es nulo" },
    { value: "is_not_null", label: "No es nulo" },
  ],
}

// Mapeo de operadores a lenguaje natural
const OPERATOR_LABELS: Record<string, string> = {
  equals: "sea",
  not_equals: "no sea",
  greater_than: "sea mayor que",
  greater_than_or_equal: "sea mayor o igual que",
  less_than: "sea menor que",
  less_than_or_equal: "sea menor o igual que",
  contains: "contenga",
  not_contains: "no contenga",
  starts_with: "comience con",
  ends_with: "termine con",
  is_null: "sea nulo",
  is_not_null: "no sea nulo",
}

export function CleaningRules({
  datasetId,
  onRulesChange,
  onExport,
}: CleaningRulesProps) {
  const [rules, setRules] = useState<CleaningRule[]>([])
  const [combinator, setCombinator] = useState<"and" | "or">("and")
  const [showWizard, setShowWizard] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [currentJobId, setCurrentJobId] = useState<number | null>(null)
  
  const queryClient = useQueryClient()

  // Wizard state
  const [wizardStep, setWizardStep] = useState(1)
  const [wizardField, setWizardField] = useState("")
  const [wizardOperator, setWizardOperator] = useState("")
  const [wizardValue, setWizardValue] = useState("")

  // Obtener columnas del dataset
  const { data: previewData } = useQuery({
    queryKey: ["dataset-preview", datasetId],
    queryFn: () => datasetsApi.getPreview(datasetId, 1),
    enabled: !!datasetId,
  })

  // Mutación para crear job
  const createJobMutation = useMutation({
    mutationFn: (data: { dataset_id: number; rules: Record<string, unknown> }) =>
      jobsApi.createJob(data),
    onSuccess: (data) => {
      setCurrentJobId(data.id)
      console.log("Job creado exitosamente:", data.id)
    },
    onError: (error) => {
      console.error("Error al crear job:", error)
      alert("Error al iniciar la limpieza. Por favor, intenta de nuevo.")
    },
  })

  // Generar opciones de columnas con iconos según tipo inferido
  const getColumnOptions = (): SelectOption[] => {
    if (!previewData?.columns) {
      return []
    }

    return previewData.columns.map((col) => {
      // Inferir tipo de columna por nombre (simple heurística)
      let icon = <Type className="w-4 h-4" />

      const colLower = col.toLowerCase()
      if (
        colLower.includes("id") ||
        colLower.includes("age") ||
        colLower.includes("edad") ||
        colLower.includes("count") ||
        colLower.includes("numero")
      ) {
        icon = <Hash className="w-4 h-4" />
      } else if (
        colLower.includes("email") ||
        colLower.includes("mail") ||
        colLower.includes("correo")
      ) {
        icon = <Mail className="w-4 h-4" />
      } else if (
        colLower.includes("date") ||
        colLower.includes("fecha") ||
        colLower.includes("time")
      ) {
        icon = <Calendar className="w-4 h-4" />
      }

      return {
        value: col,
        label: col,
        icon,
      }
    })
  }

  // Obtener tipo de columna
  const getColumnType = (_fieldName: string): string => {
    const colLower = _fieldName.toLowerCase()
    if (
      colLower.includes("id") ||
      colLower.includes("age") ||
      colLower.includes("edad") ||
      colLower.includes("count") ||
      colLower.includes("numero")
    ) {
      return "number"
    } else if (
      colLower.includes("date") ||
      colLower.includes("fecha") ||
      colLower.includes("time")
    ) {
      return "date"
    }
    return "text"
  }

  // Abrir wizard para nueva regla
  const handleAddRule = () => {
    setWizardStep(1)
    setWizardField("")
    setWizardOperator("")
    setWizardValue("")
    setEditingRuleId(null)
    setShowWizard(true)
  }

  // Abrir wizard para editar regla
  const handleEditRule = (rule: CleaningRule) => {
    setWizardStep(1)
    setWizardField(rule.field)
    setWizardOperator(rule.operator)
    setWizardValue(String(rule.value || ""))
    setEditingRuleId(rule.id)
    setShowWizard(true)
  }

  // Guardar regla del wizard
  const handleSaveRule = () => {
    if (!wizardField || !wizardOperator) {
      alert("Por favor, completa todos los campos")
      return
    }

    // Validar valor (no requerido para operadores is_null/is_not_null)
    const needsValue = !["is_null", "is_not_null"].includes(wizardOperator)
    if (needsValue && !wizardValue) {
      alert("Por favor, ingresa un valor")
      return
    }

    const columnType = getColumnType(wizardField)
    const processedValue =
      columnType === "number" ? Number(wizardValue) : wizardValue

    const newRule: CleaningRule = {
      id: editingRuleId || `rule_${Date.now()}`,
      field: wizardField,
      operator: wizardOperator,
      value: needsValue ? processedValue : null,
    }

    if (editingRuleId) {
      // Editar regla existente
      setRules(rules.map((r) => (r.id === editingRuleId ? newRule : r)))
    } else {
      // Agregar nueva regla
      setRules([...rules, newRule])
    }

    setShowWizard(false)
    setWizardStep(1)
  }

  // Eliminar regla
  const handleDeleteRule = (ruleId: string) => {
    if (confirm("¿Estás seguro de que quieres eliminar esta regla?")) {
      setRules(rules.filter((r) => r.id !== ruleId))
    }
  }

  // Convertir reglas a formato del backend
  const convertToBackendFormat = (): Record<string, unknown> => {
    if (rules.length === 0) {
      return { combinator, rules: [] }
    }

    const backendRules = rules.map((rule) => ({
      field: rule.field,
      operator: rule.operator,
      value: rule.value,
    }))

    return {
      combinator,
      rules: backendRules,
    }
  }

  // Notificar cambios
  useEffect(() => {
    const backendFormat = convertToBackendFormat()
    onRulesChange?.(backendFormat)
  }, [rules, combinator])

  // Ejecutar limpieza
  const handleRunCleaning = () => {
    // Validar datasetId
    if (!datasetId) {
      alert("Por favor, selecciona un dataset primero")
      return
    }

    // Validar que haya reglas
    if (rules.length === 0) {
      alert("Por favor, crea al menos una regla antes de ejecutar la limpieza")
      return
    }

    // Convertir reglas al formato del backend
    const exportedRules = convertToBackendFormat()
    
    console.log("Iniciando limpieza con:", {
      dataset_id: datasetId,
      rules: exportedRules,
    })

    // Ejecutar mutación
    createJobMutation.mutate({
      dataset_id: datasetId,
      rules: exportedRules,
    })
  }

  // Obtener operadores disponibles según el campo seleccionado
  const getAvailableOperators = (): SelectOption[] => {
    if (!wizardField) return []
    const columnType = getColumnType(wizardField)
    return OPERATORS_BY_TYPE[columnType] || OPERATORS_BY_TYPE.text
  }

  // Formatear regla en lenguaje natural
  const formatRuleNatural = (rule: CleaningRule): string => {
    const fieldName = rule.field
    const operatorLabel = OPERATOR_LABELS[rule.operator] || rule.operator
    const valueDisplay = rule.value !== null ? String(rule.value) : ""

    if (["is_null", "is_not_null"].includes(rule.operator)) {
      return `🗑️ Eliminar filas donde [${fieldName}] ${operatorLabel}`
    }

    return `🗑️ Eliminar filas donde [${fieldName}] ${operatorLabel} [${valueDisplay}]`
  }

  // Evaluar una regla individual contra un valor de celda
  const evaluateRule = (rule: CleaningRule, cellValue: unknown): boolean => {
    const fieldValue = cellValue
    const ruleValue = rule.value

    // Convertir valores a tipos comparables
    const getComparableValue = (val: unknown, operator: string): unknown => {
      if (val === null || val === undefined) return null
      
      // Para operadores numéricos, intentar convertir a número
      if (["greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"].includes(operator)) {
        const num = Number(val)
        return isNaN(num) ? val : num
      }
      
      return String(val)
    }

    const comparableField = getComparableValue(fieldValue, rule.operator)
    const comparableRule = getComparableValue(ruleValue, rule.operator)

    switch (rule.operator) {
      case "equals":
        return comparableField === comparableRule
      case "not_equals":
        return comparableField !== comparableRule
      case "greater_than":
        return Number(comparableField) > Number(comparableRule)
      case "greater_than_or_equal":
        return Number(comparableField) >= Number(comparableRule)
      case "less_than":
        return Number(comparableField) < Number(comparableRule)
      case "less_than_or_equal":
        return Number(comparableField) <= Number(comparableRule)
      case "contains":
        return String(comparableField).toLowerCase().includes(String(comparableRule).toLowerCase())
      case "not_contains":
        return !String(comparableField).toLowerCase().includes(String(comparableRule).toLowerCase())
      case "starts_with":
        return String(comparableField).toLowerCase().startsWith(String(comparableRule).toLowerCase())
      case "ends_with":
        return String(comparableField).toLowerCase().endsWith(String(comparableRule).toLowerCase())
      case "is_null":
        return fieldValue === null || fieldValue === undefined || fieldValue === ""
      case "is_not_null":
        return fieldValue !== null && fieldValue !== undefined && fieldValue !== ""
      default:
        return false
    }
  }

  // Calcular impacto real basado en datos de preview
  const calculateImpact = (rule: CleaningRule): { matches: number; total: number } | null => {
    // Obtener datos de preview desde el queryClient
    // Buscar todas las queries que empiecen con "dataset-preview" y datasetId
    const allQueries = queryClient.getQueriesData({
      queryKey: ["dataset-preview", datasetId],
      exact: false,
    })

    // Buscar la primera query que tenga datos válidos
    let queryData: {
      dataset_id: number
      columns: string[]
      rows: Record<string, unknown>[]
      row_count: number
      total_columns: number
    } | undefined

    for (const [, data] of allQueries) {
      if (data && typeof data === "object" && "rows" in data) {
        queryData = data as typeof queryData
        break
      }
    }

    // Si no encuentra con getQueriesData, intentar con getQueryData directamente
    if (!queryData) {
      // Intentar con diferentes variaciones de la key
      queryData = queryClient.getQueryData(["dataset-preview", datasetId, 100]) as typeof queryData
      if (!queryData) {
        queryData = queryClient.getQueryData(["dataset-preview", datasetId]) as typeof queryData
      }
    }

    // Verificar si los datos están disponibles
    if (!queryData) {
      return null
    }

    // Acceder a las filas - TanStack Query almacena directamente el resultado de queryFn
    // que es response.data, así que queryData ya es el objeto con rows
    const rows = queryData.rows

    // Verificar que rows existe y es un array válido
    if (!rows || !Array.isArray(rows) || rows.length === 0) {
      return null
    }

    // Contar cuántas filas cumplen la condición de esta regla
    let matches = 0
    for (const row of rows) {
      const cellValue = row[rule.field]
      if (evaluateRule(rule, cellValue)) {
        matches++
      }
    }

    return {
      matches,
      total: rows.length,
    }
  }

  // Obtener texto del badge de impacto
  const getImpactBadgeText = (rule: CleaningRule): string => {
    const impact = calculateImpact(rule)
    
    if (impact === null) {
      return "Calculando..."
    }

    return `Coincide con ${impact.matches} de ${impact.total} filas (Vista Previa)`
  }

  const columnOptions = getColumnOptions()
  const availableOperators = getAvailableOperators()
  const needsValue = wizardOperator && !["is_null", "is_not_null"].includes(wizardOperator)

  // Si hay un job activo, mostrar solo el estado del job
  if (currentJobId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Procesando Limpieza de Datos</CardTitle>
          <p className="text-sm text-gray-600">
            El proceso de limpieza está en ejecución. Por favor, espera...
          </p>
        </CardHeader>
        <CardContent>
          <JobStatus
            jobId={currentJobId}
            onComplete={(downloadUrl) => {
              console.log("Job completado, URL de descarga:", downloadUrl)
              // Opcional: resetear para permitir crear otro job
              // setCurrentJobId(null)
            }}
            onError={(errorMessage) => {
              console.error("Job falló:", errorMessage)
              alert(`Error en el procesamiento: ${errorMessage}`)
              // Resetear para permitir reintentar
              setCurrentJobId(null)
            }}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reglas de Limpieza</CardTitle>
        <p className="text-sm text-gray-600">
          Define reglas para filtrar y limpiar tus datos de forma intuitiva
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Selector de modo de combinación */}
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">
            Modo de combinación:
          </label>
          <Select
            value={combinator}
            onChange={(e) => setCombinator(e.target.value as "and" | "or")}
            options={[
              { value: "and", label: "Cumplir TODAS las reglas (AND)" },
              { value: "or", label: "Cumplir CUALQUIERA (OR)" },
            ]}
            className="w-64"
          />
        </div>

        {/* Lista de reglas */}
        <div className="space-y-3">
          {rules.length === 0 ? (
            <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-200 rounded-lg">
              <p className="mb-2">No hay reglas definidas</p>
              <p className="text-sm">Haz clic en "+ Agregar Regla" para comenzar</p>
            </div>
          ) : (
            rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {formatRuleNatural(rule)}
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <Badge 
                    variant="secondary" 
                    title={getImpactBadgeText(rule)}
                    className="max-w-xs truncate"
                  >
                    {getImpactBadgeText(rule)}
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEditRule(rule)}
                    className="h-8 w-8 p-0"
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteRule(rule.id)}
                    className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Botón agregar regla */}
        <Button
          onClick={handleAddRule}
          className="w-full"
          variant="outline"
          size="lg"
        >
          <Plus className="w-5 h-5 mr-2" />
          Agregar Regla de Limpieza
        </Button>

        {/* Botones de acción */}
        <div className="flex justify-end space-x-2 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => setRules([])}
            disabled={rules.length === 0}
          >
            Limpiar Todo
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              const exported = convertToBackendFormat()
              onExport?.(exported)
              console.log("Rules exported:", exported)
            }}
          >
            Exportar Reglas
          </Button>
          <Button
            onClick={handleRunCleaning}
            disabled={!datasetId || createJobMutation.isPending || rules.length === 0}
            className="min-w-[140px]"
          >
            {createJobMutation.isPending ? (
              <span className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Iniciando...
              </span>
            ) : (
              "Limpiar Datos"
            )}
          </Button>
        </div>

        {/* Wizard Dialog */}
        <Dialog open={showWizard} onOpenChange={setShowWizard}>
          <DialogContent className="max-w-2xl">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Crear Regla de Limpieza</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowWizard(false)}
                  className="h-8 w-8 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              {/* Indicador de pasos */}
              <div className="flex items-center space-x-2">
                <div
                  className={`flex-1 h-2 rounded ${
                    wizardStep >= 1 ? "bg-blue-600" : "bg-gray-200"
                  }`}
                />
                <ArrowRight className="w-4 h-4 text-gray-400" />
                <div
                  className={`flex-1 h-2 rounded ${
                    wizardStep >= 2 ? "bg-blue-600" : "bg-gray-200"
                  }`}
                />
                <ArrowRight className="w-4 h-4 text-gray-400" />
                <div
                  className={`flex-1 h-2 rounded ${
                    wizardStep >= 3 ? "bg-blue-600" : "bg-gray-200"
                  }`}
                />
              </div>

              {/* Paso 1: Seleccionar Columna */}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Paso 1: Seleccionar Columna
                    </label>
                    <Select
                      value={wizardField}
                      onChange={(e) => {
                        setWizardField(e.target.value)
                        setWizardOperator("")
                        setWizardValue("")
                      }}
                      options={columnOptions}
                      placeholder="Selecciona una columna..."
                      className="w-full"
                    />
                  </div>
                  {wizardField && (
                    <div className="flex justify-end">
                      <Button onClick={() => setWizardStep(2)}>
                        Siguiente
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Paso 2: Seleccionar Condición */}
              {wizardStep === 2 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Paso 2: Seleccionar Condición
                    </label>
                    <Select
                      value={wizardOperator}
                      onChange={(e) => {
                        setWizardOperator(e.target.value)
                        setWizardValue("")
                      }}
                      options={availableOperators}
                      placeholder="Selecciona una condición..."
                      className="w-full"
                    />
                  </div>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={() => setWizardStep(1)}>
                      Atrás
                    </Button>
                    {wizardOperator && (
                      <Button
                        onClick={() => {
                          if (needsValue) {
                            setWizardStep(3)
                          } else {
                            handleSaveRule()
                          }
                        }}
                      >
                        {needsValue ? (
                          <>
                            Siguiente
                            <ArrowRight className="w-4 h-4 ml-2" />
                          </>
                        ) : (
                          "Guardar"
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {/* Paso 3: Ingresar Valor */}
              {wizardStep === 3 && needsValue && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Paso 3: Ingresar Valor
                    </label>
                    <input
                      type={getColumnType(wizardField) === "number" ? "number" : "text"}
                      value={wizardValue}
                      onChange={(e) => setWizardValue(e.target.value)}
                      placeholder="Ingresa el valor..."
                      className="w-full h-10 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={() => setWizardStep(2)}>
                      Atrás
                    </Button>
                    <Button onClick={handleSaveRule} disabled={!wizardValue}>
                      Guardar Regla
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>

      </CardContent>
    </Card>
  )
}
