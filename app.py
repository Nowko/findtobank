import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(
    page_title="금융상품 비교센터",
    page_icon="🏦",
    layout="wide"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .api-success {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 15px 0;
    }
    
    .api-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# 금융감독원 API 클래스
class FinanceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://finlife.fss.or.kr/finlifeapi"
        
    def get_saving_products(self):
        """적금 상품 조회 (모든 기관 유형, 여러 페이지)"""
        all_products = {'result': {'baseList': [], 'optionList': []}}
        
        # 다양한 기관 유형 조회
        org_types = ['020000', '030300', '030201', '020201']  # 은행, 저축은행, 신협, 종금사
        
        for org_type in org_types:
            for page in range(1, 6):  # 최대 5페이지까지 조회
                url = f"{self.base_url}/savingProductsSearch.json"
                params = {
                    'auth': self.api_key,
                    'topFinGrpNo': org_type,
                    'pageNo': page
                }
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('result') and data['result'].get('baseList'):
                            all_products['result']['baseList'].extend(data['result']['baseList'])
                            if data['result'].get('optionList'):
                                all_products['result']['optionList'].extend(data['result']['optionList'])
                        else:
                            break  # 더 이상 데이터가 없으면 중단
                    time.sleep(0.1)  # API 요청 간격
                except Exception as e:
                    st.warning(f"기관유형 {org_type}, 페이지 {page} 조회 실패: {str(e)}")
                    continue
        
        return all_products if all_products['result']['baseList'] else None
    
    def get_deposit_products(self):
        """예금 상품 조회 (모든 기관 유형, 여러 페이지)"""
        all_products = {'result': {'baseList': [], 'optionList': []}}
        
        # 다양한 기관 유형 조회
        org_types = ['020000', '030300', '030201', '020201']  # 은행, 저축은행, 신협, 종금사
        
        for org_type in org_types:
            for page in range(1, 6):  # 최대 5페이지까지 조회
                url = f"{self.base_url}/depositProductsSearch.json"
                params = {
                    'auth': self.api_key,
                    'topFinGrpNo': org_type,
                    'pageNo': page
                }
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('result') and data['result'].get('baseList'):
                            all_products['result']['baseList'].extend(data['result']['baseList'])
                            if data['result'].get('optionList'):
                                all_products['result']['optionList'].extend(data['result']['optionList'])
                        else:
                            break  # 더 이상 데이터가 없으면 중단
                    time.sleep(0.1)  # API 요청 간격
                except Exception as e:
                    st.warning(f"기관유형 {org_type}, 페이지 {page} 조회 실패: {str(e)}")
                    continue
        
        return all_products if all_products['result']['baseList'] else None

def calculate_after_tax_amount(monthly_amount, annual_rate, months=12, tax_rate=0.154):
    """정기적금 세후 수령액 계산 (매월 적립 방식)"""
    # 연 이자율을 월 이자율로 변환
    monthly_rate = annual_rate / 100 / 12
    
    total_principal = monthly_amount * months  # 총 납입원금
    total_interest = 0
    
    # 매월 적립하는 정기적금 복리 계산
    for month in range(1, months + 1):
        # 각 월 적립금이 적립되어 있는 기간
        remaining_months = months - month + 1
        # 해당 월 적립금의 이자 (복리)
        month_interest = monthly_amount * ((1 + monthly_rate) ** remaining_months - 1)
        total_interest += month_interest
    
    # 세금 계산 (이자소득세 15.4%)
    tax = total_interest * tax_rate
    
    # 세후 수령액
    after_tax_amount = total_principal + total_interest - tax
    
    return {
        'total_principal': total_principal,
        'total_interest': total_interest,
        'tax': tax,
        'after_tax_amount': after_tax_amount,
        'net_interest': total_interest - tax
    }

def process_data(api_data):
    """API 데이터 처리"""
    if not api_data or not api_data.get('result'):
        return pd.DataFrame()
    
    base_list = api_data['result'].get('baseList', [])
    option_list = api_data['result'].get('optionList', [])
    
    if not base_list:
        return pd.DataFrame()
    
    df_base = pd.DataFrame(base_list)
    
    if option_list:
        df_options = pd.DataFrame(option_list)
        max_rates = df_options.groupby('fin_prdt_cd').agg({
            'intr_rate': 'max',
            'intr_rate2': 'max'
        }).reset_index()
        df_merged = df_base.merge(max_rates, on='fin_prdt_cd', how='left')
    else:
        df_merged = df_base.copy()
        df_merged['intr_rate'] = 0
        df_merged['intr_rate2'] = 0
    
    # 데이터 정리
    result_df = pd.DataFrame({
        '금융기관': df_merged.get('kor_co_nm', ''),
        '상품명': df_merged.get('fin_prdt_nm', ''),
        '최고금리': df_merged.get('intr_rate2', 0).apply(lambda x: f"{float(x):.2f}%" if x else "0.00%"),
        '최고금리_숫자': pd.to_numeric(df_merged.get('intr_rate2', 0), errors='coerce').fillna(0),
        '가입방법': df_merged.get('join_way', ''),
        '우대조건': df_merged.get('spcl_cnd', ''),
        '가입대상': df_merged.get('join_member', '')
    })
    
    return result_df.sort_values('최고금리_숫자', ascending=False).reset_index(drop=True)

def main():
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>🏦 금융상품 비교센터</h1>
        <p>금융감독원 공식 API 연동 - 실시간 금융상품 정보</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API 키
    api_key = "9eef9d0d97316bd23093d3317c1732af"
    
    # 사이드바
    st.sidebar.header("🔍 상품 검색")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        product_type = st.selectbox("상품 유형", ["적금", "예금"])
    with col2:
        region = st.selectbox("지역", ["전체", "서울", "부산", "대구", "인천", "광주"])
    
    period = st.sidebar.selectbox("가입기간", ["전체", "3개월", "6개월", "1년", "2년", "3년", "4년", "5년"])
    
    # 금융기관 유형 선택
    st.sidebar.subheader("🏛️ 금융기관 유형")
    
    # 버튼을 3개 행으로 배치
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        btn_all_banks = st.button("🏦 전체", use_container_width=True, key="btn_all")
    with col2:
        btn_banks = st.button("🏛️ 은행", use_container_width=True, key="btn_bank")
    with col3:
        btn_savings = st.button("🏪 저축은행", use_container_width=True, key="btn_savings")
    
    # 선택된 기관 유형 결정
    bank_type_filter = None
    if btn_banks:
        bank_type_filter = "은행"
    elif btn_savings:
        bank_type_filter = "저축은행"
    # btn_all_banks 또는 아무것도 선택 안 함 = 전체
    
    # 저축 금액 입력
    st.sidebar.subheader("💰 매월 저축 금액")
    savings_amount = st.sidebar.number_input(
        "매월 적립할 금액 (원)", 
        min_value=1000, 
        max_value=10000000, 
        value=200000, 
        step=10000,
        format="%d"
    )
    
    # 선택된 상품의 수익 계산 표시 (사이드바)
    if 'selected_product' in st.session_state:
        selected = st.session_state.selected_product
        st.sidebar.subheader("💰 수익 계산")
        
        # 가입기간을 개월 수로 변환
        period_map = {
            "전체": 12,
            "3개월": 3,
            "6개월": 6,
            "1년": 12,
            "2년": 24,
            "3년": 36,
            "4년": 48,
            "5년": 60
        }
        savings_period = period_map.get(period, 12)
        
        # 정기적금 계산
        calc_result = calculate_after_tax_amount(savings_amount, selected['최고금리_숫자'], savings_period)
        
        st.sidebar.info(f"**선택 상품**")
        st.sidebar.write(f"🏛️ {selected['금융기관']}")
        st.sidebar.write(f"📊 {selected['상품명']}")
        st.sidebar.write(f"📈 연 금리: {selected['최고금리']}")
        
        st.sidebar.write("---")
        st.sidebar.write(f"**매월 적립**: {savings_amount:,}원")
        
        # 세후 수령액을 크고 잘 보이게 표시
        st.sidebar.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4CAF50, #45a049);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin: 15px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        ">
            <h3 style="margin: 0; font-size: 18px;">💎 세후 수령액</h3>
            <h1 style="margin: 10px 0; font-size: 28px; font-weight: bold;">
                {calc_result['after_tax_amount']:,.0f}원
            </h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.write(f"**적립 기간**: {period} ({savings_period}개월)")
        st.sidebar.write(f"**총 납입원금**: {calc_result['total_principal']:,.0f}원")
        st.sidebar.success(f"**총 이자**: {calc_result['total_interest']:,.0f}원")
        st.sidebar.warning(f"**세금 (15.4%)**: {calc_result['tax']:,.0f}원")
        st.sidebar.success(f"**세후 이자**: {calc_result['net_interest']:,.0f}원")
    
    if st.sidebar.button("📊 실시간 데이터 조회", type="primary"):
        st.session_state.refresh_data = True
    
    # API 서비스
    finance_api = FinanceAPI(api_key)
    
    # 데이터 조회
    if st.session_state.get('refresh_data', False) or 'df_products' not in st.session_state:
        st.session_state.refresh_data = False
        
        with st.spinner(f"{product_type} 상품 데이터를 가져오는 중..."):
            if product_type == "적금":
                api_data = finance_api.get_saving_products()
            else:
                api_data = finance_api.get_deposit_products()
            
            if api_data:
                st.markdown('<div class="api-success">✅ API 연결 성공!</div>', unsafe_allow_html=True)
                df_products = process_data(api_data)
                st.session_state.df_products = df_products
                st.session_state.last_update = datetime.now()
            else:
                st.markdown('<div class="api-error">❌ API 호출 실패</div>', unsafe_allow_html=True)
                return
    
    # 데이터 가져오기
    df_products = st.session_state.get('df_products', pd.DataFrame())
    
    if df_products.empty:
        st.warning("데이터가 없습니다. 실시간 데이터 조회 버튼을 클릭해주세요.")
        return
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 상품 수", f"{len(df_products)}개")
    with col2:
        max_rate = df_products['최고금리_숫자'].max()
        st.metric("최고 금리", f"{max_rate:.2f}%")
    with col3:
        avg_rate = df_products['최고금리_숫자'].mean()
        st.metric("평균 금리", f"{avg_rate:.2f}%")
    with col4:
        st.metric("업데이트", datetime.now().strftime("%H:%M"))
    
    # 탭
    tab1, tab2, tab3 = st.tabs(["📋 전체 상품", "🏆 TOP 10", "📊 분석"])
    
    with tab1:
        st.subheader("전체 상품 목록")
        
        # 필터링
        filtered_df = df_products.copy()
        
        # 지역 필터링
        if region != "전체":
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains(region, na=False)]
        
        # 금융기관 유형 필터링
        if bank_type_filter == "은행":
            # "은행"이 포함되지만 "저축은행"은 제외
            filtered_df = filtered_df[
                filtered_df['금융기관'].str.contains('은행', na=False) & 
                ~filtered_df['금융기관'].str.contains('저축은행', na=False)
            ]
        elif bank_type_filter == "저축은행":
            # "저축은행"이 포함된 기관만
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains('저축은행', na=False)]
        # 전체인 경우 필터링 안 함
        
        # 필터 상태 표시
        active_filters = []
        if region != "전체":
            active_filters.append(f"지역: {region}")
        if period != "전체":
            active_filters.append(f"기간: {period}")
        if bank_type_filter:
            active_filters.append(f"기관: {bank_type_filter}")
        
        if active_filters:
            st.success(f"🎯 적용된 필터: {' | '.join(active_filters)} ({len(filtered_df)}개 상품)")
        else:
            st.info(f"📊 전체 상품 표시 중 ({len(filtered_df)}개)")
        
        # 페이지네이션
        items_per_page = 10
        total_items = len(filtered_df)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        current_page = st.session_state.current_page
        
        # 페이지 범위 체크
        if current_page > total_pages and total_pages > 0:
            st.session_state.current_page = 1
            current_page = 1
        
        # 현재 페이지 데이터
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_data = filtered_df.iloc[start_idx:end_idx]
        
        # 정보 표시
        st.info(f"📄 {start_idx + 1} ~ {min(end_idx, total_items)}번째 상품 (전체 {total_items}개)")
        
        # 테이블 표시 (클릭 가능한 상품명으로 변경)
        st.subheader("📋 상품 목록")
        for idx, row in page_data.iterrows():
            col1, col2, col3 = st.columns([3, 3, 4])
            
            with col1:
                st.write(f"🏛️ **{row['금융기관']}**")
                st.markdown(f"<span style='color: #1f77b4; font-weight: bold; font-size: 16px;'>{row['상품명']}</span>", unsafe_allow_html=True)
            
            with col2:
                # 클릭 가능한 금리 버튼
                if st.button(f"📈 {row['최고금리']}", key=f"rate_{idx}", use_container_width=True, type="primary"):
                    st.session_state.selected_product = row
                st.markdown(f"<span style='color: #ff6b35; font-weight: bold;'>가입방법: {row['가입방법']}</span>", unsafe_allow_html=True)
            
            with col3:
                st.caption(f"**가입대상**: {row['가입대상']}")
                if row['우대조건']:
                    st.caption(f"**우대조건**: {row['우대조건'][:50]}...")
            
            st.divider()
        
        # 페이지 버튼들
        if total_pages > 1:
            cols = st.columns(min(total_pages + 2, 10))  # 최대 10개 컬럼
            
            # 이전 버튼
            with cols[0]:
                if current_page > 1:
                    if st.button("◀ 이전"):
                        st.session_state.current_page = current_page - 1
                        st.rerun()
                else:
                    st.button("◀ 이전", disabled=True)
            
            # 페이지 번호들
            page_start = max(1, current_page - 3)
            page_end = min(total_pages + 1, page_start + 7)
            
            col_idx = 1
            for page_num in range(page_start, page_end):
                if col_idx < len(cols) - 1:
                    with cols[col_idx]:
                        if page_num == current_page:
                            st.button(str(page_num), disabled=True, type="primary")
                        else:
                            if st.button(str(page_num)):
                                st.session_state.current_page = page_num
                                st.rerun()
                    col_idx += 1
            
            # 다음 버튼
            with cols[-1]:
                if current_page < total_pages:
                    if st.button("다음 ▶"):
                        st.session_state.current_page = current_page + 1
                        st.rerun()
                else:
                    st.button("다음 ▶", disabled=True)
    
    with tab2:
        st.subheader("🏆 TOP 10 고금리 상품")
        top10 = df_products.head(10)
        
        for idx, row in top10.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{idx+1}위. {row['금융기관']}**")
                st.write(f"{row['상품명']}")
                st.caption(f"{row['가입방법']} | {row['가입대상']}")
            with col2:
                st.metric("최고금리", row['최고금리'])
            st.divider()
    
    with tab3:
        st.subheader("📊 금리 분석")
        
        # 금융기관별 최고금리
        bank_rates = df_products.groupby('금융기관')['최고금리_숫자'].max().sort_values(ascending=False).head(10)
        st.bar_chart(bank_rates)
        
        # 금리 구간별 분포
        st.subheader("금리 구간별 상품 분포")
        bins = [0, 2, 3, 4, 5, 100]
        labels = ['0-2%', '2-3%', '3-4%', '4-5%', '5% 이상']
        df_products['금리구간'] = pd.cut(df_products['최고금리_숫자'], bins=bins, labels=labels)
        distribution = df_products['금리구간'].value_counts()
        st.bar_chart(distribution)

if __name__ == "__main__":
    main()
