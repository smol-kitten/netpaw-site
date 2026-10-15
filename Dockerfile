# Stage 1: render the static site from GitHub data (releases, checksums, docs).
FROM python:3.13-alpine AS build
WORKDIR /src
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ARG GITHUB_TOKEN=""
# Cache-bust exactly when the inputs build.py fetches at build time change. BuildKit downloads a remote ADD on
# every build and invalidates this and all later layers when the content differs. Without it the hourly Dokploy
# redeploys reused the cached build.py layer: v0.14.0 was released 2026-10-15 22:06 and the site kept serving
# 0.13.3 through two redeploys (deployment log: "#11 [build 5/5] RUN ... python3 build.py / #11 CACHED").
ADD https://api.github.com/repos/smol-kitten/netpaw/releases/latest /tmp/stamp-latest-release.json
ADD https://api.github.com/repos/smol-kitten/netpaw/commits/main /tmp/stamp-netpaw-main.json
RUN rm -rf out && GITHUB_TOKEN="$GITHUB_TOKEN" python3 build.py

# Stage 2: serve it.
FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /src/out/ /usr/share/nginx/html/
EXPOSE 8080
