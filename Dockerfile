FROM node:buster as build

COPY . /tgfs

RUN cd /tgfs && npm install --only=prod && npm install -g pkg && pkg -t node16-linux .

FROM debian:buster-slim

WORKDIR /

COPY --from=build /tgfs/tgfs .

CMD ["./tgfs"]