# Mijn.host DDNS Updater Home Assistant App

Home Assistant App for updating Mijn.host DNS records with the current public
IPv4 and IPv6 addresses.

## Installation

1. Open **Settings → Apps** in Home Assistant.
2. Add this repository:
   `https://github.com/MarQuez-Mr/mijn_host_dns_updater_ha`
3. Install **Mijn.host DDNS Updater**.
4. Configure the Mijn.host API key, domain, records, TTL, and update interval.
5. Start the App.

## Configuration

Configuration is entered through the Home Assistant App UI. The Supervisor
writes it to `/data/options.json`; `run.sh` passes that file to the updater.

- `api_key`: Mijn.host API key.
- `domain_name`: Base domain managed by Mijn.host.
- `record_names`: Records to update, such as `@` or `*`.
- `default_ttl`: TTL for newly created records.
- `create_records_if_missing`: Create missing A and AAAA records.
- `interval`: Seconds between updates. Use `0` for one run.

## Development

App source lives in `mijn_host_ddns_updater/`.

```bash
docker build -t local/mijn-host-ddns-updater mijn_host_ddns_updater
```

The App uses the Home Assistant base image and requires `init: false` so
s6-overlay can run as PID 1.

Based on code of https://github.com/wimb0/python-mijn-host-dns-updater.git