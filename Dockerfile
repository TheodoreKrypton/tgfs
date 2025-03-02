FROM node:buster as build

COPY . /tgfs

RUN cd /tgfs && npm install --only=prod

FROM node:18-buster-slim

# Install Azure CLI for debugging Azure identity issues (optional)
RUN apt-get update && \
    apt-get install -y curl apt-transport-https lsb-release gnupg && \
    curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null && \
    echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/azure-cli.list && \
    apt-get update && \
    apt-get install -y azure-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /

COPY --from=build /tgfs/dist/src /tgfs
COPY --from=build /tgfs/node_modules /node_modules
COPY ./entrypoint.sh /

RUN chmod +x /entrypoint.sh

# ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]