
# 최고금리 찾기 · 세후수령액 계산기 (Streamlit)

이 레포는 **모네타 '최고금리' 기능을 벤치마킹**한 데모입니다.  
샘플 데이터(`rates_sample.csv`)로 동작하며, 실제 서비스 시에는 **공식 비교/공시 데이터를 검증 후** CSV/DB로 연동하세요.

## 실행 (로컬)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포 (Streamlit Community Cloud)
1. GitHub에 이 폴더를 그대로 커밋/푸시합니다.
2. https://streamlit.io/cloud 에서 **New app** → GitHub 레포 연결 → `app.py` 선택
3. (선택) 데이터 갱신은 CSV를 교체하거나 DB 연동으로 확장하세요.

## 데이터 컬럼 (샘플)
- institution, group, productType(예금/적금), savingMethod, productName, termMonths, rateBase, rateMax, rateCalcType(복리/단리), minAmount, maxAmount, onlineOnly, region, conditions, sourceUrl, lastVerifiedAt

## 주의
- 본 레포의 금리는 **임의의 샘플값**입니다.
- 세후 계산은 단순화된 가정(월복리/단리, 말일 납입 등)을 사용합니다. 실제 상품의 이자계산 규정과 다를 수 있습니다.
