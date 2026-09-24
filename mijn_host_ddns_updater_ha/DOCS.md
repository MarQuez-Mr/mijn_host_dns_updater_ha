# Mijn.host DDNS Updater

Configure App options in Home Assistant:

- `api_key`: Mijn.host API key.
- `domain_name`: Base domain managed by Mijn.host.
- `record_names`: Records to update, such as `@` or `*`.
- `default_ttl`: TTL for records created by updater.
- `create_records_if_missing`: Create missing A and AAAA records.
- `interval`: Seconds between updates. Set `0` for one run.

Updater checks public IPv4 and IPv6 addresses, then updates matching Mijn.host
A and AAAA records. Logs are available from the App page.
