"""Rule parser seguro usando patrón Visitor/Interpreter para convertir JSON a expresiones Polars."""

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class RuleParserError(Exception):
    """Excepción para errores en el parsing de reglas."""

    pass


class RuleParser:
    """
    Parser seguro para convertir JSON de reglas a expresiones Polars.

    Este parser usa el patrón Visitor/Interpreter para recorrer recursivamente
    el árbol JSON y generar expresiones Polars de manera segura, sin usar
    eval() o exec().

    PROHIBIDO: eval(), exec(), interpolación de strings SQL/Python.
    """

    # Lista blanca de operadores permitidos
    ALLOWED_LOGICAL_OPERATORS = {"and", "or", "AND", "OR"}
    ALLOWED_COMPARISON_OPERATORS = {
        "equals",
        "not_equals",
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
        "contains",
        "not_contains",
        "is_null",
        "is_not_null",
        "starts_with",
        "ends_with",
    }

    def __init__(self, schema: dict[str, pl.DataType] | None = None):
        """
        Inicializar el parser.

        Args:
            schema: Esquema del LazyFrame para hacer casting de tipos correcto
        """
        self.schema = schema or {}

    def parse(self, rule_json: dict[str, Any]) -> pl.Expr:
        """
        Parsear el JSON de reglas y generar una expresión Polars.

        Esta función es determinista: el mismo JSON genera la misma expresión.

        Args:
            rule_json: JSON con la estructura de reglas

        Returns:
            Expresión Polars ejecutable

        Raises:
            RuleParserError: Si el JSON es inválido o contiene operadores no permitidos
        """
        if not isinstance(rule_json, dict):
            raise RuleParserError("Rule must be a dictionary")

        # Detectar tipo de nodo
        if "combinator" in rule_json:
            # Nodo grupo (AND/OR)
            return self._parse_group(rule_json)
        elif "field" in rule_json and "operator" in rule_json:
            # Nodo regla (comparación)
            return self._parse_rule(rule_json)
        else:
            raise RuleParserError(
                f"Invalid rule structure: must have 'combinator' or 'field'/'operator'"
            )

    def _parse_group(self, group_json: dict[str, Any]) -> pl.Expr:
        """
        Parsear un grupo lógico (AND/OR).

        Args:
            group_json: JSON con estructura {combinator: "and"/"or", rules: [...]}

        Returns:
            Expresión Polars combinando las reglas
        """
        combinator = group_json.get("combinator", "").lower()
        if combinator not in self.ALLOWED_LOGICAL_OPERATORS:
            raise RuleParserError(
                f"Invalid combinator '{combinator}'. Allowed: {self.ALLOWED_LOGICAL_OPERATORS}"
            )

        rules = group_json.get("rules", [])
        if not rules:
            raise RuleParserError("Group must have at least one rule")

        # Parsear recursivamente cada regla
        expressions = [self.parse(rule) for rule in rules]

        # Combinar según el operador lógico
        if combinator == "and":
            result = expressions[0]
            for expr in expressions[1:]:
                result = result & expr
            return result
        else:  # or
            result = expressions[0]
            for expr in expressions[1:]:
                result = result | expr
            return result

    def _parse_rule(self, rule_json: dict[str, Any]) -> pl.Expr:
        """
        Parsear una regla de comparación individual.

        Args:
            rule_json: JSON con estructura {field: "columna", operator: "...", value: ...}

        Returns:
            Expresión Polars para la comparación
        """
        field = rule_json.get("field")
        operator = rule_json.get("operator", "").lower()
        value = rule_json.get("value")

        if not field:
            raise RuleParserError("Rule must have a 'field'")

        if operator not in self.ALLOWED_COMPARISON_OPERATORS:
            raise RuleParserError(
                f"Invalid operator '{operator}'. Allowed: {self.ALLOWED_COMPARISON_OPERATORS}"
            )

        # Obtener columna
        col = pl.col(field)

        # Hacer casting de tipo si es necesario
        if self.schema and field in self.schema:
            target_type = self.schema[field]
            # Solo hacer casting si el valor no es None
            if value is not None:
                value = self._cast_value(value, target_type)

        # Generar expresión según operador (lista blanca)
        return self._build_comparison_expression(col, operator, value)

    def _cast_value(
        self, value: Any, target_type: pl.DataType
    ) -> Any:
        """
        Hacer casting explícito del valor al tipo de la columna.

        Esta función es determinista y segura: solo hace conversiones explícitas.

        Args:
            value: Valor a convertir
            target_type: Tipo objetivo de Polars

        Returns:
            Valor convertido al tipo correcto
        """
        # Polars tipos básicos
        if isinstance(target_type, pl.Int64) or isinstance(target_type, pl.Int32):
            return int(value)
        elif isinstance(target_type, pl.Float64) or isinstance(target_type, pl.Float32):
            return float(value)
        elif isinstance(target_type, pl.Boolean):
            return bool(value)
        elif isinstance(target_type, pl.Utf8) or isinstance(target_type, pl.String):
            return str(value)
        # Si no se puede determinar, retornar el valor original
        return value

    def _build_comparison_expression(
        self, col: pl.Expr, operator: str, value: Any
    ) -> pl.Expr:
        """
        Construir expresión de comparación Polars.

        Esta función usa solo operadores nativos de Polars, sin interpolación de strings.

        Args:
            col: Expresión de columna Polars
            operator: Operador (de lista blanca)
            value: Valor a comparar

        Returns:
            Expresión Polars de comparación
        """
        # Mapeo seguro de operadores a expresiones Polars
        operator_map = {
            "equals": lambda c, v: c == v,
            "not_equals": lambda c, v: c != v,
            "greater_than": lambda c, v: c > v,
            "greater_than_or_equal": lambda c, v: c >= v,
            "less_than": lambda c, v: c < v,
            "less_than_or_equal": lambda c, v: c <= v,
            "contains": lambda c, v: c.str.contains(str(v)),
            "not_contains": lambda c, v: ~c.str.contains(str(v)),
            "is_null": lambda c, v: c.is_null(),
            "is_not_null": lambda c, v: c.is_not_null(),
            "starts_with": lambda c, v: c.str.starts_with(str(v)),
            "ends_with": lambda c, v: c.str.ends_with(str(v)),
        }

        if operator not in operator_map:
            raise RuleParserError(f"Unsupported operator: {operator}")

        try:
            return operator_map[operator](col, value)
        except Exception as e:
            raise RuleParserError(
                f"Error building expression for operator '{operator}': {str(e)}"
            )


