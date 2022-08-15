FROM jwilder/nginx-proxy
COPY ./docker/prod/nginx/vhost.d/default /etc/nginx/vhost.d/default
COPY ./docker/prod/nginx/custom.conf /etc/nginx/conf.d/custom.conf


# FROM nginx:latest

# RUN rm /etc/nginx/conf.d/default.conf

# COPY ./docker/prod/nginx/nginx.conf /etc/nginx/conf.d