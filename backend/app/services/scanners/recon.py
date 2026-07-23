"""Passive subdomain discovery + lightweight TCP port sweep.

Only uses public certificate-transparency data (crt.sh) and direct TCP
connect attempts against the target itself - no third-party scanning
services, no credential/exploit attempts.
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from app.core.config import settings

PORT_SEVERITY = {
    21: "medium",  # FTP
    22: "info",  # SSH
    25: "low",  # SMTP
    80: "info",
    110: "low",  # POP3
    143: "low",  # IMAP
    443: "info",
    3306: "high",  # MySQL exposed
    3389: "critical",  # RDP exposed
    5432: "high",  # Postgres exposed
    6379: "critical",  # Redis exposed (often unauthenticated)
    8080: "low",
    8443: "low",
}

PORT_LABELS = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-alt",
    8443: "HTTPS-alt",
}


def enumerate_subdomains(domain: str) -> list[str]:
    try:
        resp = httpx.get(
            "https://crt.sh/",
            params={"q": f"%.{domain}", "output": "json"},
            timeout=15,
            headers={"User-Agent": "SentraScan-Recon/1.0"},
        )
        resp.raise_for_status()
        entries = resp.json()
    except (httpx.HTTPError, ValueError):
        return [domain]

    subdomains: set[str] = {domain}
    for entry in entries:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower().lstrip("*.")
            if name and name.endswith(domain):
                subdomains.add(name)

    return sorted(subdomains)[: settings.RECON_MAX_SUBDOMAINS]


def resolve(hostname: str) -> str | None:
    try:
        return socket.gethostbyname(hostname)
    except OSError:
        return None


def scan_port(ip: str, port: int, timeout: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((ip, port)) == 0


def run(domain: str) -> list[dict]:
    findings: list[dict] = []
    subdomains = enumerate_subdomains(domain)

    findings.append(
        {
            "module": "recon",
            "key": "subdomain-summary",
            "severity": "info",
            "title": f"{len(subdomains)} alt alan adi/host tespit edildi",
            "description": "Sertifika seffafligi (crt.sh) kayitlarindan pasif olarak toplandi.",
            "evidence": {"subdomains": subdomains},
        }
    )

    live_hosts: dict[str, str] = {}
    for sub in subdomains:
        ip = resolve(sub)
        if ip:
            live_hosts[sub] = ip

    if not live_hosts:
        return findings

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {}
        for host, ip in live_hosts.items():
            for port in settings.RECON_PORT_LIST:
                futures[pool.submit(scan_port, ip, port, settings.RECON_PORT_TIMEOUT)] = (host, ip, port)

        for future in as_completed(futures):
            host, ip, port = futures[future]
            try:
                is_open = future.result()
            except Exception:
                is_open = False
            if is_open:
                findings.append(
                    {
                        "module": "recon",
                        "key": f"open-port:{host}:{port}",
                        "severity": PORT_SEVERITY.get(port, "low"),
                        "title": f"Acik port: {host}:{port} ({PORT_LABELS.get(port, 'unknown')})",
                        "description": f"{host} ({ip}) uzerinde {port} numarali port disaridan erisilebilir durumda.",
                        "evidence": {"host": host, "ip": ip, "port": port, "service": PORT_LABELS.get(port)},
                    }
                )

    return findings
