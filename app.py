<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>금융상품 비교 - 최고금리 적금/예금</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 1.1rem;
        }

        .filter-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            font-weight: 600;
            margin-bottom: 8px;
            color: #555;
        }

        .filter-group select, .filter-group input {
            padding: 12px 15px;
            border: 2px solid #e1e5e9;
            border-radius: 12px;
            font-size: 14px;
            background: white;
            transition: all 0.3s ease;
        }

        .filter-group select:focus, .filter-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .search-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .results-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
            gap: 15px;
        }

        .results-count {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
        }

        .refresh-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }

        .refresh-btn:hover {
            background: #218838;
            transform: translateY(-1px);
        }

        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .products-table th {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 15px 12px;
            text-align: center;
            font-weight: 600;
            font-size: 14px;
        }

        .products-table td {
            padding: 15px 12px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
        }

        .products-table tr:hover {
            background-color: #f8f9ff;
            transform: scale(1.001);
            transition: all 0.3s ease;
        }

        .rank {
            font-weight: bold;
            color: #667eea;
            font-size: 16px;
        }

        .bank-name {
            font-weight: 600;
            color: #333;
        }

        .product-name {
            color: #555;
            font-size: 14px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .interest-rate {
            font-weight: bold;
            color: #e74c3c;
            font-size: 16px;
        }

        .amount {
            font-weight: bold;
            color: #27ae60;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-best {
            background: #ffe6e6;
            color: #e74c3c;
        }

        .badge-new {
            background: #e8f5e8;
            color: #27ae60;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .comparison-section {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e1e5e9;
        }

        .comparison-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }

        .selected-products {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }

        .selected-product {
            background: #f8f9ff;
            border: 2px solid #667eea;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .filter-grid {
                grid-template-columns: 1fr;
            }
            
            .products-table {
                font-size: 12px;
            }
            
            .products-table th,
            .products-table td {
                padding: 10px 8px;
            }
        }

        .last-updated {
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-chart-line"></i> 금융상품 비교센터</h1>
            <p>전국 금융기관의 최고금리 적금/예금 상품을 한눈에 비교하세요</p>
        </div>

        <div class="filter-section">
            <div class="filter-grid">
                <div class="filter-group">
                    <label for="product-type">상품유형</label>
                    <select id="product-type">
                        <option value="적금">적금 (정기적립)</option>
                        <option value="예금">예금 (목돈굴리기)</option>
                        <option value="자유적립">자유적립식</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="period">기간</label>
                    <select id="period">
                        <option value="전체">전체</option>
                        <option value="3개월">3개월</option>
                        <option value="6개월">6개월</option>
                        <option value="1년">1년</option>
                        <option value="2년">2년</option>
                        <option value="3년">3년</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="bank-type">금융기관</label>
                    <select id="bank-type">
                        <option value="전체">전체</option>
                        <option value="은행">은행</option>
                        <option value="저축은행">저축은행</option>
                        <option value="신협">신협</option>
                        <option value="종금사">종금사</option>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="amount">저축금액</label>
                    <input type="number" id="amount" placeholder="100,000" value="100000">
                </div>
            </div>

            <div style="text-align: center;">
                <button class="search-btn" onclick="searchProducts()">
                    <i class="fas fa-search"></i> 상품검색
                </button>
            </div>
        </div>

        <div class="results-section">
            <div class="results-header">
                <div class="results-count" id="results-count">검색결과: 0개</div>
                <button class="refresh-btn" onclick="refreshData()">
                    <i class="fas fa-sync-alt"></i> 실시간 업데이트
                </button>
            </div>

            <div id="loading" class="loading" style="display: none;">
                <div class="spinner"></div>
                <p>최신 금리 정보를 불러오는 중...</p>
            </div>

            <table class="products-table" id="products-table">
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>금융기관명</th>
                        <th>상품명</th>
                        <th>세전금리</th>
                        <th>세후수령액</th>
                        <th>특징</th>
                        <th>비교</th>
                    </tr>
                </thead>
                <tbody id="products-tbody">
                    <!-- 동적으로 생성될 내용 -->
                </tbody>
            </table>

            <div class="last-updated" id="last-updated">
                최종 업데이트: <span id="update-time"></span>
            </div>
        </div>

        <div class="comparison-section" id="comparison-section" style="display: none;">
            <h3 class="comparison-title">선택한 상품 비교</h3>
            <div class="selected-products" id="selected-products">
                <!-- 비교할 상품들이 표시될 영역 -->
            </div>
        </div>
    </div>

    <script>
        // 샘플 데이터 (실제로는 API에서 가져올 데이터)
        let productsData = [
            {
                rank: 1,
                bankName: "우리종합금융",
                productName: "최고 연 10% 하이 정기적금(개인, 세전, 우대 포함)",
                interestRate: 10.00,
                afterTaxAmount: 12549900,
                features: ["최고금리", "우대조건"],
                type: "적금",
                period: "1년",
                bankType: "종금사"
            },
            {
                rank: 2,
                bankName: "우리종합금융",
                productName: "최고 연 6.60% The조은 정기적금(개인, 세전, 우대 포함)",
                interestRate: 6.60,
                afterTaxAmount: 12370352,
                features: ["신규상품"],
                type: "적금",
                period: "1년",
                bankType: "종금사"
            },
            {
                rank: 3,
                bankName: "서울)애큐온저축은행",
                productName: "처음만난적금",
                interestRate: 6.50,
                afterTaxAmount: 12364633,
                features: ["복리적용"],
                type: "적금",
                period: "1년",
                bankType: "저축은행"
            },
            {
                rank: 4,
                bankName: "우리은행",
                productName: "우리 Magic 적금 by 현대카드",
                interestRate: 5.70,
                afterTaxAmount: 12318969,
                features: ["카드연계"],
                type: "적금",
                period: "1년",
                bankType: "은행"
            },
            {
                rank: 5,
                bankName: "청원신용협동조합",
                productName: "정기적금",
                interestRate: 4.60,
                afterTaxAmount: 12294814,
                features: ["지역우대"],
                type: "적금",
                period: "1년",
                bankType: "신협"
            }
        ];

        let selectedProducts = [];

        function formatNumber(num) {
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        }

        function renderProducts(products) {
            const tbody = document.getElementById('products-tbody');
            const resultsCount = document.getElementById('results-count');
            
            tbody.innerHTML = '';
            resultsCount.textContent = `검색결과: ${products.length}개`;

            products.forEach(product => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="rank">${product.rank}</td>
                    <td class="bank-name">${product.bankName}</td>
                    <td class="product-name" title="${product.productName}">${product.productName}</td>
                    <td class="interest-rate">${product.interestRate.toFixed(2)}%</td>
                    <td class="amount">${formatNumber(product.afterTaxAmount)}원</td>
                    <td>
                        ${product.features.map(feature => {
                            const badgeClass = feature === '최고금리' ? 'badge-best' : 'badge-new';
                            return `<span class="badge ${badgeClass}">${feature}</span>`;
                        }).join(' ')}
                    </td>
                    <td>
                        <input type="checkbox" onchange="toggleProductComparison(${product.rank}, this.checked)">
                    </td>
                `;
                tbody.appendChild(row);
            });

            updateLastUpdated();
        }

        function searchProducts() {
            const productType = document.getElementById('product-type').value;
            const period = document.getElementById('period').value;
            const bankType = document.getElementById('bank-type').value;
            const amount = document.getElementById('amount').value;

            showLoading();

            // 실제 구현에서는 여기서 API 호출
            setTimeout(() => {
                let filteredProducts = productsData.filter(product => {
                    let matches = true;
                    
                    if (productType !== '전체' && product.type !== productType) {
                        matches = false;
                    }
                    
                    if (period !== '전체' && product.period !== period) {
                        matches = false;
                    }
                    
                    if (bankType !== '전체' && product.bankType !== bankType) {
                        matches = false;
                    }

                    return matches;
                });

                hideLoading();
                renderProducts(filteredProducts);
            }, 1000);
        }

        function refreshData() {
            showLoading();
            
            // 실시간 데이터 업데이트 시뮬레이션
            setTimeout(() => {
                // 금리를 약간 변동시켜 실시간 업데이트 효과
                productsData.forEach(product => {
                    const variation = (Math.random() - 0.5) * 0.1;
                    product.interestRate = Math.max(0.1, product.interestRate + variation);
                    product.afterTaxAmount = Math.floor(product.afterTaxAmount * (1 + variation / 100));
                });
                
                hideLoading();
                renderProducts(productsData);
                
                // 성공 알림
                const refreshBtn = document.querySelector('.refresh-btn');
                refreshBtn.innerHTML = '<i class="fas fa-check"></i> 업데이트 완료';
                refreshBtn.style.background = '#28a745';
                
                setTimeout(() => {
                    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 실시간 업데이트';
                    refreshBtn.style.background = '#28a745';
                }, 2000);
            }, 1500);
        }

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('products-table').style.opacity = '0.5';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('products-table').style.opacity = '1';
        }

        function toggleProductComparison(productRank, isSelected) {
            const product = productsData.find(p => p.rank === productRank);
            
            if (isSelected) {
                if (selectedProducts.length < 5) {
                    selectedProducts.push(product);
                } else {
                    alert('최대 5개 상품까지 비교할 수 있습니다.');
                    event.target.checked = false;
                    return;
                }
            } else {
                selectedProducts = selectedProducts.filter(p => p.rank !== productRank);
            }
            
            updateComparisonSection();
        }

        function updateComparisonSection() {
            const comparisonSection = document.getElementById('comparison-section');
            const selectedProductsDiv = document.getElementById('selected-products');
            
            if (selectedProducts.length > 0) {
                comparisonSection.style.display = 'block';
                selectedProductsDiv.innerHTML = '';
                
                selectedProducts.forEach(product => {
                    const productDiv = document.createElement('div');
                    productDiv.className = 'selected-product';
                    productDiv.innerHTML = `
                        <h4>${product.bankName}</h4>
                        <p>${product.productName}</p>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #e74c3c; margin: 10px 0;">
                            ${product.interestRate.toFixed(2)}%
                        </div>
                        <p>세후수령액: <strong>${formatNumber(product.afterTaxAmount)}원</strong></p>
                    `;
                    selectedProductsDiv.appendChild(productDiv);
                });
            } else {
                comparisonSection.style.display = 'none';
            }
        }

        function updateLastUpdated() {
            const now = new Date();
            const timeString = now.toLocaleString('ko-KR');
            document.getElementById('update-time').textContent = timeString;
        }

        // 초기 데이터 로드
        document.addEventListener('DOMContentLoaded', function() {
            renderProducts(productsData);
        });

        // 금액 입력 시 천단위 콤마 자동 추가
        document.getElementById('amount').addEventListener('input', function(e) {
            let value = e.target.value.replace(/,/g, '');
            if (value && !isNaN(value)) {
                e.target.value = formatNumber(parseInt(value));
            }
        });
    </script>
</body>
</html>
