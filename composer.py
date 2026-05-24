import anthropic
import json
import logging
import re

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 한국 주식 시장 전문 애널리스트 보조입니다.
제공된 데이터를 바탕으로 일간 주식 분석 리포트를 HTML 형식으로 작성합니다.

작성 원칙:
1. 매수/매도 양측 의견을 반드시 균형있게 제시하세요. 한쪽 의견만 있어도 중립적 위험 요인을 명시하세요.
2. 숫자 중심으로 작성하세요: 목표주가, 등락률, 컨센서스 비율, 거래량 등 수치를 우선시하세요.
3. 바이오/제약 섹터는 제외하세요.
4. 해외 자료는 반드시 한국어로 번역하세요.
5. 모든 정보에 출처를 명시하세요.
6. 객관적이고 사실 중심으로 작성하세요. 투자 권유는 하지 마세요."""


class Composer:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def compose(self, data: dict) -> str:
        """Takes aggregated collector data and returns an HTML report string. Falls back to error HTML on failure."""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = self._build_prompt(data)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Composer error: {e}")
            return f"""<html><body>
<h2>리포트 생성 오류</h2>
<p>Claude API 호출 중 오류가 발생했습니다: {e}</p>
<p>데이터 수집은 완료되었으나 요약 생성에 실패했습니다. API 키와 네트워크를 확인해주세요.</p>
</body></html>"""

    def compose_summary(self, data: dict) -> str:
        """
        Generate a brief narrative paragraph for the email body market summary section.
        Falls back to a minimal message on failure.
        """
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            date = data.get("date", "날짜 미상")
            prices = data.get("prices", [])
            all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
            semi_news = data.get("semi_news", [])

            prompt = f"""{date} 기준 한국 주식 시장 요약을 3~4문장으로 작성해주세요.

요구사항:
- 자연스러운 서술형 문단 (불릿 없이)
- 주요 등락 종목 1~2개를 수치(%)와 함께 언급
- 오늘 주목할 이슈 또는 테마 한 줄
- 마지막 문장은 절대 포함하지 마세요 ("상세 내용은..." 문장은 호출 측에서 추가)

종목 시세: {json.dumps(prices[:8], ensure_ascii=False)}
애널리스트 리포트 요약: {json.dumps(all_reports[:4], ensure_ascii=False)}
반도체 뉴스: {json.dumps(semi_news[:2], ensure_ascii=False)}

150자 이내로 작성하세요."""

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Summary composer error: {e}")
            date = data.get("date", "")
            return f"{date} 한국 주식 분석 리포트입니다."

    def compose_sections(self, data: dict) -> dict:
        """
        Generate deep structured AI analysis for the PDF report using two focused API calls
        to avoid JSON truncation:
          Call 1 — market_overview, stock_analysis, dart_summary
          Call 2 — semi_analysis (what/why/impact per item + kr_implications)

        Returns merged dict. Falls back gracefully per call.
        """
        client = anthropic.Anthropic(api_key=self.api_key)
        date = data.get("date", "날짜 미상")
        prices = data.get("prices", [])
        all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
        disclosures = data.get("disclosures", [])
        semi_news   = data.get("semi_news", [])

        grouped: dict[str, list] = {}
        for r in all_reports:
            grouped.setdefault(r.get("stock_name", "기타"), []).append(r)
        grouped_summary = {
            name: [{"broker": r.get("broker", ""), "opinion": r.get("opinion", ""),
                    "target_price": r.get("target_price", ""), "title": r.get("title", "")}
                   for r in reps]
            for name, reps in grouped.items()
        }

        result: dict = {}

        # ── Call 1: market / stock / dart ──────────────────────────────────
        has_reports = bool(grouped_summary)
        stock_instruction = (
            "리포트가 있는 종목만 포함. 각 종목 필드는 220자 이내 엄격 준수."
            if has_reports else
            "리포트 없음 → 빈 객체 {} 반환."
        )

        prompt1 = f"""한국 주식 전문 애널리스트로서 다음 데이터를 분석하여 JSON으로 응답하세요.
순수 JSON만 반환하세요. 코드블록(```) 금지.

반환 형식:
{{
  "market_overview": "시장 전반 3~4문장. 주요 등락 종목 수치 포함. 220자 이내.",
  "stock_analysis": {{
    "종목명": {{
      "bull_thesis": "매수 근거 2가지. 리포트 제목 기반. 수치 포함. 220자 이내.",
      "bear_thesis": "위험 요인 2가지. 220자 이내.",
      "key_metrics": "핵심 이슈 한 문장."
    }}
  }},
  "dart_summary": "공시 주목사항 2문장. 없으면 '해당일 주요 공시 없음.' 220자 이내."
}}

날짜: {date}
종목 시세: {json.dumps(prices[:12], ensure_ascii=False)}
종목별 리포트: {json.dumps(grouped_summary, ensure_ascii=False)}
DART 공시: {json.dumps(disclosures[:8], ensure_ascii=False)}

규칙:
- stock_analysis: {stock_instruction}
- 매수/매도 양측 균형
- 투자 권유 문구 금지
- 유효한 JSON만 반환"""

        try:
            r1 = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt1}],
            )
            raw1 = re.sub(r"^```(?:json)?\s*", "", r1.content[0].text.strip())
            raw1 = re.sub(r"\s*```$", "", raw1)
            result.update(json.loads(raw1))
        except Exception as e:
            logger.error(f"compose_sections call-1 error: {e}")

        # ── Call 2: semiconductor analysis ─────────────────────────────────
        n_semi = len(semi_news)
        semi_item_count = min(n_semi, 4) if n_semi > 0 else 2  # max 2 from knowledge when no data
        semi_instruction = (
            f"수집된 뉴스 {n_semi}건 분석. 최대 {semi_item_count}개 항목."
            if n_semi > 0 else
            f"수집된 뉴스 없음. {date} 기준 글로벌 반도체 핵심 이슈 2개만 지식 기반으로 작성."
        )

        prompt2 = f"""글로벌 반도체 전문 애널리스트로서 다음 데이터를 분석하여 JSON으로 응답하세요.
순수 JSON만 반환하세요. 코드블록(```) 금지.

반환 형식:
{{
  "semi_analysis": {{
    "overview": "반도체 시장 전반 동향 2문장. 200자 이내.",
    "items": [
      {{
        "headline": "뉴스 제목 (한국어 번역)",
        "what": "무슨 일: 사실·수치 중심 2문장. 250자 이내.",
        "why": "왜 발생: 원인 2문장. 250자 이내.",
        "impact": "예상 임팩트: 규모·시기·수혜기업 명시. 2문장. 250자 이내."
      }}
    ],
    "kr_implications": "국내 시사점: 삼성전자·SK하이닉스 각각 2~3문장. 250자 이내."
  }}
}}

날짜: {date}
반도체 뉴스: {json.dumps(semi_news[:6], ensure_ascii=False)}

- {semi_instruction}
- 수치(%, 달러, 웨이퍼 수 등) 최대한 포함
- 투자 권유 문구 금지
- 유효한 JSON만 반환"""

        try:
            r2 = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt2}],
            )
            raw2 = re.sub(r"^```(?:json)?\s*", "", r2.content[0].text.strip())
            raw2 = re.sub(r"\s*```$", "", raw2)
            result.update(json.loads(raw2))
        except Exception as e:
            logger.error(f"compose_sections call-2 error: {e}")

        return result

    def _build_prompt(self, data: dict) -> str:
        date = data.get("date", "날짜 미상")
        prices = data.get("prices", [])
        all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
        disclosures = data.get("disclosures", [])
        semi_news = data.get("semi_news", [])

        return f"""다음 데이터를 바탕으로 {date} 기준 한국 주식 일간 분석 리포트를 HTML 형식으로 작성해주세요.

## 요청 형식

다음 섹션을 포함한 HTML 이메일을 작성하세요:

1. **시장 개요** — 주요 종목 현재가, 등락률 표 (수치 중심)
2. **섹터별 종목 분석** — 종목별로 매수 의견과 매도/중립 의견을 균형있게 제시. 없는 쪽은 "해당 의견 없음 / 위험 요인:" 으로 대체
3. **주요 DART 공시** — 당일 주요 공시 요약
4. **글로벌 반도체 동향** — 해외 자료를 한국어로 번역하여 정리
5. **출처 전체 목록**

## 수집된 데이터

### 종목 시세
{json.dumps(prices, ensure_ascii=False, indent=2)}

### 애널리스트 리포트 (매수/매도 균형 필수)
{json.dumps(all_reports, ensure_ascii=False, indent=2)}

### DART 주요 공시
{json.dumps(disclosures, ensure_ascii=False, indent=2)}

### 글로벌 반도체 뉴스 (한국어 번역 필요)
{json.dumps(semi_news, ensure_ascii=False, indent=2)}

## HTML 스타일 요구사항
- 깔끔한 테이블 스타일 (border-collapse, 헤더 배경색 #2c3e50, 흰색 텍스트)
- 매수 의견: 초록색 (#27ae60), 매도/중립: 빨간색/주황색 (#e74c3c / #e67e22)
- 모바일 친화적 폰트 크기 (14px 이상)
- 각 섹션마다 출처 표기
- 투자 권유 면책 문구를 하단에 추가

반드시 완전한 HTML 문서를 반환하세요 (<!DOCTYPE html> 포함).
"""
