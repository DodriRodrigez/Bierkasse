# Eigenen Mailserver in Betrieb nehmen (VPS)

Diese Anleitung beschreibt, wie der in `docker-compose.mail.yml` vorbereitete
Mailserver (docker-mailserver: Postfix, Dovecot, Rspamd/DKIM) auf einem **VPS**
produktiv wird.

> Auf einem Heimanschluss (z. B. Vodafone/versanet) wird Gmail die Zustellung
> trotzdem ablehnen – Grund: keine autorisierte IP, kein PTR für eine eigene
> Domain. Zwischen Tests erledigt das lokale Mailpit (`http://localhost:8025`).

---

## 0. Voraussetzungen

| Was | Detail |
|---|---|
| VPS | öffentliche **IPv4** (empfohlen zusätzlich IPv6), mind. 2 GB RAM |
| Domain | z. B. `example.com`, DNS-Records administrierbar |
| Ports frei | **25**, 587, 465 (Firewall) |
| PTR | beim Hoster Reverse-DNS auf `mail.<domain>` setzen (oft per Support) |

Viele Hoster sperren Port 25 standardmäßig – dort muss er freigeschaltet werden.
Falls der Hoster Port 25 gar nicht erlaubt, bleibt nur ein Relay (Option B).

---

## 1. Konfiguration

```bash
cp .env.example .env
# in .env eintragen:
#   MAIL_DOMAIN=example.com
#   MAIL_HOSTNAME=mail.example.com
```

`mailserver/mailserver.env` prüfen (z. B. `POSTMASTER_ADDRESS`, `ENABLE_CLAMAV`).

---

## 2. Starten

```bash
docker compose -f docker-compose.yml -f docker-compose.mail.yml up -d --build
```

Der Backend-Container versendet damit über den eigenen Mailserver
(`BIERKASSE7_SMTP_HOST=mailserver`, Port 25).

---

## 3. Postfächer + DKIM anlegen

```bash
MAIL_FROM_PASSWORD='<sicheres-passwort>' ./mailserver/setup.sh
```

Das Skript legt `postmaster@<domain>` und `verrechnung@<domain>` an und erzeugt
den DKIM-Schlüssel. Am Ende wird der **öffentliche DKIM-Record** ausgegeben –
diesen gleich in die DNS eintragen.

---

## 4. DNS-Records (Vorlage)

Ersetze `<domain>` = `example.com` und `<vps-ip>` = deine Server-IPv4.

| Typ | Name | Wert | Zweck |
|---|---|---|---|
| **A** | `mail.<domain>` | `<vps-ip>` | Mailserver-Hostname |
| **PTR** | `<vps-ip>` (Reverse) | `mail.<domain>` | Reverse-DNS (beim Hoster) |
| **MX** | `<domain>` | `10 mail.<domain>` | Mailannahme für die Domain |
| **TXT** | `<domain>` | `v=spf1 mx -all` | SPF – nur dieser Server darf senden |
| **TXT** | `mail._domainkey.<domain>` | `v=DKIM1; k=rsa; p=<PUBLIC_KEY>` | DKIM (aus Schritt 3) |
| **TXT** | `_dmarc.<domain>` | `v=DMARC1; p=quarantine; rua=mailto:postmaster@<domain>; adkim=s; aspf=s` | DMARC |
| **TXT** | `_dmarc.<domain>` *(Variante für Start)* | `v=DMARC1; p=none; rua=mailto:postmaster@<domain>` | erst beobachten, dann auf `quarantine` |

Optional / empfohlen später:

| Typ | Name | Wert |
|---|---|---|
| TXT | `_smtp._tls.<domain>` | `v=TLSRPTv1; rua=mailto:postmaster@<domain>` |
| TXT | `_mta-sts.<domain>` | `v=STSv1; id=<timestamp>` |

### Beispiel als `zone`-Ausschnitt (BIND)

```
mail.<domain>.            IN A     <vps-ip>
<domain>.                 IN MX    10 mail.<domain>.
<domain>.                 IN TXT   "v=spf1 mx -all"
mail._domainkey.<domain>. IN TXT   "v=DKIM1; k=rsa; p=<PUBLIC_KEY>"
_dmarc.<domain>.          IN TXT   "v=DMARC1; p=quarantine; rua=mailto:postmaster@<domain>"
```

---

## 5. TLS (Let's Encrypt)

Im `mailserver/mailserver.env` `SSL_TYPE=letsencrypt` setzen und Zertifikate
nach `/mailserver/data/certs` legen (z. B. per `certbot` oder Traefik/Caddy).
Für den reinen Versand genügt zunächst das selbst-signierte Zertifikat.

---

## 6. Prüfen

```bash
dig +short MX <domain>                       # -> 10 mail.<domain>.
dig +short TXT <domain>                      # -> "v=spf1 mx -all"
dig +short TXT mail._domainkey.<domain>      # -> DKIM
dig +short TXT _dmarc.<domain>               # -> DMARC
dig -x <vps-ip> +short                       # -> mail.<domain>.  (PTR)
```

Testmail auslösen (im laufenden Stack):

```bash
curl -s -X POST http://<server>:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<passwort>"}'
# mit dem access_token:
curl -s -X POST http://<server>:8000/api/v1/users/me/settlement-email \
  -H "Authorization: Bearer <token>" -H 'Content-Type: application/json' \
  -d '{"to":"empfaenger@example.com"}'
```

Logs ansehen:

```bash
docker compose -f docker-compose.yml -f docker-compose.mail.yml logs -f mailserver
```

---

## 7. Typische Stolpersteine

| Symptom | Ursache / Lösung |
|---|---|
| `550 5.7.1 … not authorized` | PTR fehlt oder IP (Wohnanschluss) nicht autorisiert → VPS nutzen |
| Mails landen im Spam | SPF/DKIM/DMARC prüfen (`dig`), PTR prüfen, DMARC zunächst `p=none` |
| Port 25 belegt/nicht erreichbar | Hoster-Firewall; Port 25 freischalten lassen |
| DKIM-Record fehlt | `./mailserver/setup.sh` erneut ausführen, Wert in DNS übernehmen |
