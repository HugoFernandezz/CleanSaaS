FROM python:3.11-slim as base

# Instalar dependencias del sistema necesarias para Polars y PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/poetry-cache

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION} \
    && ln -s ${POETRY_VENV}/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Asegurar que los binarios estén en el PATH
ENV PATH="/opt/poetry-venv/bin:$PATH"

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando por defecto (puede ser sobrescrito en docker-compose)
# Usar python -m para asegurar que uvicorn se encuentre correctamente
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


