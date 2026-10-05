# Stage 1: render the static site from GitHub data (releases, checksums, docs).
FROM python:3.13-alpine AS build
WORKDIR /src
COPY . .
ARG GITHUB_TOKEN=""
RUN rm -rf out && GITHUB_TOKEN="$GITHUB_TOKEN" python3 build.py

# Stage 2: serve it.
FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /src/out/ /usr/share/nginx/html/
EXPOSE 8080
