FROM node:20-alpine as base

WORKDIR /app

# Instalar dependencias
COPY package.json package-lock.json* ./
RUN npm install

# Copiar código fuente
COPY . .

# Exponer puerto
EXPOSE 3000

# Comando de desarrollo (puede ser sobrescrito en docker-compose)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


