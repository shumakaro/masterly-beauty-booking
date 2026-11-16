FROM node:24-bookworm-slim AS build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig*.json vite.config.ts ./
COPY src ./src
COPY public ./public
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM nginx:1.30.6-alpine AS runtime
COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/includes /etc/nginx/includes
ENV NGINX_ENVSUBST_FILTER=PUBLIC_HOST
EXPOSE 8080 8443
