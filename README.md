# 한국 주식 애널리스트 리포트 에이전트

매일 07:00 KST에 한국 주식 애널리스트 분석 리포트를 Gmail로 발송하는 Python 에이전트.

## 데이터 소스
- **DART OpenAPI** — 기업 공시, 재무 데이터 (공식 무료 API)
- **KIS Open API** — 실시간 주가, 거래량 (한국투자증권 공식 API)
- **네이버 금융** — 애널리스트 투자의견, 목표주가, 컨센서스
- **주요 증권사** — 삼성, 미래에셋, KB, 키움, NH 최신 리포트
- **TrendForce / SEMI.org** — 글로벌 반도체 동향 (한국어 번역)

## 설치

### 1. Clone & Setup
```bash
git clone <repo-url>
cd stock-report-agent
chmod +x setup.sh && ./setup.sh
```

### 2. API 키 발급
| 서비스 | 발급 URL |
|--------|---------|
| DART API | https://opendart.fss.or.kr/uat/uia/eAPIPcpnInfoInqire.do |
| KIS Open API | https://apiportal.koreainvestment.com/ (한투 계좌 필요) |
| Anthropic | https://console.anthropic.com/ |
| Gmail App Password | Google 계정 → 보안 → 앱 비밀번호 |

### 3. .env 설정
```bash
cp .env.example .env
# 각 항목을 실제 키로 채우세요
```

### 4. 테스트 실행
```bash
source .venv/bin/activate
python main.py --date 2026-05-23
```

### 5. cron 등록 (매일 07:00 KST, 월~금)
```bash
crontab -e
```
다음 줄 추가 (YOUR_USERNAME을 실제 Mac 사용자명으로 교체):
```
0 7 * * 1-5 cd /Users/YOUR_USERNAME/stock-report-agent && source .venv/bin/activate && python main.py >> logs/report.log 2>&1
```

로그 디렉토리 생성:
```bash
mkdir -p logs
```

## 다른 Mac에서 사용하기
1. `git clone` 후 `./setup.sh` 실행
2. `.env` 파일을 새로 설정 (또는 기존 .env 내용 복사)
3. cron 등록

## 리포트 구성
1. 시장 개요 (KOSPI/KOSDAQ 주요 종목)
2. 섹터별 종목 분석 (매수/매도 균형 있게 제시)
3. 주요 DART 공시
4. 글로벌 반도체 동향 (한국어 번역, 출처 명시)
5. 전체 출처 목록

바이오/제약 섹터 제외. 숫자·수치 중심 구성.
