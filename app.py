import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

st.set_page_config(
    page_title="금융상품 비교센터",
    page_icon="🏦",
    layout="wide"
)

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

class FinanceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://finlife.fss.or.kr/finlifeapi"
        
    def get_saving_products(self):
        all_products = {'result': {'baseList': [], 'optionList': []}}
        org_types = ['020000', '030300', '030201', '020201']
        
        for org_type in org_types:
            for page in range(1, 6):
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
                            break
                    time.sleep(0.1)
                except Exception as e:
                    st.warning(f"기관유형 {org_type}, 페이지 {page} 조회 실패: {str(e)}")
                    continue
        
        return all_products if all_products['result']['baseList'] else None
    
    def get_deposit_products(self):
        all_products = {'result': {'baseList': [], 'optionList': []}}
        org_types = ['020000', '030300', '030201', '020201']
        
        for org_type in org_types:
            for page in range(1, 6):
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
                            break
                    time.sleep(0.1)
                except Exception as e:
                    st.warning(f"기관유형 {org_type}, 페이지 {page} 조회 실패: {str(e)}")
                    continue
        
        return all_products if all_products['result']['baseList'] else None

def calculate_after_tax_amount(monthly_amount, annual_rate, months=12, tax_rate=0.154, interest_type="복리", method="standard"):
    total_principal = monthly_amount * months
    
    if interest_type == "단리":
        total_interest = 0
        for month in range(1, months + 1):
            remaining_months = months - month + 1
            simple_interest = monthly_amount * (annual_rate / 100) * (remaining_months / 12)
            total_interest += simple_interest
    else:
        if method == "moneta_style":
            monthly_rate = annual_rate / 100 / 12
            running_balance = 0
            
            for month in range(1, months + 1):
                running_balance += monthly_amount
                if month > 1:
                    running_balance = running_balance * (1 + monthly_rate)
            
            total_amount = running_balance * (1 + monthly_rate)
            total_interest = total_amount - total_principal
        else:
            monthly_rate = annual_rate / 100 / 12
            total_interest = 0
            
            for month in range(1, months + 1):
                remaining_months = months - month + 1
                compound_interest = monthly_amount * ((1 + monthly_rate) ** remaining_months - 1)
                total_interest += compound_interest
    
    tax = total_interest * tax_rate
    after_tax_amount = total_principal + total_interest - tax
    
    return {
        'total_principal': total_principal,
        'total_interest': total_interest,
        'tax': tax,
        'after_tax_amount': after_tax_amount,
        'net_interest': total_interest - tax,
        'interest_type': interest_type
    }

def process_data(api_data, period_filter=None):
    if not api_data or not api_data.get('result'):
        return pd.DataFrame()
    
    base_list = api_data['result'].get('baseList', [])
    option_list = api_data['result'].get('optionList', [])
    
    if not base_list:
        return pd.DataFrame()
    
    df_base = pd.DataFrame(base_list)
    
    if period_filter and period_filter != "전체":
        period_keywords = {
            "3개월": ["3개월", "3M", "90일"],
            "6개월": ["6개월", "6M", "180일"],
            "1년": ["1년", "12개월", "12M"],
            "2년": ["2년", "24개월", "24M"],
            "3년": ["3년", "36개월", "36M"],
            "4년": ["4년", "48개월", "48M"],
            "5년": ["5년", "60개월", "60M"]
        }
        
        if period_filter in period_keywords:
            keywords = period_keywords[period_filter]
            mask = df_base['fin_prdt_nm'].str.contains('|'.join(keywords), na=False, case=False)
            if 'join_member' in df_base.columns:
                mask |= df_base['join_member'].str.contains('|'.join(keywords), na=False, case=False)
            if 'spcl_cnd' in df_base.columns:
                mask |= df_base['spcl_cnd'].str.contains('|'.join(keywords), na=False, case=False)
            
            df_base = df_base[mask]
    
    if option_list:
        df_options = pd.DataFrame(option_list)
        
        if period_filter and period_filter != "전체":
            if 'save_trm' in df_options.columns:
                period_map = {
                    "3개월": "3", "6개월": "6", "1년": "12",
                    "2년": "24", "3년": "36", "4년": "48", "5년": "60"
                }
                
                if period_filter in period_map:
                    target_months = period_map[period_filter]
                    df_options = df_options[df_options['save_trm'] == target_months]
        
        df_options = df_options[df_options['fin_prdt_cd'].isin(df_base['fin_prdt_cd'])]
        
        if not df_options.empty:
            max_rates = df_options.groupby('fin_prdt_cd').agg({
                'intr_rate': 'max',
                'intr_rate2': 'max'
            }).reset_index()
            df_merged = df_base.merge(max_rates, on='fin_prdt_cd', how='left')
        else:
            df_merged = df_base.copy()
            df_merged['intr_rate'] = 0
            df_merged['intr_rate2'] = 0
    else:
        df_merged = df_base.copy()
        df_merged['intr_rate'] = 0
        df_merged['intr_rate2'] = 0
    
    result_df = pd.DataFrame({
        '금융기관': df_merged.get('kor_co_nm', ''),
        '상품명': df_merged.get('fin_prdt_nm', ''),
        '최고금리': df_merged.get('intr_rate2', 0).apply(lambda x: f"{float(x):.2f}%" if x else "0.00%"),
        '최고금리_숫자': pd.to_numeric(df_merged.get('intr_rate2', 0), errors='coerce').fillna(0),
        '가입방법': df_merged.get('join_way', ''),
        '우대조건': df_merged.get('spcl_cnd', ''),
        '가입대상': df_merged.get('join_member', ''),
        '이자계산방법': df_merged.get('intr_rate_type_nm', '복리')
    })
    
    return result_df.sort_values('최고금리_숫자', ascending=False).reset_index(drop=True)

def main():
    st.markdown("""
    <div class="main-header">
        <h1>🏦 금융상품 비교센터</h1>
        <p>금융감독원 공식 API 연동 - 실시간 금융상품 정보</p>
    </div>
    """, unsafe_allow_html=True)
    
    api_key = "9eef9d0d97316bd23093d3317c1732af"
    
    st.sidebar.header("🔍 상품 검색")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        product_type = st.selectbox("상품 유형", ["적금", "예금"])
    with col2:
        region = st.selectbox("지역", ["전체", "서울", "부산", "대구", "인천", "광주"])
    
    period = st.sidebar.selectbox("가입기간", ["전체", "3개월", "6개월", "1년", "2년", "3년", "4년", "5년"])
    
    st.sidebar.subheader("🏛️ 금융기관 유형")
    
    col1, col2, col3 = st.sidebar.columns(3)
    
    if 'bank_type_filter' not in st.session_state:
        st.session_state.bank_type_filter = None
    
    with col1:
        if st.button("🏦 전체", use_container_width=True, key="btn_all"):
            st.session_state.bank_type_filter = None
    with col2:
        if st.button("🏛️ 은행", use_container_width=True, key="btn_bank"):
            st.session_state.bank_type_filter = "은행"
    with col3:
        if st.button("🏪 저축은행", use_container_width=True, key="btn_savings"):
            st.session_state.bank_type_filter = "저축은행"
    
    bank_type_filter = st.session_state.bank_type_filter
    
    st.sidebar.subheader("💰 매월 저축 금액")
    savings_amount = st.sidebar.number_input(
        "매월 적립할 금액 (원)", 
        min_value=1000, 
        max_value=10000000, 
        value=200000, 
        step=10000,
        format="%d"
    )
    
    savings_amount_man = savings_amount // 10000
    st.sidebar.write(f"💰 **{savings_amount_man}만원** / 월")
    
    st.sidebar.subheader("📊 계산 방식")
    calculation_method = st.sidebar.radio(
        "이자 계산 방식을 선택하세요",
        options=["standard", "moneta_style"],
        format_func=lambda x: "표준 월복리 방식" if x == "standard" else "모네타 유사 방식",
        index=1,
        help="표준 방식: 일반적인 금융권 계산 방식\n모네타 방식: 모네타 사이트와 유사한 계산 방식"
    )
    
    if 'selected_product' in st.session_state:
        selected = st.session_state.selected_product
        
        period_map = {
            "전체": 12, "3개월": 3, "6개월": 6, "1년": 12,
            "2년": 24, "3년": 36, "4년": 48, "5년": 60
        }
        savings_period = period_map.get(period, 12)
        
        product_interest_type = selected.get('이자계산방법', '복리')
        calc_result = calculate_after_tax_amount(
            savings_amount, 
            selected['최고금리_숫자'], 
            savings_period, 
            interest_type=product_interest_type,
            method=calculation_method
        )
        
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
        
        st.sidebar.subheader("💰 수익 계산")
        
        st.sidebar.info(f"**선택 상품**")
        st.sidebar.write(f"🏛️ {selected['금융기관']}")
        st.sidebar.write(f"📊 {selected['상품명']}")
        st.sidebar.write(f"📈 연 금리: {selected['최고금리']}")
        st.sidebar.write(f"🔢 이자방식: {calc_result['interest_type']}")
        
        st.sidebar.write("---")
        st.sidebar.write(f"**매월 적립**: {savings_amount_man}만원")
        st.sidebar.write(f"**적립 기간**: {period} ({savings_period}개월)")
        st.sidebar.write(f"**총 납입원금**: {calc_result['total_principal']:,.0f}원")
        st.sidebar.success(f"**총 이자**: {calc_result['total_interest']:,.0f}원")
        st.sidebar.warning(f"**세금 (15.4%)**: {calc_result['tax']:,.0f}원")
        st.sidebar.success(f"**세후 이자**: {calc_result['net_interest']:,.0f}원")
    
    if st.sidebar.button("📊 실시간 데이터 조회", type="primary"):
        st.session_state.refresh_data = True
    
    finance_api = FinanceAPI(api_key)
    
    if st.session_state.get('refresh_data', False) or 'df_products' not in st.session_state or st.session_state.get('last_period') != period:
        st.session_state.refresh_data = False
        st.session_state.last_period = period
        
        with st.spinner(f"{product_type} 상품 데이터를 가져오는 중..."):
            if product_type == "적금":
                api_data = finance_api.get_saving_products()
            else:
                api_data = finance_api.get_deposit_products()
            
            if api_data:
                st.markdown('<div class="api-success">✅ API 연결 성공!</div>', unsafe_allow_html=True)
                df_products = process_data(api_data, period)
                st.session_state.df_products = df_products
                st.session_state.last_update = datetime.now()
            else:
                st.markdown('<div class="api-error">❌ API 호출 실패</div>', unsafe_allow_html=True)
                return
    
    df_products = st.session_state.get('df_products', pd.DataFrame())
    
    if df_products.empty:
        st.warning("데이터가 없습니다. 실시간 데이터 조회 버튼을 클릭해주세요.")
        return
    
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
    
    tab1, tab2, tab3 = st.tabs(["📋 전체 상품", "🏆 TOP 10", "📊 분석"])
    
    with tab1:
        st.subheader("전체 상품 목록")
        
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
        
        if period != "전체":
            st.info(f"💡 {period} 상품만 표시됩니다. 가입기간을 변경하면 상품 목록이 업데이트됩니다.")
        
        if bank_type_filter:
            st.sidebar.info(f"현재 필터: {bank_type_filter}")
        else:
            st.sidebar.info("현재 필터: 전체")
        
        items_per_page = 10
        total_items = len(filtered_df)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        current_page = st.session_state.current_page
        
        if current_page > total_pages and total_pages > 0:
            st.session_state.current_page = 1
            current_page = 1
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_data = filtered_df.iloc[start_idx:end_idx]
        
        st.info(f"📄 {start_idx + 1} ~ {min(end_idx, total_items)}번째 상품 (전체 {total_items}개)")
        
        st.subheader("📋 상품 목록")
        for idx, row in page_data.iterrows():
            col1, col2, col3 = st.columns([3, 3, 4])
            
            with col1:
                st.write(f"🏛️ **{row['금융기관']}**")
                st.markdown(f"<span style='color: #1f77b4; font-weight: bold; font-size: 16px;'>{row['상품명']}</span>", unsafe_allow_html=True)
            
            with col2:
                if st.button(f"📈 {row['최고금리']}", key=f"rate_{idx}_{row['금융기관']}_{bank_type_filter}", use_container_width=True, type="primary"):
                    st.session_state.selected_product = row
                    st.session_state.bank_type_filter = bank_type_filter
                    st.rerun()
                st.markdown(f"<span style='color: #ff6b35; font-weight: bold;'>가입방법: {row['가입방법']}</span>", unsafe_allow_html=True)
            
            with col3:
                interest_method = row.get('이자계산방법', '복리')
                method_color = "#28a745" if interest_method == "복리" else "#6c757d"
                st.markdown(f"<span style='color: {method_color}; font-weight: bold;'>🔢 {interest_method}</span>", unsafe_allow_html=True)
                
                st.caption(f"**가입대상**: {row['가입대상']}")
                if row['우대조건']:
                    st.caption(f"**우대조건**: {row['우대조건'][:50]}...")
            
            st.divider()
        
        if total_pages > 1:
            cols = st.columns(min(total_pages + 2, 10))
            
            with cols[0]:
                if current_page > 1:
                    if st.button("◀ 이전"):
                        st.session_state.current_page = current_page - 1
                        st.rerun()
                else:
                    st.button("◀ 이전", disabled=True)
            
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
        
        bank_rates = df_products.groupby('금융기관')['최고금리_숫자'].max().sort_values(ascending=False).head(10)
        st.bar_chart(bank_rates)
        
        st.subheader("금리 구간별 상품 분포")
        bins = [0, 2, 3, 4, 5, 100]
        labels = ['0-2%', '2-3%', '3-4%', '4-5%', '5% 이상']
        df_products['금리구간'] = pd.cut(df_products['최고금리_숫자'], bins=bins, labels=labels)
        distribution = df_products['금리구간'].value_counts()
        st.bar_chart(distribution)

if __name__ == "__main__":
    main()
