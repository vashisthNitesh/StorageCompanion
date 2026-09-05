# Multi-stage frontend Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Output stage: minimal image containing only the built static assets
FROM alpine:latest
WORKDIR /var/www/app
COPY --from=builder /app/dist /var/www/app
CMD ["echo", "Frontend static assets compiled."]
