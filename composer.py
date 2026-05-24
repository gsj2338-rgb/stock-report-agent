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
        """Generate a brief plain-text summary for the email body. Falls back to a minimal message on failure."""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            date = data.get("date", "날짜 미상")
            prices = data.get("prices", [])
            all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
            disclosures = data.get("disclosures", [])
            semi_news = data.get("semi_news", [])

            prompt = f"""{date} 기준 한국 주식 분석 리포트 요약을 이메일 본문용 짧은 텍스트로 작성해주세요.

형식:
- 3~5문장 핵심 요약 (불릿 없이 자연스러운 문단)
- 주요 등락 종목 1~2개 수치와 함께 언급
- 마지막 문장은 "상세 내용은 첨부된 PDF 리포트를 확인해주세요." 로 마무리

데이터:
종목 시세: {json.dumps(prices[:6], ensure_ascii=False)}
애널리스트 리포트: {json.dumps(all_reports[:3], ensure_ascii=False)}
공시: {json.dumps(disclosures[:3], ensure_ascii=False)}
반도체 뉴스: {json.dumps(semi_news[:2], ensure_ascii=False)}

200자 이내로 간결하게 작성하세요."""

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Summary composer error: {e}")
            date = data.get("date", "")
            return f"{date} 한국 주식 분석 리포트입니다.\n상세 내용은 첨부된 PDF 리포트를 확인해주세요."

    def compose_sections(self, data: dict) -> dict:
        """
        Generate structured AI analysis text for each PDF section.
        Returns dict with keys: market_overview, dart_summary, semi_summary.
        Falls back to {} on any failure.
        """
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            date = data.get("date", "날짜 미상")
            prices = data.get("prices", [])
            all_reports = data.get("analyst_reports", []) + data.get("broker_reports", [])
            disclosures = data.get("disclosures", [])
            semi_news = data.get("semi_news", [])

            prompt = f"""다음 데이터를 분석하여 JSON 형식으로 응답해주세요. 마크다운이나 설명 없이 순수 JSON만 반환하세요.

반환 형식:
{{
  "market_overview": "시장 전반 분석 3~4문장. 주요 종목 등락률 수치 포함.",
  "dart_summary": "주요 공시 중 투자자가 주목해야 할 사항 2~3문장.",
  "semi_summary": "반도체 글로벌 동향 한국어 번역 요약 2~3문장. 수치 포함."
}}

날짜: {date}
종목 시세 (최대 8개): {json.dumps(prices[:8], ensure_ascii=False)}
애널리스트 리포트 (최대 5개): {json.dumps(all_reports[:5], ensure_ascii=False)}
DART 공시 (최대 5개): {json.dumps(disclosures[:5], ensure_ascii=False)}
반도체 뉴스 (최대 3개): {json.dumps(semi_news[:3], ensure_ascii=False)}

각 섹션에 데이터가 없으면 "데이터를 수집하지 못했습니다." 로 작성하세요.
반드시 유효한 JSON만 반환하세요."""

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"compose_sections error: {e}")
            return {}

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
