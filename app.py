import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 설정
st.set_page_config(
    page_title="실제 금융상품 비교센터",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
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
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    .api-status {
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid;
    }
    
    .api-success {
        background-color: #d4edda;
        color: #155724;
        border-left-color: #28a745;
    }
    
    .api-error {
        background-color: #f8d7da;
        color: #721c24;
        border-left-color: #dc3545;
    }
    
    .metric-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    .rate-highlight {
        font-size: 2rem;
        font-weight: bold;
        color: #e74c3c;
    }
    
    .bank-badge {
        background: #3498db;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        display: inline-block;
        margin: 2px;
    }
    
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        transition: transform 0.2s;
    }
    
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 금융감독원 API 클래스 (개선된 버전)
class FinanceAPIService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://finlife.fss.or.kr/finlifeapi"
        self.session = requests.Session()
        
    def _make_request(self, endpoint, params=None):
        """API 요청 공통 함수"""
        if params is None:
            params = {}
        
        params['auth'] = self.api_key
        params['topFinGrpNo'] = '020000'  # 은행권
        params['pageNo'] = 1
        
        try:
            url = f"{self.base_url}/{endpoint}"
            st.write(f"🔄 API 요청: {url}")
            st.write(f"📋 파라미터: {params}")
            
            response = self.session.get(url, params=params, timeout=30)
            st.write(f"📡 응답 상태: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('result'):
                return data
            else:
                st.error(f"API 응답 오류: {data}")
                return None
                
        except requests.exceptions.Timeout:
            st.error("⏰ API 요청 시간 초과 (30초)")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"🚫 API 요청 실패: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            st.error(f"📄 JSON 파싱 오류: {str(e)}")
            return None
    
    def get_saving_products(self):
        """적금 상품 조회"""
        return self._make_request('savingProductsSearch.json')
    
    def get_deposit_products(self):
        """예금 상품 조회"""
        return self._make_request('depositProductsSearch.json')
    
    def get_company_list(self):
        """금융회사 목록 조회"""
        return self._make_request('companySearch.json')

def process_product_data(api_data):
    """API 데이터를 처리하여 DataFrame으로 변환"""
    if not api_data or not api_data.get('result'):
        return pd.DataFrame()
    
    base_list = api_data['result'].get('baseList', [])
    option_list = api_data['result'].get('optionList', [])
    
    if not base_list:
        return pd.DataFrame()
    
    # 기본 상품 정보 DataFrame 생성
    df_base = pd.DataFrame(base_list)
    
    # 옵션 정보가 있으면 최고 금리 계산
    if option_list:
        df_options = pd.DataFrame(option_list)
        
        # 상품별 최고 금리 계산
        max_rates = df_options.groupby('fin_prdt_cd').agg({
            'intr_rate': 'max',
            'intr_rate2': 'max'
        }).reset_index()
        
        # 기본 정보와 병합
        df_merged = df_base.merge(max_rates, on='fin_prdt_cd', how='left')
    else:
        df_merged = df_base.copy()
        df_merged['intr_rate'] = 0
        df_merged['intr_rate2'] = 0
    
    # 컬럼명 정리 및 데이터 타입 변환
    df_merged['기본금리'] = pd.to_numeric(df_merged.get('intr_rate', 0), errors='coerce').fillna(0)
    df_merged['최고금리'] = pd.to_numeric(df_merged.get('intr_rate2', 0), errors='coerce').fillna(0)
    
    # 필요한 컬럼만 선택
    result_df = pd.DataFrame({
        '금융기관': df_merged.get('kor_co_nm', ''),
        '상품명': df_merged.get('fin_prdt_nm', ''),
        '기본금리': df_merged['기본금리'],
        '최고금리': df_merged['최고금리'],
        '가입방법': df_merged.get('join_way', ''),
        '우대조건': df_merged.get('spcl_cnd', ''),
        '가입대상': df_merged.get('join_member', ''),
        '상품ID': df_merged.get('fin_prdt_cd', ''),
        '기관코드': df_merged.get('fin_co_no', '')
    })
    
    # 최고금리 기준으로 정렬
    result_df = result_df.sort_values('최고금리', ascending=False).reset_index(drop=True)
    result_df.index = result_df.index + 1
    
    return result_df

# 메인 앱
def main():
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>🏦 실제 금융상품 비교센터</h1>
        <p>금융감독원 공식 API 연동 - 실시간 금융상품 정보</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">API Key: 9eef***********32af (인증 완료)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API 키 설정
    api_key = "9eef9d0d97316bd23093d3317c1732af"
    
    # 사이드바
    st.sidebar.header("🔍 상품 검색")
    
    product_type = st.sidebar.selectbox(
        "상품 유형",
        ["적금", "예금"],
        help="조회할 금융상품 유형을 선택하세요"
    )
    
    # 실시간 데이터 조회 버튼
    if st.sidebar.button("📊 실시간 데이터 조회", type="primary", use_container_width=True):
        st.session_state.refresh_data = True
    
    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("🔄 자동 새로고침 (60초)", value=False)
    
    if auto_refresh:
        st.sidebar.info("60초마다 자동으로 데이터를 업데이트합니다.")
        time.sleep(60)
        st.rerun()
    
    # API 서비스 초기화
    finance_api = FinanceAPIService(api_key)
    
    # 데이터 조회 실행
    if st.session_state.get('refresh_data', False) or 'df_products' not in st.session_state:
        st.session_state.refresh_data = False
        
        with st.spinner(f"🔄 {product_type} 상품 데이터를 가져오는 중..."):
            progress_bar = st.progress(0)
            
            # API 호출
            progress_bar.progress(25)
            if product_type == "적금":
                api_data = finance_api.get_saving_products()
            else:
                api_data = finance_api.get_deposit_products()
            
            progress_bar.progress(50)
            
            if api_data:
                st.markdown('<div class="api-status api-success">✅ API 연결 성공! 실시간 데이터를 가져왔습니다.</div>', 
                           unsafe_allow_html=True)
                
                # 데이터 처리
                progress_bar.progress(75)
                df_products = process_product_data(api_data)
                st.session_state.df_products = df_products
                st.session_state.last_update = datetime.now()
                
                progress_bar.progress(100)
                time.sleep(0.5)
                progress_bar.empty()
                
            else:
                st.markdown('<div class="api-status api-error">❌ API 호출 실패. 잠시 후 다시 시도해주세요.</div>', 
                           unsafe_allow_html=True)
                return
    
    # 세션에서 데이터 가져오기
    df_products = st.session_state.get('df_products', pd.DataFrame())
    last_update = st.session_state.get('last_update', datetime.now())
    
    if df_products.empty:
        st.warning("⚠️ 표시할 데이터가 없습니다. '실시간 데이터 조회' 버튼을 클릭해주세요.")
        return
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 총 상품 수",
            value=f"{len(df_products)}개",
            delta=f"업데이트: {last_update.strftime('%H:%M')}"
        )
    
    with col2:
        max_rate = df_products['최고금리'].max()
        st.metric(
            label="🔥 최고 금리",
            value=f"{max_rate:.2f}%",
            delta="세전 기준"
        )
    
    with col3:
        avg_rate = df_products['최고금리'].mean()
        st.metric(
            label="📈 평균 금리",
            value=f"{avg_rate:.2f}%",
            delta=f"{len(df_products[df_products['최고금리'] >= 4])}개 상품이 4% 이상"
        )
    
    with col4:
        bank_count = df_products['금융기관'].nunique()
        st.metric(
            label="🏛️ 참여 기관",
            value=f"{bank_count}개",
            delta="금융기관"
        )
    
    # 탭으로 구분된 뷰
    tab1, tab2, tab3, tab4 = st.tabs(["📋 전체 상품", "🏆 TOP 10", "📊 분석 차트", "🔍 상품 검색"])
    
    with tab1:
        st.subheader(f"📋 전체 {product_type} 상품 목록")
        
        # 필터링 옵션
        col1, col2 = st.columns(2)
        with col1:
            min_rate = st.slider("최소 금리 (%)", 0.0, 10.0, 0.0, 0.1)
        with col2:
            selected_banks = st.multiselect(
                "금융기관 필터",
                options=df_products['금융기관'].unique(),
                default=[]
            )
        
        # 필터 적용
        filtered_df = df_products.copy()
        if min_rate > 0:
            filtered_df = filtered_df[filtered_df['최고금리'] >= min_rate]
        if selected_banks:
            filtered_df = filtered_df[filtered_df['금융기관'].isin(selected_banks)]
        
        # 스타일링된 테이블 표시
        def highlight_top_rates(val):
            if isinstance(val, (int, float)) and val >= 5.0:
                return 'background-color: #ffebee; font-weight: bold; color: #c62828'
            elif isinstance(val, (int, float)) and val >= 3.0:
                return 'background-color: #fff3e0; font-weight: bold; color: #ef6c00'
            return ''
        
        styled_df = filtered_df.style.applymap(highlight_top_rates, subset=['최고금리'])
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # 다운로드 버튼
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name=f'{product_type}_products_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
            mime='text/csv'
        )
    
    with tab2:
        st.subheader("🏆 TOP 10 고금리 상품")
        
        top10 = df_products.head(10)
        
        for idx, row in top10.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="product-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #2c3e50;">
                                {idx}위. {row['금융기관']}
                            </h4>
                            <p style="margin: 5px 0; color: #7f8c8d;">{row['상품명']}</p>
                            <small style="color: #95a5a6;">{row['가입방법']} | {row['가입대상']}</small>
                        </div>
                        <div style="text-align: right;">
                            <div class="rate-highlight">{row['최고금리']:.2f}%</div>
                            <small style="color: #7f8c8d;">기본: {row['기본금리']:.2f}%</small>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("📊 금리 분석 차트")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 금융기관별 최고금리 비교
            bank_max_rates = df_products.groupby('금융기관')['최고금리'].max().sort_values(ascending=False).head(10)
            
            fig1 = px.bar(
                x=bank_max_rates.values,
                y=bank_max_rates.index,
                orientation='h',
                title="금융기관별 최고금리 TOP 10",
                labels={'x': '최고금리 (%)', 'y': '금융기관'},
                color=bank_max_rates.values,
                color_continuous_scale='Reds'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 금리 분포 히스토그램
            fig2 = px.histogram(
                df_products,
                x='최고금리',
                nbins=20,
                title="금리 분포",
                labels={'x': '최고금리 (%)', 'y': '상품 수'},
                color_discrete_sequence=['#3498db']
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 기본금리 vs 최고금리 산점도
        fig3 = px.scatter(
            df_products,
            x='기본금리',
            y='최고금리',
            hover_data=['금융기관', '상품명'],
            title="기본금리 vs 최고금리 관계",
            labels={'x': '기본금리 (%)', 'y': '최고금리 (%)'},
            color='최고금리',
            color_continuous_scale='Viridis'
        )
        fig3.update_layout(height=500)
        st.plotly_chart(fig3, use_container_width=True)
    
    with tab4:
        st.subheader("🔍 상품 검색")
        
        search_term = st.text_input("상품명 또는 금융기관명으로 검색", placeholder="예: 우리은행, 적금, 우대조건")
        
        if search_term:
            search_results = df_products[
                df_products['상품명'].str.contains(search_term, case=False, na=False) |
                df_products['금융기관'].str.contains(search_term, case=False, na=False) |
                df_products['우대조건'].str.contains(search_term, case=False, na=False)
            ]
            
            if not search_results.empty:
                st.success(f"🔍 '{search_term}' 검색 결과: {len(search_results)}개 상품")
                st.dataframe(search_results, use_container_width=True)
            else:
                st.info(f"😕 '{search_term}'에 대한 검색 결과가 없습니다.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p><strong>💡 실시간 금융상품 비교 서비스</strong></p>
        <p>📊 데이터 출처: 금융감독원 금융상품통합비교공시 Open API</p>
        <p>⏰ 마지막 업데이트: {}</p>
        <p>🔐 API 인증 상태: <span style="color: green;">✅ 정상 연결</span></p>
    </div>
    """.format(last_update.strftime("%Y년 %m월 %d일 %H시 %M분")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
