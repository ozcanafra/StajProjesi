"""AI-driven synthesis of raw scan findings into a risk-scored report,
plus a Q&A chat layer over that report. This is the differentiating
layer of the product: instead of dumping raw tool output, findings are
turned into a prioritized, explained, remediation-oriented narrative.

Runs against a local Ollama server, so no API key, no per-request cost
and no data leaving the machine - the scan findings stay on the host
that produced them.
"""

import json
from typing import Any

import requests

from app.core.config import settings

SYSTEM_PROMPT = """Sen bir siber guvenlik analistisin. Sana bir hedef domain icin \
otomatik taramalardan gelen ham bulgular verilecek. Gorevin bunlari sentezleyip \
tam olarak su JSON semasina uyan bir yanit uretmek:

{
  "risk_score": <0-100 arasi sayi, genel risk skoru>,
  "executive_summary": "<yonetim icin 3-5 cumlelik ozet, teknik jargon az>",
  "technical_summary": "<teknik ekip icin daha detayli ozet>",
  "prioritized_findings": [
    {
      "title": "<bulgu basligi>",
      "severity": "<info|low|medium|high|critical>",
      "business_impact": "<bu bulgu neden onemli, olasi etkisi>",
      "remediation": "<somut, uygulanabilir duzeltme adimlari>"
    }
  ]
}

Sadece JSON dondur, aciklama veya markdown kod bloku ekleme. \
prioritized_findings listesini risk siralamasina gore (en kritik once) diz. \
Eger sana onceki taramayla kiyaslanmis bir degisim (trend) bilgisi verilirse, \
executive_summary'nin icine bu degisimi (yeni/kapatilan bulgu sayisi, risk \
yonelimi) mutlaka kisaca yansit. Turkce yaz."""

CHAT_SYSTEM_PROMPT = """Sen bir siber guvenlik danismanisin. Kullaniciya, elindeki \
tarama raporu hakkinda sorulan sorulari, rapor baglamini kullanarak Turkce ve \
anlasilir bicimde yanitla. Rapor disindaki konularda spekulasyon yapma, bulgulara \
dayan."""

SETUP_HINT = (
    "Ollama sunucusuna ulasilamadi. Kurulum: https://ollama.com/download adresinden "
    f"Ollama'yi kurup `ollama pull {settings.OLLAMA_MODEL}` ile modeli indirin, "
    "docker-compose kullaniyorsaniz `ollama` servisinin ayakta oldugunu kontrol edin."
)


def _chat(messages: list[dict], json_mode: bool, num_predict: int) -> str:
    """POSTs to Ollama's /api/chat and returns the assistant message text.

    Raises requests.RequestException when the server is unreachable or the
    model is missing, so callers can degrade to a non-AI response.
    """
    payload: dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }
    if json_mode:
        payload["format"] = "json"

    resp = requests.post(
        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json=payload,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _fallback_report(findings: list[dict], trend_context: str | None = None) -> dict[str, Any]:
    severity_weight = {"info": 0, "low": 10, "high": 40, "critical": 60, "medium": 25}
    score = min(100, sum(severity_weight.get(f["severity"], 0) for f in findings))
    prioritized = sorted(findings, key=lambda f: severity_weight.get(f["severity"], 0), reverse=True)
    summary = (
        "AI rapor katmani devrede degil, bulgular kural tabanli olarak ozetlendi. "
        f"Toplam {len(findings)} ham bulgu tespit edildi, agirliklandirilmis risk skoru: {score}."
    )
    if trend_context:
        summary += f" {trend_context}"
    return {
        "risk_score": score,
        "executive_summary": summary,
        "technical_summary": SETUP_HINT,
        "prioritized_findings": [
            {
                "title": f["title"],
                "severity": f["severity"],
                "business_impact": f.get("description", ""),
                "remediation": "AI destekli remediation onerisi icin Ollama sunucusu gereklidir.",
            }
            for f in prioritized[:10]
        ],
    }


def generate_report(target_domain: str, findings: list[dict], trend_context: str | None = None) -> dict[str, Any]:
    user_prompt = (
        f"Hedef domain: {target_domain}\n\nHam bulgular (JSON):\n"
        f"{json.dumps(findings, ensure_ascii=False, indent=2)}"
    )
    if trend_context:
        user_prompt += f"\n\nOnceki taramaya gore degisim: {trend_context}"

    try:
        content = _chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            num_predict=4096,
        )
        data = json.loads(content)
        data.setdefault("prioritized_findings", [])
        data["risk_score"] = float(data.get("risk_score", 0))
        return data
    except (requests.RequestException, json.JSONDecodeError, ValueError, KeyError, TypeError):
        return _fallback_report(findings, trend_context)


def chat_about_report(report: Any, history: list[dict], question: str) -> str:
    context = (
        f"Risk skoru: {report.risk_score}\n"
        f"Yonetici ozeti: {report.executive_summary}\n"
        f"Teknik ozet: {report.technical_summary}\n"
        f"Onceliklendirilmis bulgular (JSON): "
        f"{json.dumps(report.prioritized_findings, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Rapor baglami:\n{context}"},
        {"role": "assistant", "content": "Rapor baglamini aldim, sorularinizi yanitlamaya hazirim."},
    ]
    messages.extend({"role": msg["role"], "content": msg["content"]} for msg in history)
    messages.append({"role": "user", "content": question})

    try:
        return _chat(messages, json_mode=False, num_predict=1024)
    except (requests.RequestException, KeyError, ValueError) as exc:
        return f"AI servisine ulasilamadi ({exc.__class__.__name__}). {SETUP_HINT}"
