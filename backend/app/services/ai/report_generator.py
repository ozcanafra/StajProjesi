"""AI-driven synthesis of raw scan findings into a risk-scored report,
plus a Q&A chat layer over that report. This is the differentiating
layer of the product: instead of dumping raw tool output, findings are
turned into a prioritized, explained, remediation-oriented narrative.

Uses Google's Gemini API (free tier available) via the google-genai SDK.
"""

import json
from typing import Any

from google import genai
from google.genai import errors, types

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

prioritized_findings listesini risk siralamasina gore (en kritik once) diz. \
Eger sana onceki taramayla kiyaslanmis bir degisim (trend) bilgisi verilirse, \
executive_summary'nin icine bu degisimi (yeni/kapatilan bulgu sayisi, risk \
yonelimi) mutlaka kisaca yansit. Turkce yaz."""

CHAT_SYSTEM_PROMPT = """Sen bir siber guvenlik danismanisin. Kullaniciya, elindeki \
tarama raporu hakkinda sorulan sorulari, rapor baglamini kullanarak Turkce ve \
anlasilir bicimde yanitla. Rapor disindaki konularda spekulasyon yapma, bulgulara \
dayan."""


def _client() -> genai.Client | None:
    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _fallback_report(findings: list[dict], trend_context: str | None = None) -> dict[str, Any]:
    severity_weight = {"info": 0, "low": 10, "high": 40, "critical": 60, "medium": 25}
    score = min(100, sum(severity_weight.get(f["severity"], 0) for f in findings))
    prioritized = sorted(findings, key=lambda f: severity_weight.get(f["severity"], 0), reverse=True)
    summary = (
        "AI rapor katmani yapilandirilmamis (GEMINI_API_KEY tanimli degil). "
        f"Toplam {len(findings)} ham bulgu tespit edildi, agirliklandirilmis risk skoru: {score}."
    )
    if trend_context:
        summary += f" {trend_context}"
    return {
        "risk_score": score,
        "executive_summary": summary,
        "technical_summary": "Detayli teknik yorum icin GEMINI_API_KEY ve GEMINI_MODEL ayarlarini yapilandirin.",
        "prioritized_findings": [
            {
                "title": f["title"],
                "severity": f["severity"],
                "business_impact": f.get("description", ""),
                "remediation": "AI destekli remediation onerisi icin GEMINI_API_KEY gereklidir.",
            }
            for f in prioritized[:10]
        ],
    }


def generate_report(target_domain: str, findings: list[dict], trend_context: str | None = None) -> dict[str, Any]:
    client = _client()
    if client is None:
        return _fallback_report(findings, trend_context)

    user_prompt = (
        f"Hedef domain: {target_domain}\n\nHam bulgular (JSON):\n"
        f"{json.dumps(findings, ensure_ascii=False, indent=2)}"
    )
    if trend_context:
        user_prompt += f"\n\nOnceki taramaya gore degisim: {trend_context}"

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        data = json.loads(response.text)
        data.setdefault("prioritized_findings", [])
        data["risk_score"] = float(data.get("risk_score", 0))
        return data
    except (errors.APIError, json.JSONDecodeError, ValueError, KeyError, AttributeError):
        return _fallback_report(findings, trend_context)


def chat_about_report(report: Any, history: list[dict], question: str) -> str:
    client = _client()
    if client is None:
        return (
            "AI sohbet ozelligi su an yapilandirilmamis. Lutfen GEMINI_API_KEY ve "
            "GEMINI_MODEL ortam degiskenlerini ayarlayin."
        )

    context = (
        f"Risk skoru: {report.risk_score}\n"
        f"Yonetici ozeti: {report.executive_summary}\n"
        f"Teknik ozet: {report.technical_summary}\n"
        f"Onceliklendirilmis bulgular (JSON): "
        f"{json.dumps(report.prioritized_findings, ensure_ascii=False)}"
    )

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"Rapor baglami:\n{context}")]),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="Rapor baglamini aldim, sorularinizi yanitlamaya hazirim.")],
        ),
    ]
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT, max_output_tokens=1024),
        )
        return response.text or ""
    except errors.APIError as exc:
        return f"AI servisine ulasilamadi: {exc}"
