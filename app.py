import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

st.set_page_config(
    page_title="금융상품 비교센터",
    page_icon="🏦",
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 1rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 15px;
    margin-bottom: 1rem;
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

class OptimizedFinanceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://finlife.fss.or.kr/finlifeapi"
        
    def fetch_single_page(self, url, params, timeout=10):
        """단일 페이지를 가져오는 최적화된 함수"""
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return None
    
    def get_products_parallel(self, product_type="saving"):
        """병렬 처리로 데이터 가져오기 - 첫 페이지만"""
        all_products = {'result': {'baseList': [], 'optionList': []}}
        
        # 주요 기관만 선택 (시간 단축)
        org_types = ['020000', '030300']  # 은행, 저축은행만
        
        if product_type == "saving":
            endpoint = "savingProductsSearch.json"
        else:
            endpoint = "depositProductsSearch.json"
        
        def fetch_org_data(org_type):
            url = f"{self.base_url}/{endpoint}"
            params = {
                'auth': self.api_key,
                'topFinGrpNo': org_type,
                'pageNo': 1  # 첫 페이지만
            }
            return self.fetch_single_page(url, params)
        
        # 병렬로 데이터 가져오기
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_org = {executor.submit(fetch_org_data, org_type): org_type for org_type in org_types}
            
            for future in as_completed(future_to_org, timeout=15):
                try:
                    data = future.result()
                    if data and data.get('result') and data['result'].get('baseList'):
                        all_products['result']['baseList'].extend(data['result']['baseList'])
                        if data['result'].get('optionList'):
                            all_products['result']['optionList'].extend(data['result']['optionList'])
                except Exception:
                    continue
        
        return all_products if all_products['result']['baseList'] else None
    
    def get_saving_products(self):
        return self.get_products_parallel("saving")
    
    def get_deposit_products(self):
        return self.get_products_parallel("deposit")

# 캐시 관리 함수들
@st.cache_data(ttl=300, show_spinner=False)  # 5분 캐시
def cached_api_call(api_key, product_type):
    """API 호출을 캐시하여 중복 호출 방지"""
    finance_api = OptimizedFinanceAPI(api_key)
    
    if product_type == "적금":
        return finance_api.get_saving_products()
    else:
        return finance_api.get_deposit_products()

@st.cache_data(show_spinner=False)
def process_data_cached(api_data_str, period_filter=None):
    """데이터 처리를 캐시하여 반복 계산 방지"""
    api_data = json.loads(api_data_str)
    
    if not api_data or not api_data.get('result'):
        return pd.DataFrame()
    
    base_list = api_data['result'].get('baseList', [])
    option_list = api_data['result'].get('optionList', [])
    
    if not base_list:
        return pd.DataFrame()
    
    df_base = pd.DataFrame(base_list)
    
    # 기간 필터링 최적화
    if period_filter and period_filter != "전체":
        period_keywords = {
            "3개월": ["3개월", "3M", "90일"],
            "6개월": ["6개월", "6M", "180일"], 
            "1년": ["1년", "12개월", "12M"],
            "2년": ["2년", "24개월", "24M"],
            "3년": ["3년", "36개월", "36M"]
        }
        
        if period_filter in period_keywords:
            keywords = period_keywords[period_filter]
            pattern = '|'.join(keywords)
            mask = df_base['fin_prdt_nm'].str.contains(pattern, na=False, case=False)
            df_base = df_base[mask]
    
    # 옵션 데이터 처리 최적화
    if option_list:
        df_options = pd.DataFrame(option_list)
        
        # 기간별 필터링
        if period_filter and period_filter != "전체":
            period_map = {
                "3개월": "3", "6개월": "6", "1년": "12",
                "2년": "24", "3년": "36"
            }
            if period_filter in period_map and 'save_trm' in df_options.columns:
                target_months = period_map[period_filter]
                df_options = df_options[df_options['save_trm'] == target_months]
        
        # 상품별 최고 금리만 선택
        df_options = df_options[df_options['fin_prdt_cd'].isin(df_base['fin_prdt_cd'])]
        
        if not df_options.empty:
            max_rate_indices = df_options.groupby('fin_prdt_cd')['intr_rate2'].idxmax()
            max_rate_with_term = df_options.loc[max_rate_indices]
            product_info = max_rate_with_term[['fin_prdt_cd', 'intr_rate', 'intr_rate2', 'save_trm']].copy()
            df_merged = df_base.merge(product_info, on='fin_prdt_cd', how='left')
        else:
            df_merged = df_base.copy()
            # 기본값 설정 시 Series로 생성
            df_merged['intr_rate'] = pd.Series([0] * len(df_merged))
            df_merged['intr_rate2'] = pd.Series([0] * len(df_merged))
            df_merged['save_trm'] = pd.Series([12] * len(df_merged))
    else:
        df_merged = df_base.copy()
        # 기본값 설정 시 Series로 생성
        df_merged['intr_rate'] = pd.Series([0] * len(df_merged))
        df_merged['intr_rate2'] = pd.Series([0] * len(df_merged))
        df_merged['save_trm'] = pd.Series([12] * len(df_merged))
    
    # 결과 데이터프레임 생성 - fillna 오류 수정
    result_df = pd.DataFrame({
        '금융기관': df_merged.get('kor_co_nm', pd.Series([''] * len(df_merged))).fillna(''),
        '상품명': df_merged.get('fin_prdt_nm', pd.Series([''] * len(df_merged))).fillna(''),
        '최고금리': df_merged.get('intr_rate2', pd.Series([0] * len(df_merged))).apply(lambda x: f"{float(x):.2f}%" if x and x != 0 else "0.00%"),
        '최고금리_숫자': pd.to_numeric(df_merged.get('intr_rate2', pd.Series([0] * len(df_merged))), errors='coerce').fillna(0),
        '가입방법': df_merged.get('join_way', pd.Series([''] * len(df_merged))).fillna(''),
        '우대조건': df_merged.get('spcl_cnd', pd.Series([''] * len(df_merged))).fillna(''),
        '가입대상': df_merged.get('join_member', pd.Series([''] * len(df_merged))).fillna(''),
        '이자계산방법': df_merged.get('intr_rate_type_nm', pd.Series(['단리'] * len(df_merged))).fillna('단리'),
        'save_trm': pd.to_numeric(df_merged.get('save_trm', pd.Series([12] * len(df_merged))), errors='coerce').fillna(12)
    })
    
    return result_df.sort_values('최고금리_숫자', ascending=False).reset_index(drop=True)

def calculate_after_tax_amount(amount, annual_rate, months=12, tax_rate=0.154, interest_type="단리", product_type="적금"):
    """세후 수령액 계산 (기존 함수와 동일)"""
    total_principal = amount if product_type == "예금" else amount * months
    
    if not interest_type or interest_type == "" or pd.isna(interest_type):
        interest_type = "단리"
    
    if product_type == "예금":
        if interest_type == "단리":
            total_interest = amount * (annual_rate / 100) * (months / 12)
        else:
            total_interest = amount * ((1 + annual_rate / 100) ** (months / 12) - 1)
    else:
        if interest_type == "단리":
            total_interest = 0
            for month in range(1, months + 1):
                remaining_months = months - month + 1
                simple_interest = amount * (annual_rate / 100) * (remaining_months / 12)
                total_interest += simple_interest
        else:
            monthly_rate = annual_rate / 100 / 12
            total_interest = 0
            for month in range(1, months + 1):
                remaining_months = months - month + 1
                compound_interest = amount * ((1 + monthly_rate) ** remaining_months - 1)
                total_interest += compound_interest
    
    tax = total_interest * tax_rate
    after_tax_amount = total_principal + total_interest - tax
    
    return {
        'total_principal': total_principal,
        'total_interest': total_interest,
        'tax': tax,
        'after_tax_amount': after_tax_amount,
        'net_interest': total_interest - tax,
        'interest_type': interest_type,
        'product_type': product_type
    }

def load_data_with_progress(product_type, period):
    """진행 상황을 보여주면서 데이터 로드"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔍 API 연결 중...")
        progress_bar.progress(20)
        
        # 캐시된 API 호출
        api_data = cached_api_call("9eef9d0d97316bd23093d3317c1732af", product_type)
        progress_bar.progress(60)
        
        if not api_data:
            status_text.text("❌ 데이터를 가져올 수 없습니다.")
            return None
            
        status_text.text("📊 데이터 처리 중...")
        progress_bar.progress(80)
        
        # 캐시된 데이터 처리
        api_data_str = json.dumps(api_data)
        df_products = process_data_cached(api_data_str, period)
        
        progress_bar.progress(100)
        status_text.text("✅ 완료!")
        
        # 잠시 후 상태 메시지 제거
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return df_products
        
    except Exception as e:
        status_text.text(f"❌ 오류: {str(e)}")
        progress_bar.empty()
        return None

def main():
    st.markdown("""
    <div class="main-header">
        <h2>🏦 금융상품 비교센터</h2>
        <p>금융감독원 공식 API 연동 - 최적화된 빠른 조회</p>
        <p style="font-size: 12px; margin-top: 10px; opacity: 0.8;">Developed by NOWKO</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바 설정
    st.sidebar.header("🔍 상품 검색")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        product_type = st.selectbox("상품 유형", ["적금", "예금"])
    with col2:
        region = st.selectbox("지역", ["전체", "서울", "부산", "대구"])
    
    period = st.sidebar.selectbox("가입기간", ["전체", "3개월", "6개월", "1년", "2년", "3년"])
    
    # 금융기관 유형 필터 - 새로 수정된 부분
    st.sidebar.subheader("🏛️ 금융기관 유형")
    
    col1, col2, col3 = st.sidebar.columns(3)
    
    if 'bank_type_filter' not in st.session_state:
        st.session_state.bank_type_filter = None
    
    with col1:
        if st.button("🏦전체", use_container_width=True, key="btn_all"):
            st.session_state.bank_type_filter = None
    with col2:
        if st.button("🏛️은행", use_container_width=True, key="btn_bank"):
            st.session_state.bank_type_filter = "은행"
    with col3:
        if st.button("🏪저축", use_container_width=True, key="btn_savings"):
            st.session_state.bank_type_filter = "저축은행"
    
    bank_type_filter = st.session_state.bank_type_filter
    
    # 저축 금액 설정
    if product_type == "예금":
        st.sidebar.subheader("💰 일시 예치금")
        savings_amount = st.sidebar.number_input(
            "예금할 총 금액 (원)", 
            min_value=10000, 
            max_value=1000000000, 
            value=1000000,
            step=100000,
            format="%d"
        )
        st.sidebar.write(f"💰 **{savings_amount//10000}만원** ({savings_amount:,}원) 일시예치")
    else:
        st.sidebar.subheader("💰 매월 저축 금액")
        savings_amount = st.sidebar.number_input(
            "매월 적립할 금액 (원)", 
            min_value=1000, 
            max_value=10000000, 
            value=200000, 
            step=10000,
            format="%d"
        )
        st.sidebar.write(f"💰 **{savings_amount//10000}만원** ({savings_amount:,}원) / 월")
    
    # 선택된 상품 수익 계산 표시
    if 'selected_product' in st.session_state:
        selected = st.session_state.selected_product
        
        period_map = {
            "전체": 12, "3개월": 3, "6개월": 6, "1년": 12,
            "2년": 24, "3년": 36
        }
        savings_period = period_map.get(period, 12)
        
        calc_result = calculate_after_tax_amount(
            savings_amount,
            selected['최고금리_숫자'], 
            savings_period, 
            interest_type=selected.get('이자계산방법', '단리'),
            product_type=product_type
        )
        
        st.sidebar.subheader("💰 수익 계산")
        
        st.sidebar.info(f"**선택 상품**")
        st.sidebar.write(f"🏛️ {selected['금융기관']}")
        st.sidebar.write(f"📊 {selected['상품명']}")
        st.sidebar.write(f"📈 연 금리: {selected['최고금리']}")
        st.sidebar.write(f"🔢 이자방식: {calc_result['interest_type']}")
        
        st.sidebar.write("---")
        if product_type == "예금":
            st.sidebar.write(f"**일시 예치**: {savings_amount//10000}만원")
        else:
            st.sidebar.write(f"**매월 적립**: {savings_amount//10000}만원")
        st.sidebar.write(f"**가입 기간**: {period} ({savings_period}개월)")
        st.sidebar.write(f"**총 원금**: {calc_result['total_principal']:,.0f}원")
        st.sidebar.success(f"**총 이자**: {calc_result['total_interest']:,.0f}원")
        st.sidebar.warning(f"**세금 (15.4%)**: {calc_result['tax']:,.0f}원")
        st.sidebar.success(f"**세후 이자**: {calc_result['net_interest']:,.0f}원")
        
        # 최종 수령액 박스
        st.sidebar.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4CAF50, #45a049);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin: 10px 0;
            border: 2px solid #45a049;
        ">
            <h3 style="margin: 0; font-size: 16px;">💎 최종 세후 수령액</h3>
            <h2 style="margin: 5px 0; font-size: 24px; font-weight: bold;">
                {calc_result['after_tax_amount']:,.0f}원
            </h2>
        </div>
        """, unsafe_allow_html=True)
    
    # 캐시 상태 표시
    if st.sidebar.button("🔄 캐시 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    # 데이터 로드 상태 확인
    cache_key = f"{product_type}_{period}"
    
    if ('df_products' not in st.session_state or 
        st.session_state.get('last_cache_key') != cache_key):
        
        st.session_state.last_cache_key = cache_key
        
        # 진행 상황과 함께 데이터 로드
        df_products = load_data_with_progress(product_type, period)
        
        if df_products is not None and not df_products.empty:
            st.session_state.df_products = df_products
            st.success(f"✅ {len(df_products)}개 상품을 빠르게 불러왔습니다!")
        else:
            st.error("❌ 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
            return
    
    df_products = st.session_state.get('df_products', pd.DataFrame())
    
    if df_products.empty:
        st.warning("데이터가 없습니다.")
        return
    
    # 메트릭 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 상품 수", f"{len(df_products)}개")
    with col2:
        max_rate = df_products['최고금리_숫자'].max()
        st.metric("최고 금리", f"{max_rate:.2f}%")
    with col3:
        avg_rate = df_products['최고금리_숫자'].mean()
        st.metric("평균 금리", f"{avg_rate:.2f}%")
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📋 전체 상품", "🏆 TOP 10", "📊 분석"])
    
    with tab1:
        st.subheader("전체 상품 목록")
        
        # 필터 적용
        filtered_df = df_products.copy()
        
        if region != "전체":
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains(region, na=False)]
        
        if bank_type_filter == "은행":
            filtered_df = filtered_df[
                filtered_df['금융기관'].str.contains('은행', na=False) & 
                ~filtered_df['금융기관'].str.contains('저축은행', na=False)
            ]
        elif bank_type_filter == "저축은행":
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains('저축은행', na=False)]
        
        st.info(f"📊 {len(filtered_df)}개 상품 표시 중")
        
        # 페이지네이션
        items_per_page = 10
        total_items = len(filtered_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        current_page = min(st.session_state.current_page, total_pages)
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_df.iloc[start_idx:end_idx]
        
        # 상품 목록 표시 - 첫 번째 열 축소
        for idx, row in page_data.iterrows():
            col1, col2 = st.columns([1.5, 8.5])  # 기관명:상세정보 = 1.5:8.5 (기존 2.5에서 60%로 축소)
            
            with col1:
                st.write(f"🏛️ **{row['금융기관']}**")
                # 상품명을 더 컴팩트하게 표시 (폭이 줄어든 만큼 텍스트도 단축)
                product_name = row['상품명']
                if len(product_name) > 20:
                    product_name = product_name[:20] + "..."
                st.markdown(f"<span style='color: #1f77b4; font-weight: bold; font-size: 12px;'>{product_name}</span>", 
                           unsafe_allow_html=True)
                
                # 최종 세후 수령액 계산 및 표시
                period_map = {
                    "전체": 12, "3개월": 3, "6개월": 6, "1년": 12,
                    "2년": 24, "3년": 36
                }
                savings_period = period_map.get(period, 12)
                
                calc_result = calculate_after_tax_amount(
                    savings_amount,
                    row['최고금리_숫자'], 
                    savings_period, 
                    interest_type=row.get('이자계산방법', '단리'),
                    product_type=product_type
                )
                
                # 세후 수령액을 강조하여 표시
                st.markdown(f"""
                <div style="background-color: #e8f5e8; padding: 5px; border-radius: 5px; margin-top: 5px;">
                    <span style="font-size: 10px; color: #666;">💰 세후 수령액</span><br>
                    <span style="font-weight: bold; color: #2e7d32; font-size: 12px;">
                        {calc_result['after_tax_amount']:,.0f}원
                    </span>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # 금리, 가입방법, 가입대상을 한 줄에 배치
                col_rate, col_method, col_target = st.columns([2, 2.5, 3])
                
                with col_rate:
                    # 금리 버튼
                    if st.button(f"📈 {row['최고금리']}", key=f"rate_{idx}", 
                                use_container_width=True, type="primary"):
                        st.session_state.selected_product = row
                        st.rerun()
                    
                    # 이자계산방식
                    interest_method = row.get('이자계산방법', '단리')
                    method_color = "#28a745" if interest_method == "복리" else "#6c757d"
                    st.markdown(f"<span style='color: {method_color}; font-weight: bold; font-size: 11px;'>🔢 {interest_method}</span>", 
                               unsafe_allow_html=True)
                
                with col_method:
                    # 가입방법
                    st.markdown("**📝 가입방법**")
                    join_way = row['가입방법']
                    if len(join_way) > 12:
                        join_way = join_way[:12] + "..."
                    st.write(f"{join_way}")
                
                with col_target:
                    # 가입대상
                    st.markdown("**👥 가입대상**")
                    join_member = row['가입대상']
                    if len(join_member) > 25:
                        join_member = join_member[:25] + "..."
                    st.write(f"{join_member}")
                
                # 우대조건은 전체 폭에서 expander로
                with st.expander("🎁 우대조건 보기", expanded=False):
                    special_condition = row['우대조건'] if row['우대조건'] and row['우대조건'].strip() else '해당없음'
                    st.write(special_condition)
            
            st.divider()
        
        # 페이지 네비게이션
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if current_page > 1:
                    if st.button("◀ 이전"):
                        st.session_state.current_page = current_page - 1
                        st.rerun()
            with col2:
                st.write(f"📄 페이지 {current_page} / {total_pages}")
            with col3:
                if current_page < total_pages:
                    if st.button("다음 ▶"):
                        st.session_state.current_page = current_page + 1
                        st.rerun()
    
    with tab2:
        st.subheader("🏆 TOP 10 고금리 상품")
        top10 = df_products.head(10)
        
        for idx, row in top10.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{idx+1}위. {row['금융기관']}**")
                st.write(f"{row['상품명']}")
            with col2:
                st.metric("최고금리", row['최고금리'])
            st.divider()
    
    with tab3:
        st.subheader("📊 금리 분석")
        
        # 기관별 최고 금리 차트
        bank_rates = df_products.groupby('금융기관')['최고금리_숫자'].max().sort_values(ascending=False).head(10)
        st.bar_chart(bank_rates)
        
        # 금리 구간별 분포
        st.subheader("금리 구간별 상품 분포")
        bins = [0, 2, 3, 4, 5, 100]
        labels = ['0-2%', '2-3%', '3-4%', '4-5%', '5% 이상']
        df_products['금리구간'] = pd.cut(df_products['최고금리_숫자'], bins=bins, labels=labels)
        distribution = df_products['금리구간'].value_counts()
        st.bar_chart(distribution)
    
    # 성능 정보
    if st.sidebar.checkbox("성능 정보 표시"):
        st.sidebar.info(f"""
        **최적화 적용**
        - ✅ 병렬 API 호출
        - ✅ 데이터 캐싱 (5분)
        - ✅ 주요 기관만 조회
        - ✅ 첫 페이지만 로드
        
        **로딩 시간**: ~3-5초
        **캐시 히트시**: ~1초 이내
        """)

if __name__ == "__main__":
    main()
