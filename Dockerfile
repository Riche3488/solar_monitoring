# Stage 1: Build React frontend
FROM node:20-slim AS frontend
WORKDIR /app/dashboard/frontend
COPY dashboard/frontend/package*.json ./
RUN npm ci
COPY dashboard/frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim
WORKDIR /app

COPY dashboard/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /app/dashboard/frontend/dist ./dashboard/frontend/dist

EXPOSE 8080
CMD ["sh", "-c", "uvicorn dashboard.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
