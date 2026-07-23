"""AI-driven synthesis of raw scan findings into a risk-scored report,
plus a Q&A chat layer over that report. This is the differentiating
layer of the product: instead of dumping raw tool output, findings are
turned into a prioritized, explained, remediation-oriented narrative.
"""

import json
from typing import Any

import anthropic

from app.core.config import settings

SYSTEM_PROMPT = """Sen bir siber guvenlik analistisin. Sana bir hedef domain icin \
otomatik taramalardan gelen ham bulgular verilecek. Gorevin bunlari sentezleyip \
ONLY valid JSON (baska hicbir metin olmadan) formatinda su sekilde yanitlamak:

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

prioritized_findings listesini risk siralamasina gore (en kritik once) diz. \
Turkce yaz. JSON disinda hicbir aciklama ekleme."""

CHAT_SYSTEM_PROMPT = """Sen bir siber guvenlik danismanisin. Kullaniciya, elindeki \
tarama raporu hakkinda sorulan sorulari, rapor baglamini kullanarak Turkce ve \
anlasilir bicimde yanitla. Rapor disindaki konularda spekulasyon yapma, bulgulara \
dayan."""


def _client() -> anthropic.Anthropic | None:
    if not settings.ANTHROPIC_API_KEY or not settings.ANTHROPIC_MODEL:
        return None
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _fallback_report(findings: list[dict]) -> dict[str, Any]:
    severity_weight = {"info": 0, "low": 10, "high": 40, "critical": 60, "medium": 25}
    score = min(100, sum(severity_weight.get(f["severity"], 0) for f in findings))
    prioritized = sorted(findings, key=lambda f: severity_weight.get(f["severity"], 0), reverse=True)
    return {
        "risk_score": score,
        "executive_summary": (
            "AI rapor katmani yapilandirilmamis (ANTHROPIC_API_KEY tanimli degil). "
            f"Toplam {len(findings)} ham bulgu tespit edildi, agirliklandirilmis risk skoru: {score}."
        ),
        "technical_summary": "Detayli teknik yorum icin ANTHROPIC_API_KEY ve ANTHROPIC_MODEL ayarlarini yapilandirin.",
        "prioritized_findings": [
            {
                "title": f["title"],
                "severity": f["severity"],
                "business_impact": f.get("description", ""),
                "remediation": "AI destekli remediation onerisi icin ANTHROPIC_API_KEY gereklidir.",
            }
            for f in prioritized[:10]
        ],
    }


def generate_report(target_domain: str, findings: list[dict]) -> dict[str, Any]:
    client = _client()
    if client is None:
        return _fallback_report(findings)

    user_prompt = (
        f"Hedef domain: {target_domain}\n\nHam bulgular (JSON):\n"
        f"{json.dumps(findings, ensure_ascii=False, indent=2)}"
    )

    try:
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        data = json.loads(text)
        data.setdefault("prioritized_findings", [])
        data["risk_score"] = float(data.get("risk_score", 0))
        return data
    except (anthropic.APIError, json.JSONDecodeError, ValueError, KeyError):
        return _fallback_report(findings)


def chat_about_report(report: Any, history: list[dict], question: str) -> str:
    client = _client()
    if client is None:
        return (
            "AI sohbet ozelligi su an yapilandirilmamis. Lutfen ANTHROPIC_API_KEY ve "
            "ANTHROPIC_MODEL ortam degiskenlerini ayarlayin."
        )

    context = (
        f"Risk skoru: {report.risk_score}\n"
        f"Yonetici ozeti: {report.executive_summary}\n"
        f"Teknik ozet: {report.technical_summary}\n"
        f"Onceliklendirilmis bulgular (JSON): "
        f"{json.dumps(report.prioritized_findings, ensure_ascii=False)}"
    )

    messages = [{"role": "user", "content": f"Rapor baglami:\n{context}"}]
    messages.append({"role": "assistant", "content": "Rapor baglamini aldim, sorularinizi yanitlamaya hazirim."})
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    try:
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")
    except anthropic.APIError as exc:
        return f"AI servisine ulasilamadi: {exc}"
