FROM node:buster as build

COPY . /tgfs

RUN cd /tgfs && npm install --only=prod

FROM node:18-buster-slim

WORKDIR /

COPY --from=build /tgfs/dist/src /tgfs
COPY --from=build /tgfs/node_modules /node_modules
COPY ./entrypoint.sh /

RUN chmod +x /entrypoint.sh

# ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]