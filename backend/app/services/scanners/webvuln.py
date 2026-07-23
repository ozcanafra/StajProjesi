"""Passive web-vulnerability checks: outdated JS libraries, exposed
sensitive paths/directory listings, insecure form configuration.

Everything here is a plain GET against publicly served content - no
injection payloads, no authentication bypass, no active exploitation.
Content-based validators are used (not just HTTP 200) to avoid false
positives on single-page apps that return 200 for every path.
"""

import re
from collections.abc import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 8
HEADERS = {"User-Agent": "SentraScan/1.0"}

# library name -> (regex capturing the version from a script src, minimum safe version)
KNOWN_LIBRARIES: dict[str, tuple[re.Pattern, tuple[int, int, int]]] = {
    "jQuery": (re.compile(r"jquery[.\-]?(\d+\.\d+\.\d+)", re.I), (3, 5, 0)),
    "Bootstrap": (re.compile(r"bootstrap[.\-]?(\d+\.\d+\.\d+)", re.I), (4, 3, 1)),
    "AngularJS": (re.compile(r"angular[.\-]?(\d+\.\d+\.\d+)", re.I), (1, 8, 0)),
}


def _is_git_head(text: str) -> bool:
    return text.strip().startswith("ref:")


def _is_env_file(text: str) -> bool:
    head = text[:500]
    return "<html" not in head.lower() and "=" in text and "\n" in text


def _is_wp_config_backup(text: str) -> bool:
    return "<html" not in text[:500].lower() and ("DB_NAME" in text or "wpdb" in text)


SENSITIVE_PATHS: dict[str, tuple[str, str, Callable[[str], bool]]] = {
    "/.git/HEAD": ("critical", "Git deposu (.git) disariya acik - kaynak kod/gecmis sizintisi riski", _is_git_head),
    "/.env": ("critical", "Ortam degiskenleri (.env) dosyasi disaridan erisilebilir", _is_env_file),
    "/wp-config.php.bak": (
        "high",
        "WordPress yapilandirma yedegi disariya acik olabilir",
        _is_wp_config_backup,
    ),
}

LISTING_PATHS = ["/uploads/", "/backup/", "/assets/", "/files/", "/images/"]


def _version_tuple(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(p) for p in text.split("."))
    except ValueError:
        return None


def check_outdated_js_libraries(soup: BeautifulSoup) -> list[dict]:
    script_srcs = [tag.get("src", "") for tag in soup.find_all("script") if tag.get("src")]

    findings: list[dict] = []
    seen: set[str] = set()
    for src in script_srcs:
        for name, (pattern, min_version) in KNOWN_LIBRARIES.items():
            if name in seen:
                continue
            match = pattern.search(src)
            if not match:
                continue
            version = _version_tuple(match.group(1))
            if version is None or version >= min_version:
                continue
            seen.add(name)
            findings.append(
                {
                    "module": "webvuln",
                    "key": f"outdated-js-library:{name}",
                    "severity": "medium",
                    "title": f"Guncel olmayan JS kutuphanesi: {name} {match.group(1)}",
                    "description": (
                        f"{src} dosyasinda tespit edildi. Bilinen guvenlik acigi olan bir surum "
                        "kullaniliyor olabilir, guncel surume yukseltilmesi onerilir."
                    ),
                    "evidence": {"src": src, "version": match.group(1)},
                }
            )
    return findings


def check_insecure_forms(soup: BeautifulSoup) -> list[dict]:
    findings: list[dict] = []
    for idx, form in enumerate(soup.find_all("form")):
        action = form.get("action") or ""
        method = (form.get("method") or "get").lower()
        has_password = form.find("input", {"type": "password"}) is not None

        if action.lower().startswith("http://"):
            findings.append(
                {
                    "module": "webvuln",
                    "key": f"mixed-content-form:{idx}",
                    "severity": "high",
                    "title": "Form, HTTPS sayfadan HTTP adresine veri gonderiyor",
                    "description": f"Form action='{action}' - mixed content, veri sifrelenmeden gonderilebilir.",
                    "evidence": {"action": action},
                }
            )

        if has_password and method == "get":
            findings.append(
                {
                    "module": "webvuln",
                    "key": f"password-via-get:{idx}",
                    "severity": "high",
                    "title": "Sifre alani GET metoduyla gonderiliyor",
                    "description": (
                        "Sifre URL uzerinden (GET) gonderildigi icin tarayici gecmisinde veya sunucu "
                        "loglarinda acik metin olarak kalabilir."
                    ),
                    "evidence": {"method": method},
                }
            )

    return findings


def check_sensitive_paths(domain: str) -> list[dict]:
    base = f"https://{domain}"
    findings: list[dict] = []
    for path, (severity, description, validator) in SENSITIVE_PATHS.items():
        try:
            resp = requests.get(urljoin(base, path), timeout=REQUEST_TIMEOUT, headers=HEADERS)
        except requests.RequestException:
            continue
        if resp.status_code == 200 and validator(resp.text):
            findings.append(
                {
                    "module": "webvuln",
                    "key": f"exposed-path:{path}",
                    "severity": severity,
                    "title": f"Hassas dosya disariya acik: {path}",
                    "description": description,
                    "evidence": {"path": path},
                }
            )
    return findings


def check_directory_listing(domain: str) -> list[dict]:
    base = f"https://{domain}"
    findings: list[dict] = []
    for path in LISTING_PATHS:
        try:
            resp = requests.get(urljoin(base, path), timeout=REQUEST_TIMEOUT, headers=HEADERS)
        except requests.RequestException:
            continue
        if resp.status_code == 200 and re.search(r"index of /", resp.text, re.I):
            findings.append(
                {
                    "module": "webvuln",
                    "key": f"directory-listing:{path}",
                    "severity": "medium",
                    "title": f"Acik dizin listeleme: {path}",
                    "description": (
                        "Sunucu bu dizin icin otomatik dosya listesi donduruyor, hassas dosyalarin "
                        "ifsasina yol acabilir."
                    ),
                    "evidence": {"path": path},
                }
            )
    return findings


def run(domain: str) -> list[dict]:
    findings: list[dict] = []

    try:
        resp = requests.get(f"https://{domain}", timeout=REQUEST_TIMEOUT, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")
        findings.extend(check_outdated_js_libraries(soup))
        findings.extend(check_insecure_forms(soup))
    except requests.RequestException:
        pass

    findings.extend(check_sensitive_paths(domain))
    findings.extend(check_directory_listing(domain))

    if not findings:
        findings.append(
            {
                "module": "webvuln",
                "key": "webvuln-clean",
                "severity": "info",
                "title": "Pasif web-vuln kontrollerinde belirgin bir sorun bulunamadi",
                "description": "Eski JS kutuphanesi, acik dizin listeleme veya guvensiz form ayari tespit edilmedi.",
                "evidence": {},
            }
        )

    return findings
