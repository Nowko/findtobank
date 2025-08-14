
import math
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="최고금리 찾기 · 세후수령액 계산기", page_icon="💰", layout="wide")

st.title("💰 최고금리 찾기 · 세후수령액 계산기")
st.caption("샘플 데이터 기반 데모입니다. 실제 가입 전 반드시 원문 페이지에서 금리와 조건을 확인하세요.")

# -------------------- 유틸 --------------------
@st.cache_data
def load_rates(default_path: str = "rates_sample.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(default_path)
    except Exception as e:
        st.warning("샘플 데이터 로드 실패: {}. 업로드 기능을 이용해 보세요.".format(e))
        df = pd.DataFrame()
    # 타입 정리
    if not df.empty:
        num_cols = ["termMonths", "rateBase", "rateMax", "minAmount", "maxAmount"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "onlineOnly" in df.columns:
            df["onlineOnly"] = df["onlineOnly"].astype(bool)
        if "lastVerifiedAt" in df.columns:
            pass
    return df

def calc_deposit(principal: float, annual_rate: float, months: int, compounding: str, tax_rate: float):
    i = annual_rate / 12.0
    if compounding == "월복리":
        gross = principal * ((1 + i) ** months)
    else:
        gross = principal * (1 + annual_rate * (months / 12.0))

    interest_gross = gross - principal
    tax = interest_gross * tax_rate
    net = principal + (interest_gross - tax)
    return gross, interest_gross, tax, net

def calc_saving(monthly: float, annual_rate: float, months: int, compounding: str, tax_rate: float):
    i = annual_rate / 12.0
    if compounding == "월복리":
        # 말일 납입 가정
        gross = monthly * (((1 + i) ** months - 1) / i) if i != 0 else monthly * months
    else:
        # 단리 간단 가정
        interest = monthly * (annual_rate / 12.0) * (months * (months + 1) / 2.0)
        gross = monthly * months + interest

    total_paid = monthly * months
    interest_gross = gross - total_paid
    tax = interest_gross * tax_rate
    net = total_paid + (interest_gross - tax)
    return gross, total_paid, interest_gross, tax, net

# -------------------- 데이터 --------------------
st.sidebar.header("데이터")
uploaded = st.sidebar.file_uploader("CSV 업로드(샘플 형식 참조)", type=["csv"], accept_multiple_files=False)
if uploaded:
    try:
        rates_df = pd.read_csv(uploaded)
        st.sidebar.success("업로드한 데이터로 계산합니다.")
    except Exception as e:
        st.sidebar.error(f"업로드 실패: {e}")
        rates_df = load_rates()
else:
    rates_df = load_rates()

if rates_df.empty:
    st.stop()

with st.expander("데이터 컬럼 가이드", expanded=False):
    st.markdown("""
    **필수 컬럼**
    - institution (문자) : 금융기관명
    - group (문자) : 기관군 (은행/저축은행/신협/새마을금고 등)
    - productType (문자) : '예금' | '적금'
    - savingMethod (문자) : 적금일 때 '정기적립식' | '자유적립식' (예금이면 빈칸 가능)
    - productName (문자) : 상품명
    - termMonths (숫자) : 기간(개월)
    - rateBase (숫자) : 기본금리 (예: 0.045)
    - rateMax (숫자) : 우대 포함 최대금리 (예: 0.055)
    - rateCalcType (문자) : '복리' | '단리'
    - minAmount, maxAmount (숫자)
    - onlineOnly (불리언)
    - region (문자) : '전국' 등
    - conditions (문자) : 우대 조건 요약
    - sourceUrl (문자) : 원문 링크
    - lastVerifiedAt (문자) : 검증 시점(YYYY-MM-DD)
    """)

# -------------------- 사이드바 입력 --------------------
st.sidebar.header("조건 선택")
prod_type = st.sidebar.radio("상품 유형", ["예금", "적금"], horizontal=True)

if prod_type == "예금":
    amount = st.sidebar.number_input("예치금액(원)", min_value=0, step=10000, value=10000000)
else:
    amount = st.sidebar.number_input("월 납입액(원)", min_value=0, step=10000, value=500000)

months = st.sidebar.select_slider("기간(개월)", options=[3,6,12,24,36,48,60], value=12)
compounding = st.sidebar.radio("이자 계산 방식", ["월복리", "단리"], horizontal=True)

tax_mode = st.sidebar.radio("세금(이자소득세+지방세)", ["기본 15.4%", "비과세(0%)", "직접 입력"])
if tax_mode == "기본 15.4%":
    tax_rate = 0.154
elif tax_mode == "비과세(0%)":
    tax_rate = 0.0
else:
    tax_rate = st.sidebar.number_input("세율(예: 0.154 = 15.4%)", min_value=0.0, max_value=0.99, step=0.001, value=0.154)

use_max_rate = st.sidebar.toggle("우대금리 포함(최대금리로 계산)", value=True)

groups = st.sidebar.multiselect("기관군 필터", options=sorted(rates_df["group"].dropna().unique().tolist()), default=None)
regions = st.sidebar.multiselect("지역 필터", options=sorted(rates_df["region"].dropna().unique().tolist()), default=None)

only_online = st.sidebar.selectbox("온라인 전용", options=["전체", "온라인 전용만", "오프라인 포함"], index=0)

sort_by = st.sidebar.selectbox("정렬 기준", ["세후수령액", "세전이자", "금리(선택)"], index=0)

# -------------------- 필터링 --------------------
df = rates_df.copy()
df = df[df["productType"] == prod_type]
df = df[df["termMonths"] == months]

if groups:
    df = df[df["group"].isin(groups)]
if regions:
    df = df[df["region"].isin(regions)]
if only_online == "온라인 전용만":
    df = df[df["onlineOnly"] == True]

if df.empty:
    st.warning("선택한 조건에 맞는 상품이 없습니다. 필터를 조정해 보세요.")
    st.stop()

# 사용할 금리 컬럼 선택
rate_col = "rateMax" if use_max_rate else "rateBase"

# -------------------- 계산 --------------------
calc_rows = []
for idx, row in df.iterrows():
    r = float(row[rate_col]) if not np.isnan(row[rate_col]) else 0.0
    calc_type = row.get("rateCalcType", "복리")
    # '복리'인 상품은 기본적으로 월복리 권장
    comp_use = compounding
    # 계산
    if prod_type == "예금":
        gross, interest_gross, tax, net = calc_deposit(amount, r, int(months), comp_use, tax_rate)
        total_paid = amount
    else:
        gross, total_paid, interest_gross, tax, net = calc_saving(amount, r, int(months), comp_use, tax_rate)

    calc_rows.append({
        "금융기관": row["institution"],
        "상품명": row["productName"],
        "기관군": row["group"],
        "지역": row["region"],
        "기간(개월)": int(row["termMonths"]),
        "금리기준": "최대금리" if use_max_rate else "기본금리",
        "금리(연)": r,
        "계산방식": comp_use,
        "세전만기": gross,
        "총납입": total_paid,
        "세전이자": interest_gross,
        "예상세금": tax,
        "세후수령액": net,
        "우대조건": row.get("conditions", ""),
        "원문": row.get("sourceUrl", ""),
        "검증일": row.get("lastVerifiedAt", ""),
        "_rateBase": row.get("rateBase", np.nan),
        "_rateMax": row.get("rateMax", np.nan),
        "_onlineOnly": row.get("onlineOnly", False),
    })

out_df = pd.DataFrame(calc_rows)

# 정렬
if sort_by == "세후수령액":
    out_df = out_df.sort_values("세후수령액", ascending=False)
elif sort_by == "세전이자":
    out_df = out_df.sort_values("세전이자", ascending=False)
else:
    # 금리(선택) 기준
    out_df = out_df.sort_values("금리(연)", ascending=False)

# 상단 하이라이트
best = out_df.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("최고 세후수령액", f"{best['세후수령액']:,.0f} 원")
c2.metric("세전이자", f"{best['세전이자']:,.0f} 원")
c3.metric("금리(연)", f"{best['금리(연)']*100:.2f} %")
c4.metric("기간", f"{int(best['기간(개월)'])} 개월")

# 표시용 포맷
display_cols = ["금융기관", "상품명", "기관군", "지역", "기간(개월)", "금리기준", "금리(연)", "계산방식",
                "총납입", "세전이자", "예상세금", "세후수령액", "우대조건", "원문", "검증일"]
df_show = out_df[display_cols].copy()
df_show["금리(연)"] = (df_show["금리(연)"] * 100).map(lambda x: f"{x:.2f}%")
for col in ["총납입", "세전이자", "예상세금", "세후수령액"]:
    df_show[col] = df_show[col].map(lambda x: f"{x:,.0f} 원")

st.subheader("결과 목록")
st.dataframe(df_show, use_container_width=True, height=520)

# 다운로드
csv = out_df.to_csv(index=False).encode("utf-8-sig")
st.download_button("결과 CSV 다운로드", data=csv, file_name="rate_calc_results.csv", mime="text/csv")

with st.expander("계산 가정/주의사항"):
    st.markdown("""
    - 세율 기본값 15.4%는 (이자소득세 14% + 지방세 1.4%)를 의미합니다. 비과세/우대세율 등은 사용자가 설정하세요.
    - '월복리'는 월 이자 재투자 가정, '단리'는 단순이자 가정입니다. 금융기관의 실제 이자 계산 규정과 차이가 있을 수 있습니다.
    - 적금의 '자유적립식'은 납입 시점이 제각각이므로 본 계산기는 **정기적립식과 동일한 월말 납입 가정**으로 근사할 수 있습니다.
    - 데이터의 금리는 **샘플**이며, 실제 금리는 상품 공시/원문 페이지에서 확인해야 합니다.
    """)

st.caption("© 2025 최고금리 찾기 데모 · Streamlit")
