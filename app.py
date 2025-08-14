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
        """적금 상품 조회"""
        url = f"{self.base_url}/savingProductsSearch.json"
        params = {
            'auth': self.api_key,
            'topFinGrpNo': '020000',
            'pageNo': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API 오류: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"요청 실패: {str(e)}")
            return None
    
    def get_deposit_products(self):
        """예금 상품 조회"""
        url = f"{self.base_url}/depositProductsSearch.json"
        params = {
            'auth': self.api_key,
            'topFinGrpNo': '020000',
            'pageNo': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API 오류: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"요청 실패: {str(e)}")
            return None

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
    
    period = st.sidebar.selectbox("가입기간", ["전체", "3개월", "6개월", "1년", "2년", "3년"])
    
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
        
        # 지역 필터링 (간단한 버전)
        if region != "전체":
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains(region, na=False)]
        
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
        
        # 테이블 표시
        display_df = page_data[['금융기관', '상품명', '최고금리', '가입방법', '우대조건', '가입대상']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
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
