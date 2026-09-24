FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3

WORKDIR /app
COPY mijn_host_ddns_updater.py /app/mijn_host_ddns_updater.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
