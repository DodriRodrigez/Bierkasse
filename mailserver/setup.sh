#!/usr/bin/env bash
#
# Einrichtung des eigenen Mailservers nach dem ersten Start.
#
#   MAIL_FROM_PASSWORD='<passwort>' ./mailserver/setup.sh
#
# Legt die benötigten Postfächer an und erzeugt den DKIM-Schlüssel.
set -euo pipefail

CONTAINER="${MAIL_CONTAINER:-bierkasse7-mailserver}"
DOMAIN="${MAIL_DOMAIN:-example.com}"
FROM_USER="${MAIL_FROM_USER:-verrechnung}"
POSTMASTER_PASSWORD="${MAIL_POSTMASTER_PASSWORD:-$(openssl rand -base64 12 2>/dev/null || echo changeme123)}"
FROM_PASSWORD="${MAIL_FROM_PASSWORD:-}"

if [ -z "$FROM_PASSWORD" ]; then
  echo "FEHLER: Bitte MAIL_FROM_PASSWORD setzen (Passwort für ${FROM_USER}@${DOMAIN})." >&2
  exit 1
fi

echo "==> Postfach postmaster@${DOMAIN} anlegen"
docker exec "$CONTAINER" setup email add "postmaster@${DOMAIN}" "$POSTMASTER_PASSWORD" || true

echo "==> Postfach ${FROM_USER}@${DOMAIN} anlegen (Absender der Verrechnung)"
docker exec "$CONTAINER" setup email add "${FROM_USER}@${DOMAIN}" "$FROM_PASSWORD" || true

echo "==> DKIM-Schlüssel für ${DOMAIN} erzeugen"
docker exec "$CONTAINER" setup config dkim domain "${DOMAIN}"

echo
echo "==> DKIM (DNS) – folgenden TXT-Record für  mail._domainkey.${DOMAIN}  eintragen:"
docker exec "$CONTAINER" sh -c "cat /tmp/docker-mailserver/rspamd/dkim/*.public.dns.txt 2>/dev/null \
  || find /tmp/docker-mailserver -name '*.public.dns.txt' -exec cat {} +"

echo
echo "Fertig. Weiter mit den DNS-Records aus mailserver/DNS-VORLAGE.md."
