import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional


API_BASE_URL = "https://mijn.host/api/v2"
USER_AGENT = "Python-DDNS-Client"
logger = logging.getLogger(__name__)


def _perform_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict] = None,
    data: Optional[bytes] = None,
) -> bytes:
    base_headers = {"User-Agent": USER_AGENT}
    if headers:
        base_headers.update(headers)

    request = urllib.request.Request(
        url,
        data=data,
        headers=base_headers,
        method=method,
    )
    logger.debug("Executing request: %s %s", method, url)

    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 400:
            raise urllib.error.HTTPError(
                url,
                response.status,
                response.reason,
                response.headers,
                None,
            )
        return response.read()


def get_public_ip(version: int) -> Optional[str]:
    try:
        response = _perform_request(f"https://ipv{version}.icanhazip.com")
        ip_address = response.decode("utf-8").strip()
        logger.debug("Found public IPv%s address: %s", version, ip_address)
        return ip_address
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        logger.warning("Could not retrieve public IPv%s address: %s", version, error)
        return None


def get_records(api_key: str, domain_name: str) -> Optional[List[Dict]]:
    url = f"{API_BASE_URL}/domains/{domain_name}/dns"
    headers = {"API-Key": api_key, "Accept": "application/json"}
    try:
        response = _perform_request(url, headers=headers)
        data = json.loads(response)
        records = data.get("data", {}).get("records")
        if records is not None:
            logger.debug(
                "Current DNS records for %s:\n%s",
                domain_name,
                json.dumps(records, indent=2),
            )
        return records
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        logger.error("Error fetching DNS records: %s", error)
    except json.JSONDecodeError:
        logger.error("Error parsing the DNS records response.")
    return None


def put_records(api_key: str, domain_name: str, records: List[Dict]) -> bool:
    url = f"{API_BASE_URL}/domains/{domain_name}/dns"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    data = json.dumps({"records": records}).encode("utf-8")
    try:
        _perform_request(url, method="PUT", headers=headers, data=data)
        logger.info("DNS records updated successfully.")
        return True
    except (urllib.error.URLError, urllib.error.HTTPError) as error:
        logger.error("Error updating DNS records: %s", error)
        return False


def update_ddns(config: Dict, preview: bool = False) -> None:
    logger.info(
        "Starting update routine%s.",
        " in PREVIEW mode. No changes will be made" if preview else "",
    )

    api_key = config["api_key"]
    domain_name = config["domain_name"]
    record_names = config["record_names"]
    create_records = config.get("create_records_if_missing", False)

    all_records = get_records(api_key, domain_name)
    if all_records is None:
        return

    records_to_update = list(all_records)
    changes_found = []
    public_ipv4 = get_public_ip(4)
    public_ipv6 = get_public_ip(6)

    if not public_ipv4:
        logger.info("No public IPv4 address found, skipping A records.")
    if not public_ipv6:
        logger.info("No public IPv6 address found, skipping AAAA records.")

    def normalize_record_name(name: str) -> str:
        return name.rstrip(".")

    for record_name in record_names:
        full_target_name = (
            f"{record_name}.{domain_name}" if record_name != "@" else domain_name
        ).rstrip(".")
        logger.info("--- Processing record: %s ---", full_target_name)

        if public_ipv4:
            a_record = next(
                (
                    record
                    for record in records_to_update
                    if record["type"] == "A"
                    and normalize_record_name(record["name"]) == full_target_name
                ),
                None,
            )
            if a_record:
                if a_record["value"] != public_ipv4:
                    summary = (
                        f"Update A record for '{full_target_name}' from "
                        f"'{a_record['value']}' to '{public_ipv4}'"
                    )
                    logger.info("CHANGE DETECTED: %s", summary)
                    changes_found.append(summary)
                    a_record["value"] = public_ipv4
            elif create_records:
                ttl = config["default_ttl"]
                summary = (
                    f"Create A record for '{full_target_name}' with IP "
                    f"'{public_ipv4}' and TTL {ttl}"
                )
                logger.info("CHANGE DETECTED: %s", summary)
                changes_found.append(summary)
                records_to_update.append(
                    {"type": "A", "name": record_name, "value": public_ipv4, "ttl": ttl}
                )

        if public_ipv6:
            aaaa_record = next(
                (
                    record
                    for record in records_to_update
                    if record["type"] == "AAAA"
                    and normalize_record_name(record["name"]) == full_target_name
                ),
                None,
            )
            if aaaa_record:
                if aaaa_record["value"] != public_ipv6:
                    summary = (
                        f"Update AAAA record for '{full_target_name}' from "
                        f"'{aaaa_record['value']}' to '{public_ipv6}'"
                    )
                    logger.info("CHANGE DETECTED: %s", summary)
                    changes_found.append(summary)
                    aaaa_record["value"] = public_ipv6
            elif create_records:
                ttl = config["default_ttl"]
                summary = (
                    f"Create AAAA record for '{full_target_name}' with IP "
                    f"'{public_ipv6}' and TTL {ttl}"
                )
                logger.info("CHANGE DETECTED: %s", summary)
                changes_found.append(summary)
                records_to_update.append(
                    {"type": "AAAA", "name": record_name, "value": public_ipv6, "ttl": ttl}
                )

    if not changes_found:
        logger.info("No action required. All checked records are already up-to-date.")
        return

    if preview:
        logger.info("PREVIEW: The following changes would be made:")
        for change in changes_found:
            print(f"  - {change}")
        return

    logger.info("Pushing updates to the API...")
    put_records(api_key, domain_name, records_to_update)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mijn.host DDNS updater")
    parser.add_argument(
        "-c",
        "--config",
        default="./config.json",
        help="Path to the JSON configuration file (default: ./config.json).",
    )
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-p", "--preview", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logger.info("Starting Mijn.host DDNS Updater")

    try:
        with open(args.config, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        logger.error("Configuration file not found at: %s", args.config)
        sys.exit(1)
    except IsADirectoryError:
        logger.error("Configuration path is a directory: %s", args.config)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Error parsing configuration file: %s", args.config)
        sys.exit(1)

    required_keys = ["api_key", "domain_name", "record_names", "default_ttl"]
    if not all(key in config for key in required_keys):
        logger.error("Configuration missing required keys: %s", required_keys)
        sys.exit(1)

    interval = config.get("interval", 0)
    while True:
        try:
            update_ddns(config, preview=args.preview)
        except Exception as error:
            logger.error("Unexpected error during update routine: %s", error)

        if interval <= 0:
            logger.info("Interval is 0, script will now exit.")
            break

        logger.info("Waiting for %s seconds before next run...", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
