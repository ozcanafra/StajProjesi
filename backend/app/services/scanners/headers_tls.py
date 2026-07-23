"""HTTP security header + TLS/certificate posture checks.

Entirely passive: a single HTTPS GET plus a TLS handshake against the
target's own port 443. No injection payloads, no credential attempts.
"""

import socket
import ssl
from datetime import datetime, timezone

import requests

REQUIRED_HEADERS = {
    "Strict-Transport-Security": ("medium", "HSTS eksik: taraycilar HTTP'ye dusme riskiyle karsi karsiya."),
    "Content-Security-Policy": ("medium", "CSP eksik: XSS/veri enjeksiyonu etkisini sinirlayan bir katman yok."),
    "X-Content-Type-Options": ("low", "X-Content-Type-Options eksik: MIME sniffing riski."),
    "X-Frame-Options": ("low", "X-Frame-Options eksik: clickjacking'e karsi koruma yok."),
    "Referrer-Policy": ("info", "Referrer-Policy eksik: referrer bilgisi kontrolsuz sizabilir."),
}

WEAK_TLS_VERSIONS = {"TLSv1", "TLSv1.1", "SSLv3", "SSLv2"}


def check_headers(domain: str) -> list[dict]:
    findings: list[dict] = []
    url = f"https://{domain}"
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": "SentraScan/1.0"})
    except requests.RequestException as exc:
        return [
            {
                "module": "headers_tls",
                "severity": "medium",
                "title": "HTTPS uzerinden erisilemedi",
                "description": f"{url} adresine baglanilamadi: {exc}",
                "evidence": {"url": url},
            }
        ]

    for header, (severity, description) in REQUIRED_HEADERS.items():
        if header not in resp.headers:
            findings.append(
                {
                    "module": "headers_tls",
                    "severity": severity,
                    "title": f"Eksik guvenlik header'i: {header}",
                    "description": description,
                    "evidence": {"url": url},
                }
            )

    server_header = resp.headers.get("Server")
    if server_header:
        findings.append(
            {
                "module": "headers_tls",
                "severity": "info",
                "title": "Sunucu bilgisi Server header'inda ifsa ediliyor",
                "description": f"Server header degeri: {server_header}",
                "evidence": {"server": server_header},
            }
        )

    for cookie in resp.cookies:
        issues = []
        if not cookie.secure:
            issues.append("Secure bayragi yok")
        has_httponly = "httponly" in {k.lower() for k in (cookie._rest or {}).keys()}
        if not has_httponly:
            issues.append("HttpOnly bayragi yok")
        if issues:
            findings.append(
                {
                    "module": "headers_tls",
                    "severity": "low",
                    "title": f"Guvensiz cookie ayari: {cookie.name}",
                    "description": ", ".join(issues),
                    "evidence": {"cookie": cookie.name},
                }
            )

    if not findings:
        findings.append(
            {
                "module": "headers_tls",
                "severity": "info",
                "title": "Temel guvenlik header'lari mevcut",
                "description": "Kontrol edilen zorunlu header'larin tumu bulundu.",
                "evidence": {"url": url},
            }
        )

    return findings


def check_tls(domain: str) -> list[dict]:
    findings: list[dict] = []
    context = ssl.create_default_context()

    try:
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version()
    except (OSError, ssl.SSLError) as exc:
        return [
            {
                "module": "headers_tls",
                "severity": "medium",
                "title": "TLS handshake basarisiz",
                "description": f"{domain}:443 uzerinde TLS baglantisi kurulamadi: {exc}",
                "evidence": {"domain": domain},
            }
        ]

    if protocol in WEAK_TLS_VERSIONS:
        findings.append(
            {
                "module": "headers_tls",
                "severity": "high",
                "title": f"Zayif TLS protokolu kullaniliyor: {protocol}",
                "description": "Modern istemciler TLS 1.2 veya ustunu beklemelidir.",
                "evidence": {"protocol": protocol},
            }
        )
    else:
        findings.append(
            {
                "module": "headers_tls",
                "severity": "info",
                "title": f"Negotiated TLS protokolu: {protocol}",
                "description": "Baglanti sirasinda kullanilan TLS surumu.",
                "evidence": {"protocol": protocol},
            }
        )

    not_after = cert.get("notAfter") if cert else None
    if not_after:
        expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = (expires_at - datetime.now(timezone.utc)).days
        if days_left < 0:
            severity, title = "critical", "TLS sertifikasinin suresi dolmus"
        elif days_left < 14:
            severity, title = "high", f"TLS sertifikasinin suresi {days_left} gun icinde doluyor"
        elif days_left < 30:
            severity, title = "medium", f"TLS sertifikasinin suresi {days_left} gun icinde doluyor"
        else:
            severity, title = "info", f"TLS sertifikasi {days_left} gun daha gecerli"
        findings.append(
            {
                "module": "headers_tls",
                "severity": severity,
                "title": title,
                "description": f"Sertifika bitis tarihi: {not_after}",
                "evidence": {"not_after": not_after, "days_left": days_left},
            }
        )

    return findings


def run(domain: str) -> list[dict]:
    return check_headers(domain) + check_tls(domain)
