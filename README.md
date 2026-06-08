# 📱 한의학사전: 온디바이스 한의·중의 통합 한자 사전 앱

## 요약

**HanjaDic**는 한의/중의 의료 문헌을 위한 온디바이스 통합 한자 사전 애플리케이션입니다.

**OCR 텍스트 추출 + SQLite 기반 검색**을 핵심으로, 의서의 한자를 촬영하면 즉시 독음과 의미를 제공합니다.

### 핵심 특징
- 기본 표준 한자 단어 수록
- 동의보감 등 주요 의서의 체계적 데이터 수집
- 본초(약재), 방제(처방), 혈위/질병 정보 통합 데이터베이스
- 로컬 SQLite 기반으로 빠른 검색 (인터넷 불필요)
- 간체/번체 자동 정규화

## 아키텍쳐

```
[카메라 촬영 / 텍스트 입력]
        ⬇️
1. 온디바이스 OCR 
   ➡️ 한자 텍스트 추출 (간체/번체 동시 대응)
        ⬇️
2. SQLite 사전 DB 검색
   ➡️ 음/뜻, 본초/방제 기초 정보 즉시 출력
```

## 핵심 구성요소

### 1. OCR 모듈 (간체/번체 통합)
- iOS: `Vision Framework`
- Android: `Google ML Kit`
- 간체자 ↔ 번체자 정규화로 DB 검색 정확도 향상

### 2. 로컬 SQLite 데이타베이스 (~40MB)
한방 의학 데이터를 DB화하여 오프라인 즉시 검색

**포함 데이터:**
- 한방 본초(약재) 사전: ~500여 종의 한약재 정보 (기미, 귀경, 효능)
- 표준 방제(처방) 사전: 방약합편, 동의보감 등 주요 처방
- 한자어 사전: 의학 용어 및 일반 한자어
- 상용 한자 사전: 기본 자전 데이터
- 경혈/질병 정보

## 개발 스택

### 백앤드, 데이타 처리
```
Python 3.x
- SQLite: 로컬 데이터베이스
- PyPDF, PaddleOCR: 문서 처리 및 OCR
```

### 프론트엔드
- **iOS**: SwiftUI + Vision Framework
- **Android**: Kotlin + ML Kit (예정)

## 지금 시작하기

### 준비해야할 것
```bash
python 3.8+
pip install -r requirements.txt
```

### 데이타 처리 스크립트
```bash
# 동의보감 데이터 추출
python scripts/extract_dongeuibogam_v2.py

# 처방 데이터 로드
python scripts/load_formula.py

# 한자어 데이터 로드
python scripts/load_hanja_words.py

# 혈위/질병 데이터 로드
python scripts/load_acupoints_diseases.py
```

## 참고

- **Traditional Medicine Texts**: 동의보감, 경악전서, 상한론
- **Data Sources**: 한국한의학연구원(KIOM), AI Hub, 국립국어원

## 라이센스

Copyright © 2026 Chester Kim. All rights reserved.
