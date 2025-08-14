import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(
    page_title="금융상품 비교센터",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .best-rate {
        color: #e74c3c;
        font-weight: bold;
        font-size: 1.2em;
    }
    
    .bank-name {
        color: #2c3e50;
        font-weight: 600;
    }
    
    .amount {
        color: #27ae60;
        font-weight: bold;
    }
    
    .stSelectbox > label {
        font-weight: 600;
        color: #2c3e50;
    }
    
    .highlight-row {
        background-color: #f8f9ff;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("""
<div class="main-header">
    <h1>📊 금융상품 비교센터</h1>
    <p>전국 금융기관의 최고금리 적금/예금 상품을 한눈에 비교하세요</p>
</div>
""", unsafe_allow_html=True)

# 샘플 데이터 생성
@st.cache_data
def load_sample_data():
    data = {
        '순위': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        '금융기관명': [
            '우리종합금융', '우리종합금융', '서울)애큐온저축은행', 
            '서울)애큐온저축은행', '대구)엠에스저축은행', 
            '우리은행', '청원신용협동조합', '계산신협', 
            '서울서부신용협동조합', '동암신용협동조합'
        ],
        '상품명': [
            '최고 연 10% 하이 정기적금', 'The조은 정기적금', '처음만난적금',
            '처음만난적금', '아이사랑 정기적금', 'Magic 적금 by 현대카드',
            '정기적금', '유니온정기적금', '자동이체 적금', 'e-파란적금'
        ],
        '세전금리(%)': [10.00, 6.60, 6.50, 6.50, 6.00, 5.70, 4.60, 4.50, 4.50, 4.45],
        '세후수령액': [12549900, 12370352, 12364633, 12357435, 12329940, 
                    12318969, 12294814, 12288405, 12288405, 12285200],
        '기관유형': ['종금사', '종금사', '저축은행', '저축은행', '저축은행', 
                  '은행', '신협', '신협', '신협', '신협'],
        '기간': ['1년', '1년', '1년', '2년', '1년', '1년', '1년', '1년', '1년', '1년'],
        '특징': [
            '최고금리,우대조건', '신규상품', '복리적용', '장기우대', 
            '자녀적금', '카드연계', '지역우대', '모바일전용', 
            '자동이체', '인터넷전용'
        ]
    }
    return pd.DataFrame(data)

# 사이드바 필터
st.sidebar.header("🔍 상품 검색 필터")

# 필터 옵션들
product_type = st.sidebar.selectbox(
    "상품유형",
    ["전체", "적금", "예금", "자유적립식"]
)

period = st.sidebar.selectbox(
    "기간",
    ["전체", "3개월", "6개월", "1년", "2년", "3년"]
)

bank_type = st.sidebar.selectbox(
    "금융기관 유형",
    ["전체", "은행", "저축은행", "신협", "종금사"]
)

amount = st.sidebar.number_input(
    "저축금액 (원)",
    min_value=10000,
    max_value=100000000,
    value=100000,
    step=10000,
    format="%d"
)

# 실시간 업데이트 버튼
if st.sidebar.button("🔄 실시간 업데이트", type="primary"):
    with st.spinner("최신 금리 정보를 불러오는 중..."):
        time.sleep(2)  # 로딩 시뮬레이션
        st.sidebar.success("✅ 업데이트 완료!")
        st.rerun()

# 데이터 로드 및 필터링
df = load_sample_data()

# 필터 적용
filtered_df = df.copy()

if bank_type != "전체":
    filtered_df = filtered_df[filtered_df['기관유형'] == bank_type]

if period != "전체":
    filtered_df = filtered_df[filtered_df['기간'] == period]

# 메인 컨텐츠
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="총 상품 수",
        value=f"{len(filtered_df)}개",
        delta=f"전체 {len(df)}개 중"
    )

with col2:
    if len(filtered_df) > 0:
        max_rate = filtered_df['세전금리(%)'].max()
        st.metric(
            label="최고 금리",
            value=f"{max_rate}%",
            delta="세전 기준"
        )

with col3:
    if len(filtered_df) > 0:
        avg_rate = filtered_df['세전금리(%)'].mean()
        st.metric(
            label="평균 금리",
            value=f"{avg_rate:.2f}%",
            delta="세전 기준"
        )

with col4:
    st.metric(
        label="최종 업데이트",
        value=datetime.now().strftime("%H:%M"),
        delta="실시간"
    )

# 검색 결과 테이블
st.subheader(f"📋 검색결과: {len(filtered_df)}개")

if len(filtered_df) > 0:
    # 상품 선택을 위한 체크박스 컬럼 추가
    selection_df = filtered_df.copy()
    selection_df.insert(0, '선택', False)
    
    # 데이터 편집 가능한 테이블
    edited_df = st.data_editor(
        selection_df,
        column_config={
            "선택": st.column_config.CheckboxColumn(
                "비교선택",
                help="비교할 상품을 선택하세요 (최대 5개)",
                default=False,
            ),
            "세전금리(%)": st.column_config.NumberColumn(
                "세전금리(%)",
                format="%.2f%%"
            ),
            "세후수령액": st.column_config.NumberColumn(
                "세후수령액",
                format="%d원"
            )
        },
        disabled=["순위", "금융기관명", "상품명", "세전금리(%)", "세후수령액", "기관유형", "기간", "특징"],
        hide_index=True,
        use_container_width=True
    )
    
    # 선택된 상품들 확인
    selected_products = edited_df[edited_df['선택'] == True]
    
    if len(selected_products) > 0:
        st.subheader("📊 선택한 상품 비교")
        
        if len(selected_products) > 5:
            st.warning("⚠️ 최대 5개 상품까지만 비교할 수 있습니다.")
            selected_products = selected_products.head(5)
        
        # 비교 차트
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("금리 비교")
            chart_data = selected_products[['금융기관명', '세전금리(%)']].set_index('금융기관명')
            st.bar_chart(chart_data)
        
        with col2:
            st.subheader("세후수령액 비교")
            chart_data2 = selected_products[['금융기관명', '세후수령액']].set_index('금융기관명')
            st.bar_chart(chart_data2)
        
        # 상세 비교 표
        st.subheader("상세 비교")
        comparison_df = selected_products.drop(['선택'], axis=1)
        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("검색 조건에 맞는 상품이 없습니다. 필터 조건을 조정해보세요.")

# 푸터 정보
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    💡 <strong>주의사항</strong><br>
    • 세후수령액은 세금을 제한 후의 실제 만기금액입니다<br>
    • 예금상품은 각 금융기관별 고시금리 기준이며, 예금 신규시 금액별 또는 영업점별로 차등금리를 적용할 수 있습니다<br>
    • 실제 가입 전 해당 금융기관에 정확한 조건을 확인하시기 바랍니다
</div>
""", unsafe_allow_html=True)

# 실시간 업데이트 시뮬레이션 (자동 새로고침)
if st.sidebar.checkbox("자동 새로고침 (30초마다)", value=False):
    time.sleep(30)
    st.rerun()
