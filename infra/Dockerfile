# Build stage
FROM alpine:3.20 AS builder

ARG TERRAFORM_VERSION=1.11.3
RUN apk update && apk add --no-cache wget unzip python3 py3-pip zip jq openssl
RUN wget -q https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Production stage
FROM alpine:3.20 AS production

RUN apk update && apk add --no-cache ca-certificates python3 py3-pip zip jq openssl && \
    adduser -D -u 1000 terraform

COPY --from=builder terraform /usr/local/bin/
COPY --chown=terraform infra/main.tf infra/outputs.tf infra/providers.tf infra/variables.tf ./
COPY --chown=terraform infra/modules/ ./modules/

USER terraform
WORKDIR /terraform
