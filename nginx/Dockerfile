FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config
COPY nginx/nginx.conf /etc/nginx/conf.d/fashionai.conf

# Copy static web files
COPY web/ /usr/share/nginx/html/

EXPOSE 80