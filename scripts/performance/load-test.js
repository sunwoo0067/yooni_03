import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// 커스텀 메트릭
const errorRate = new Rate('errors');
const productListDuration = new Trend('product_list_duration');
const productDetailDuration = new Trend('product_detail_duration');
const searchDuration = new Trend('search_duration');
const orderCreationDuration = new Trend('order_creation_duration');

// 테스트 옵션
export const options = {
  scenarios: {
    // 일반 사용자 시나리오
    regular_users: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // 50명까지 증가
        { duration: '5m', target: 50 },   // 50명 유지
        { duration: '2m', target: 100 },  // 100명까지 증가
        { duration: '5m', target: 100 },  // 100명 유지
        { duration: '2m', target: 0 },    // 종료
      ],
      exec: 'regularUserScenario',
    },
    // 피크 시간 시나리오
    peak_hours: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '1m', target: 50 },
        { duration: '2m', target: 100 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 10 },
      ],
      exec: 'peakHourScenario',
    },
  },
  thresholds: {
    // 전체 요청
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.05'],
    
    // 개별 엔드포인트
    product_list_duration: ['p(95)<300'],
    product_detail_duration: ['p(95)<200'],
    search_duration: ['p(95)<500'],
    order_creation_duration: ['p(95)<1000'],
    
    // 에러율
    errors: ['rate<0.05'],
  },
  tags: {
    testid: `${__ENV.TEST_RUN_ID || Date.now()}`,
  },
};

// 테스트 데이터
const searchTerms = ['laptop', 'phone', 'tablet', 'monitor', 'keyboard'];
const categories = ['electronics', 'computers', 'accessories', 'smartphones'];

// 헬퍼 함수
function makeRequest(name, method, url, payload = null, params = {}) {
  const defaultParams = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    tags: { name },
  };
  
  const mergedParams = Object.assign({}, defaultParams, params);
  
  let response;
  const startTime = new Date().getTime();
  
  if (method === 'GET') {
    response = http.get(url, mergedParams);
  } else if (method === 'POST') {
    response = http.post(url, JSON.stringify(payload), mergedParams);
  }
  
  const duration = new Date().getTime() - startTime;
  
  // 메트릭 기록
  switch (name) {
    case 'product_list':
      productListDuration.add(duration);
      break;
    case 'product_detail':
      productDetailDuration.add(duration);
      break;
    case 'search':
      searchDuration.add(duration);
      break;
    case 'order_creation':
      orderCreationDuration.add(duration);
      break;
  }
  
  // 응답 검증
  const checkResult = check(response, {
    [`${name} status is 200`]: (r) => r.status === 200,
    [`${name} response time OK`]: (r) => r.timings.duration < 500,
    [`${name} has body`]: (r) => r.body && r.body.length > 0,
  });
  
  if (!checkResult) {
    errorRate.add(1);
    console.error(`Error in ${name}: ${response.status} - ${response.body}`);
  }
  
  return response;
}

// 일반 사용자 시나리오
export function regularUserScenario() {
  const baseUrl = __ENV.TARGET_URL || 'http://localhost:8000';
  
  group('Browse Products', () => {
    // 상품 목록 조회
    const listResponse = makeRequest(
      'product_list',
      'GET',
      `${baseUrl}/api/v1/products?page=1&per_page=20`
    );
    
    sleep(randomIntBetween(1, 3));
    
    // 카테고리별 조회
    const category = randomItem(categories);
    makeRequest(
      'category_products',
      'GET',
      `${baseUrl}/api/v1/products?category=${category}`
    );
    
    sleep(randomIntBetween(2, 5));
  });
  
  group('Search Products', () => {
    // 상품 검색
    const searchTerm = randomItem(searchTerms);
    const searchResponse = makeRequest(
      'search',
      'GET',
      `${baseUrl}/api/v1/products/search?q=${searchTerm}`
    );
    
    sleep(randomIntBetween(1, 2));
    
    // 검색 결과에서 상품 선택
    if (searchResponse.status === 200) {
      try {
        const results = JSON.parse(searchResponse.body).results;
        if (results && results.length > 0) {
          const product = randomItem(results);
          makeRequest(
            'product_detail',
            'GET',
            `${baseUrl}/api/v1/products/${product.id}`
          );
        }
      } catch (e) {
        console.error('Failed to parse search results:', e);
      }
    }
    
    sleep(randomIntBetween(3, 7));
  });
}

// 피크 시간 시나리오
export function peakHourScenario() {
  const baseUrl = __ENV.TARGET_URL || 'http://localhost:8000';
  const userId = `user_${__VU}_${__ITER}`;
  
  group('Quick Purchase Flow', () => {
    // 빠른 상품 조회
    const listResponse = makeRequest(
      'product_list',
      'GET',
      `${baseUrl}/api/v1/products?page=1&per_page=10`
    );
    
    if (listResponse.status === 200) {
      try {
        const products = JSON.parse(listResponse.body).results;
        if (products && products.length > 0) {
          // 상품 2-3개 빠르게 조회
          const numProducts = randomIntBetween(2, 3);
          for (let i = 0; i < Math.min(numProducts, products.length); i++) {
            makeRequest(
              'product_detail',
              'GET',
              `${baseUrl}/api/v1/products/${products[i].id}`
            );
            sleep(randomIntBetween(1, 2));
          }
          
          // 주문 시뮬레이션 (인증 필요시 스킵)
          if (__ENV.AUTH_TOKEN) {
            const orderPayload = {
              user_id: userId,
              items: [
                {
                  product_id: products[0].id,
                  quantity: randomIntBetween(1, 3),
                  price: products[0].price,
                }
              ],
              shipping_address: {
                street: '123 Test St',
                city: 'Test City',
                postal_code: '12345',
              }
            };
            
            makeRequest(
              'order_creation',
              'POST',
              `${baseUrl}/api/v1/orders`,
              orderPayload,
              {
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${__ENV.AUTH_TOKEN}`,
                }
              }
            );
          }
        }
      } catch (e) {
        console.error('Failed to process products:', e);
      }
    }
  });
  
  sleep(randomIntBetween(1, 3));
}

// 유틸리티 함수
function randomIntBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min);
}

// 셋업 함수
export function setup() {
  const baseUrl = __ENV.TARGET_URL || 'http://localhost:8000';
  
  // 헬스체크
  const healthCheck = http.get(`${baseUrl}/health`);
  if (healthCheck.status !== 200) {
    throw new Error(`Health check failed: ${healthCheck.status}`);
  }
  
  console.log('Performance test started');
  console.log(`Target URL: ${baseUrl}`);
  console.log(`Test ID: ${options.tags.testid}`);
  
  return {
    baseUrl,
    startTime: new Date().toISOString(),
  };
}

// 테스트 종료 처리
export function teardown(data) {
  console.log('Performance test completed');
  console.log(`Start time: ${data.startTime}`);
  console.log(`End time: ${new Date().toISOString()}`);
}

// 기본 함수 (scenarios를 사용하지 않을 경우)
export default function() {
  regularUserScenario();
}