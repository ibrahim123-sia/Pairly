# Pairly web app: build the static site, serve it with nginx.
#   docker build -t pairly-web ./frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# '/api' = same origin; nginx below forwards it to the API container.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
# API_UPSTREAM is filled in by the nginx image's envsubst step at start-up.
ENV API_UPSTREAM=http://backend:5000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
