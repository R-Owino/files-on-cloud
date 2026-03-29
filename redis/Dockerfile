FROM redis:alpine

# Install AWS CLI and jq
RUN apk add --no-cache aws-cli jq

COPY ./scripts/redis-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/redis-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/redis-entrypoint.sh"]
