"""HTTP security header + TLS/certificate posture checks.

Entirely passive: a single GET (HTTPS, falling back to HTTP if the
target doesn't serve TLS) plus a TLS handshake attempt against the
target's own port 443. No injection payloads, no credential attempts.
"""

import socket
import ssl
from datetime import datetime, timezone

import requests

from app.services.scanners import http_utils

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
    try:
        resp, base_url = http_utils.get(domain, allow_redirects=True)
    except requests.RequestException as exc:
        return [
            {
                "module": "headers_tls",
                "key": "unreachable",
                "severity": "medium",
                "title": "Hedefe HTTP(S) uzerinden erisilemedi",
                "description": f"{domain} adresine ne HTTPS ne de HTTP ile baglanilabildi: {exc}",
                "evidence": {"domain": domain},
            }
        ]

    if base_url.startswith("http://"):
        findings.append(
            {
                "module": "headers_tls",
                "key": "https-not-supported",
                "severity": "medium",
                "title": "Hedef HTTPS uzerinden erisilemedi, duz HTTP'ye dusuldu",
                "description": (
                    "https:// baglantisi basarisiz oldu, http:// ile devam edildi. Tum trafik "
                    "sifrelenmeden tasiniyor olabilir."
                ),
                "evidence": {"base_url": base_url},
            }
        )

    for header, (severity, description) in REQUIRED_HEADERS.items():
        if header not in resp.headers:
            findings.append(
                {
                    "module": "headers_tls",
                    "key": f"missing-header:{header}",
                    "severity": severity,
                    "title": f"Eksik guvenlik header'i: {header}",
                    "description": description,
                    "evidence": {"url": base_url},
                }
            )

    server_header = resp.headers.get("Server")
    if server_header:
        findings.append(
            {
                "module": "headers_tls",
                "key": "server-header-disclosure",
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
                    "key": f"insecure-cookie:{cookie.name}",
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
                "key": "headers-ok",
                "severity": "info",
                "title": "Temel guvenlik header'lari mevcut",
                "description": "Kontrol edilen zorunlu header'larin tumu bulundu.",
                "evidence": {"url": base_url},
            }
        )

    return findings


def check_tls(domain: str) -> list[dict]:
    context = ssl.create_default_context()

    try:
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version()
    except (ConnectionRefusedError, TimeoutError, socket.gaierror) as exc:
        return [
            {
                "module": "headers_tls",
                "key": "https-port-closed",
                "severity": "info",
                "title": "Hedef 443 portunda HTTPS sunmuyor",
                "description": f"{domain}:443 uzerinde baglanti kurulamadi ({exc}). Site sadece HTTP uzerinden calisiyor olabilir.",
                "evidence": {"domain": domain},
            }
        ]
    except (OSError, ssl.SSLError) as exc:
        return [
            {
                "module": "headers_tls",
                "key": "tls-handshake-failed",
                "severity": "medium",
                "title": "TLS handshake basarisiz",
                "description": f"{domain}:443 uzerinde TLS baglantisi kurulamadi: {exc}",
                "evidence": {"domain": domain},
            }
        ]

    findings: list[dict] = []

    if protocol in WEAK_TLS_VERSIONS:
        findings.append(
            {
                "module": "headers_tls",
                "key": "weak-tls-protocol",
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
                "key": "tls-protocol",
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
                "key": "tls-cert-expiry",
                "severity": severity,
                "title": title,
                "description": f"Sertifika bitis tarihi: {not_after}",
                "evidence": {"not_after": not_after, "days_left": days_left},
            }
        )

    return findings


def run(domain: str) -> list[dict]:
    return check_headers(domain) + check_tls(domain)
