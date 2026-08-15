FROM debian:bookworm-slim

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends samba smbclient ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY smb.conf.template /etc/samba/smb.conf.template
COPY entrypoint.sh /usr/local/bin/storage-lab-entrypoint
RUN chmod 0755 /usr/local/bin/storage-lab-entrypoint

EXPOSE 445
ENTRYPOINT ["/usr/local/bin/storage-lab-entrypoint"]
