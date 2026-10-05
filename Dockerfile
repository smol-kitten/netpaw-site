FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY out/ /usr/share/nginx/html/
EXPOSE 8080