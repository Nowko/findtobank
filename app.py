import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

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
        if 'topFinGrpNo' not in params:
            params['topFinGrpNo'] = '020000'  # 기본값: 은행권
        if 'pageNo' not in params:
            params['pageNo'] = 1
        
        try:
            url = f"{self.base_url}/{endpoint}"
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result'):
                    return data
                else:
                    st.error(f"API 응답 오류: {data.get('error', '알 수 없는 오류')}")
                    return None
            else:
                st.error(f"HTTP 오류: {response.status_code}")
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
        except Exception as e:
            st.error(f"🔥 예상치 못한 오류: {str(e)}")
            return None
    
    def get_saving_products(self):
        """적금 상품 조회"""
        return self._make_request('savingProductsSearch.json')
    
    def get_deposit_products(self):
        """예금 상품 조회"""
        return self._make_request('depositProductsSearch.json')
    
    def get_company_list(self, bank_type='020000'):
        """금융회사 목록 조회"""
        return self._make_request('companySearch.json', {'topFinGrpNo': bank_type})
    
    def get_saving_products_by_region(self, region_code=None):
        """지역별 적금 상품 조회"""
        params = {}
        if region_code:
            # 실제 API에서 지역 코드를 지원하는 경우 사용
            params['region'] = region_code
        return self._make_request('savingProductsSearch.json', params)
    
    def get_deposit_products_by_region(self, region_code=None):
        """지역별 예금 상품 조회"""
        params = {}
        if region_code:
            # 실제 API에서 지역 코드를 지원하는 경우 사용
            params['region'] = region_code
        return self._make_request('depositProductsSearch.json', params)

def process_product_data(api_data):
    """API 데이터를 처리하여 DataFrame으로 변환"""
    if not api_data or not api_data.get('result'):
        st.warning("API 응답에서 result 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()
    
    base_list = api_data['result'].get('baseList', [])
    option_list = api_data['result'].get('optionList', [])
    
    if not base_list:
        st.warning("기본 상품 목록이 비어있습니다.")
        return pd.DataFrame()
    
    try:
        # 기본 상품 정보 DataFrame 생성
        df_base = pd.DataFrame(base_list)
        
        # 옵션 정보가 있으면 최고 금리와 기간 정보 계산
        if option_list:
            df_options = pd.DataFrame(option_list)
            
            # 상품별 최고 금리와 기간 정보 계산
            product_info = df_options.groupby('fin_prdt_cd').agg({
                'intr_rate': 'max',
                'intr_rate2': 'max',
                'save_trm': lambda x: list(set(x)) if 'save_trm' in df_options.columns else ['12']
            }).reset_index()
            
            # 기본 정보와 병합
            df_merged = df_base.merge(product_info, on='fin_prdt_cd', how='left')
        else:
            df_merged = df_base.copy()
            df_merged['intr_rate'] = 0
            df_merged['intr_rate2'] = 0
            df_merged['save_trm'] = [['12']] * len(df_merged)  # 기본값 1년
        
        # 컬럼명 정리 및 데이터 타입 변환
        df_merged['기본금리'] = pd.to_numeric(df_merged.get('intr_rate', 0), errors='coerce').fillna(0)
        df_merged['최고금리'] = pd.to_numeric(df_merged.get('intr_rate2', 0), errors='coerce').fillna(0)
        
        # 기간 정보 처리 (개월 단위를 년/개월로 변환)
        def convert_period(save_trm_list):
            if not save_trm_list or not isinstance(save_trm_list, list):
                return ['1년']
            
            periods = []
            for trm in save_trm_list:
                try:
                    months = int(trm) if trm else 12
                    if months == 3:
                        periods.append('3개월')
                    elif months == 6:
                        periods.append('6개월')
                    elif months == 12:
                        periods.append('1년')
                    elif months == 24:
                        periods.append('2년')
                    elif months == 36:
                        periods.append('3년')
                    elif months == 48:
                        periods.append('4년')
                    elif months == 60:
                        periods.append('5년')
                    else:
                        # 기타 기간은 년/개월로 변환
                        if months >= 12:
                            years = months // 12
                            remaining_months = months % 12
                            if remaining_months == 0:
                                periods.append(f'{years}년')
                            else:
                                periods.append(f'{years}년{remaining_months}개월')
                        else:
                            periods.append(f'{months}개월')
                except:
                    continue
            
            return periods if periods else ['1년']
        
        df_merged['가입기간'] = df_merged.get('save_trm', [['12']] * len(df_merged)).apply(convert_period)
        
        # 필요한 컬럼만 선택
        result_df = pd.DataFrame({
            '금융기관': df_merged.get('kor_co_nm', '알 수 없음'),
            '상품명': df_merged.get('fin_prdt_nm', '알 수 없음'),
            '최고금리': df_merged['최고금리'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"),
            '최고금리_숫자': df_merged['최고금리'],  # 정렬용
            '가입방법': df_merged.get('join_way', '정보없음'),
            '우대조건': df_merged.get('spcl_cnd', '정보없음'),
            '가입대상': df_merged.get('join_member', '정보없음'),
            '가입기간': df_merged['가입기간']  # 기간 정보 추가
        })
        
        # 최고금리 기준으로 정렬 (숫자 컬럼 사용)
        result_df = result_df.sort_values('최고금리_숫자', ascending=False).reset_index(drop=True)
        result_df.index = result_df.index + 1
        
        return result_df
        
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {str(e)}")
        return pd.DataFrame()

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
    
    # 상품 유형과 지역선택을 같은 행에 배치
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        product_type = st.selectbox(
            "상품 유형",
            ["적금", "예금"],
            help="조회할 금융상품 유형을 선택하세요"
        )
    
    with col2:
        region_selection = st.selectbox(
            "지역 선택",
            ["전체", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", 
             "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"],
            index=0,
            help="특정 지역의 금융기관 상품만 보고 싶을 때 선택하세요"
        )
    
    # 지역 필터 처리
    region_filter = region_selection if region_selection != "전체" else None
    
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
            
            try:
                # API 호출
                progress_bar.progress(25)
                if product_type == "적금":
                    api_data = finance_api.get_saving_products()
                    progress_bar.progress(50)
                else:  # 예금
                    api_data = finance_api.get_deposit_products()
                    progress_bar.progress(50)
                
                if api_data:
                    st.markdown('<div class="api-status api-success">✅ API 연결 성공! 실시간 데이터를 가져왔습니다.</div>', 
                               unsafe_allow_html=True)
                    
                    # 데이터 처리
                    progress_bar.progress(75)
                    df_products = process_product_data(api_data)
                    
                    if not df_products.empty:
                        st.session_state.df_products = df_products
                        st.session_state.last_update = datetime.now()
                        st.session_state.product_type = product_type
                        
                        progress_bar.progress(100)
                        time.sleep(0.5)
                        progress_bar.empty()
                        st.success(f"✅ {product_type} {len(df_products)}개 상품 데이터 로드 완료!")
                    else:
                        st.warning(f"⚠️ {product_type} 상품 데이터가 비어있습니다.")
                        progress_bar.empty()
                        return
                
                else:
                    st.markdown('<div class="api-status api-error">❌ API 호출 실패. 잠시 후 다시 시도해주세요.</div>', 
                               unsafe_allow_html=True)
                    progress_bar.empty()
                    return
                    
            except Exception as e:
                progress_bar.empty()
                st.error(f"🔥 데이터 처리 중 오류 발생: {str(e)}")
                st.info("💡 문제가 지속되면 페이지를 새로고침하거나 잠시 후 다시 시도해주세요.")
                return
    
    # 세션에서 데이터 가져오기
    df_products = st.session_state.get('df_products', pd.DataFrame())
    last_update = st.session_state.get('last_update', datetime.now())
    current_product_type = st.session_state.get('product_type', product_type)
    
    # 상품 유형이 변경된 경우 데이터 새로 로드
    if current_product_type != product_type:
        st.session_state.refresh_data = True
        st.rerun()
    
    if df_products.empty:
        st.warning("⚠️ 표시할 데이터가 없습니다. '실시간 데이터 조회' 버튼을 클릭해주세요.")
        
        # 자동으로 데이터 로드 시도
        if st.button("🔄 자동 데이터 로드", type="primary"):
            st.session_state.refresh_data = True
            st.rerun()
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
        max_rate = df_products['최고금리_숫자'].max()
        st.metric(
            label="🔥 최고 금리",
            value=f"{max_rate:.2f}%",
            delta="세전 기준"
        )
    
    with col3:
        avg_rate = df_products['최고금리_숫자'].mean()
        st.metric(
            label="📈 평균 금리",
            value=f"{avg_rate:.2f}%",
            delta=f"{len(df_products[df_products['최고금리_숫자'] >= 4])}개 상품이 4% 이상"
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
        st.subheader("📅 가입기간별 보기")
        
        # 가입기간별 버튼
        period_cols = st.columns(7)
        
        with period_cols[0]:
            btn_3m = st.button("3개월", use_container_width=True)
        with period_cols[1]:
            btn_6m = st.button("6개월", use_container_width=True)
        with period_cols[2]:
            btn_1y = st.button("1년", use_container_width=True)
        with period_cols[3]:
            btn_2y = st.button("2년", use_container_width=True)
        with period_cols[4]:
            btn_3y = st.button("3년", use_container_width=True)
        with period_cols[5]:
            btn_4y = st.button("4년", use_container_width=True)
        with period_cols[6]:
            btn_5y = st.button("5년", use_container_width=True)
        
        # 선택된 기간 확인
        period_filter = None
        if btn_3m:
            period_filter = "3개월"
        elif btn_6m:
            period_filter = "6개월"
        elif btn_1y:
            period_filter = "1년"
        elif btn_2y:
            period_filter = "2년"
        elif btn_3y:
            period_filter = "3년"
        elif btn_4y:
            period_filter = "4년"
        elif btn_5y:
            period_filter = "5년"
        
        st.subheader("🏛️ 금융기관 유형별 보기")
        
        # 금융기관 유형별 버튼 (전체와 은행만)
        col1, col2 = st.columns(2)
        
        with col1:
            btn_all = st.button("🏦 전체", use_container_width=True)
        with col2:
            btn_bank = st.button("🏛️ 은행", use_container_width=True)
        
        # 금융기관 유형 매핑
        bank_filter = None
        if btn_bank:
            bank_filter = "은행"
        
        # 다중 선택 필터 (기존)
        selected_banks = st.multiselect(
            "특정 금융기관 선택 (선택사항)",
            options=df_products['금융기관'].unique(),
            default=[],
            help="특정 금융기관만 보고 싶을 때 선택하세요"
        )
        
        # 필터 적용
        filtered_df = df_products.copy()
        
        # 가입기간별 필터링 (가입기간 컬럼이 있는 경우에만)
        if period_filter and '가입기간' in filtered_df.columns:
            # 해당 기간이 포함된 상품만 필터링
            try:
                mask = filtered_df['가입기간'].apply(lambda periods: period_filter in periods if isinstance(periods, list) else False)
                filtered_df = filtered_df[mask]
            except:
                # 필터링 실패 시 전체 데이터 유지
                st.warning(f"⚠️ {period_filter} 필터링 중 오류가 발생했습니다. 전체 데이터를 표시합니다.")
        
        # 기관 유형별 필터링 (은행만)
        if bank_filter == "은행":
            # 은행: "은행"이 포함된 기관 (저축은행 제외)
            filtered_df = filtered_df[filtered_df['금융기관'].str.contains('은행', na=False) & 
                                    ~filtered_df['금융기관'].str.contains('저축은행', na=False)]
        
        # 지역별 필터링 (개선된 방식)
        if region_filter:
            # 지역별 금융기관 매핑 (실제 지역 기반)
            region_banks = {
                "서울": ["KB국민은행", "신한은행", "우리은행", "KEB하나은행", "NH농협은행", "IBK기업은행", "한국산업은행"],
                "부산": ["부산은행", "BNK부산은행"],
                "대구": ["대구은행", "DGB대구은행"],
                "인천": ["신한은행", "KB국민은행", "우리은행"],
                "광주": ["광주은행"],
                "대전": ["대전은행"],
                "울산": ["울산농협", "울산신협"],
                "경기": ["경기은행"],
                "강원": ["강원은행"],
                "충북": ["충북은행"],
                "충남": ["충남은행"],
                "전북": ["전북은행"],
                "전남": ["전남은행"],
                "경북": ["경북은행"],
                "경남": ["경남은행"],
                "제주": ["제주은행", "제주농협"]
            }
            
            # 지역에 따른 은행 필터링 (유연한 매칭)
            if region_filter in region_banks:
                region_pattern = f"({region_filter}|{'|'.join(region_banks[region_filter])})"
                filtered_df = filtered_df[filtered_df['금융기관'].str.contains(region_pattern, na=False, regex=True)]
            else:
                # 기본 지역명 매칭
                filtered_df = filtered_df[filtered_df['금융기관'].str.contains(region_filter, na=False)]
        
        # 특정 기관 선택 필터링
        if selected_banks:
            filtered_df = filtered_df[filtered_df['금융기관'].isin(selected_banks)]
        
        # 필터 상태 표시
        active_filters = []
        if period_filter:
            active_filters.append(f"기간: {period_filter}")
        if bank_filter:
            active_filters.append(f"유형: {bank_filter}")
        if region_filter:
            active_filters.append(f"지역: {region_filter}")
        if selected_banks:
            active_filters.append(f"기관: {', '.join(selected_banks)}")
        
        if active_filters:
            st.info(f"📊 적용된 필터: {' | '.join(active_filters)} ({len(filtered_df)}개 상품)")
            
            # 지역 필터링 안내 메시지
            if region_filter and len(filtered_df) == 0:
                st.warning(f"⚠️ '{region_filter}' 지역의 상품이 없습니다. 금융감독원 API는 본점 기준 데이터를 제공하므로, 해당 지역 기반 은행의 상품이 표시됩니다.")
                st.info("💡 **참고**: 모네타와 결과가 다를 수 있는 이유는 모네타는 지점별 상품을 표시하지만, 금융감독원 API는 본점 기준 전국 상품을 제공하기 때문입니다.")
        else:
            st.info(f"📊 전체 상품 표시 중 ({len(filtered_df)}개)")
        
        # 표시용 데이터프레임 (가입기간 컬럼이 있는지 확인)
        base_columns = ['금융기관', '상품명', '최고금리', '가입방법', '우대조건', '가입대상']
        
        if '가입기간' in filtered_df.columns:
            display_columns = base_columns + ['가입기간']
            display_df = filtered_df[display_columns].copy()
            # 가입기간 컬럼을 문자열로 변환 (리스트를 보기 좋게)
            display_df['가입기간'] = display_df['가입기간'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else str(x) if pd.notnull(x) else '정보없음'
            )
        else:
            display_df = filtered_df[base_columns].copy()
        
        # 스타일링된 테이블 표시 (페이지네이션과 고정 높이 적용)
        st.subheader("📄 상품 목록")
        
        # 페이지네이션 설정
        items_per_page = 10
        total_pages = (len(display_df) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                current_page = st.selectbox(
                    f"페이지 선택 (총 {total_pages}페이지, {len(display_df)}개 상품)",
                    range(1, total_pages + 1),
                    key="page_selector"
                )
        else:
            current_page = 1
        
        # 현재 페이지 데이터 추출
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_df = display_df.iloc[start_idx:end_idx]
        
        # 스크롤 가능한 컨테이너로 표시
        st.markdown("""
        <style>
        .scrollable-table {
            max-height: 600px;
            overflow-y: auto;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            padding: 10px;
            background-color: white;
        }
        
        .scrollable-table::-webkit-scrollbar {
            width: 12px;
        }
        
        .scrollable-table::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .scrollable-table::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
        
        .scrollable-table::-webkit-scrollbar-thumb:hover {
            background: #5a6fd8;
        }
        
        .pagination-info {
            text-align: center;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 페이지네이션 정보 표시
        st.markdown(f"""
        <div class="pagination-info">
            📄 {start_idx + 1} ~ {min(end_idx, len(display_df))}번째 상품 표시 중 (전체 {len(display_df)}개)
        </div>
        """, unsafe_allow_html=True)
        
        # 스크롤바가 보이는 데이터프레임
        with st.container():
            st.dataframe(
                page_df, 
                use_container_width=True, 
                height=400,  # 고정 높이로 스크롤바 표시
                hide_index=True
            )
        
        # 페이지 네비게이션 버튼
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if current_page > 1:
                    if st.button("⬅️ 이전", key="prev_page"):
                        st.session_state.page_selector = current_page - 1
                        st.rerun()
            
            with col2:
                if current_page > 2:
                    if st.button("1️⃣ 첫 페이지", key="first_page"):
                        st.session_state.page_selector = 1
                        st.rerun()
            
            with col3:
                st.markdown(f"<div style='text-align: center; padding: 10px; font-weight: bold;'>{current_page} / {total_pages}</div>", 
                           unsafe_allow_html=True)
            
            with col4:
                if current_page < total_pages - 1:
                    if st.button("🔚 마지막", key="last_page"):
                        st.session_state.page_selector = total_pages
                        st.rerun()
            
            with col5:
                if current_page < total_pages:
                    if st.button("다음 ➡️", key="next_page"):
                        st.session_state.page_selector = current_page + 1
                        st.rerun()
        
        # 다운로드 버튼
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
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
                            <div class="rate-highlight">{row['최고금리']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("📊 금리 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏛️ 금융기관별 최고금리 TOP 10")
            bank_max_rates = df_products.groupby('금융기관')['최고금리_숫자'].max().sort_values(ascending=False).head(10)
            
            # 테이블 형태로 표시
            bank_df = pd.DataFrame({
                '순위': range(1, len(bank_max_rates) + 1),
                '금융기관': bank_max_rates.index,
                '최고금리': [f"{rate:.2f}%" for rate in bank_max_rates.values]
            })
            st.dataframe(bank_df, use_container_width=True)
            
            # Streamlit 내장 바차트 사용
            st.bar_chart(bank_max_rates)
        
        with col2:
            st.subheader("📈 금리 구간별 상품 수")
            
            # 금리 구간별 분포
            bins = [0, 2, 3, 4, 5, float('inf')]
            labels = ['0-2%', '2-3%', '3-4%', '4-5%', '5% 이상']
            df_products['금리구간'] = pd.cut(df_products['최고금리_숫자'], bins=bins, labels=labels, include_lowest=True)
            
            rate_distribution = df_products['금리구간'].value_counts().sort_index()
            
            # 테이블로 표시
            dist_df = pd.DataFrame({
                '금리구간': rate_distribution.index,
                '상품수': rate_distribution.values,
                '비율(%)': (rate_distribution.values / len(df_products) * 100).round(1)
            })
            st.dataframe(dist_df, use_container_width=True)
            
            # Streamlit 내장 바차트 사용
            st.bar_chart(rate_distribution)
        
        # 기본금리 vs 최고금리 상관관계 섹션 제거하고 간단한 통계로 대체
        st.subheader("💹 금리 통계")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 전체 상품 수", f"{len(df_products)}개")
        with col2:
            max_single_rate = df_products['최고금리_숫자'].max()
            st.metric("🔥 단일 최고금리", f"{max_single_rate:.2f}%")
        with col3:
            high_rate_count = len(df_products[df_products['최고금리_숫자'] >= 5.0])
            st.metric("⭐ 5% 이상 상품", f"{high_rate_count}개")
        
        # 최고금리 상위 상품 테이블
        st.subheader("🎯 최고금리 상위 상품 TOP 10")
        
        if '가입기간' in df_products.columns:
            top_rate_df = df_products[['금융기관', '상품명', '최고금리', '가입기간']].head(10).copy()
            # 가입기간을 문자열로 변환
            top_rate_df['가입기간'] = top_rate_df['가입기간'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else str(x) if pd.notnull(x) else '정보없음'
            )
        else:
            top_rate_df = df_products[['금융기관', '상품명', '최고금리']].head(10)
        
        st.dataframe(top_rate_df, use_container_width=True)
    
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
