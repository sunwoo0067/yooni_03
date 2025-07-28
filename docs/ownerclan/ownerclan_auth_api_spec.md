# 오너클랜 인증 API 명세서

## 개요
오너클랜 API는 JWT(JSON Web Token) 기반의 인증 시스템을 사용합니다. API를 사용하기 전에 인증 엔드포인트를 통해 토큰을 발급받아야 합니다.

## 인증 엔드포인트

### 환경별 URL
- **Production**: `https://auth.ownerclan.com/auth`
- **Sandbox**: `https://auth-sandbox.ownerclan.com/auth`

## 토큰 발급

### HTTP 메서드
```
POST /auth
```

### 요청 헤더
```
Content-Type: application/json
```

### 요청 본문
```json
{
    "service": "ownerclan",
    "userType": "seller",
    "username": "판매사ID",
    "password": "판매사PW"
}
```

#### 파라미터 설명
| 필드 | 타입 | 필수 여부 | 설명 |
|------|------|-----------|------|
| service | string | 필수 | 서비스 구분자 (고정값: "ownerclan") |
| userType | string | 필수 | 사용자 타입 (고정값: "seller") |
| username | string | 필수 | 판매사 ID |
| password | string | 필수 | 판매사 비밀번호 |

### 응답

#### 성공 응답 (200 OK)
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 3600,
    "tokenType": "Bearer"
}
```

#### 응답 필드 설명
| 필드 | 타입 | 설명 |
|------|------|------|
| token | string | JWT 액세스 토큰 |
| expiresIn | number | 토큰 만료 시간 (초 단위) |
| tokenType | string | 토큰 타입 (Bearer) |

#### 오류 응답

**401 Unauthorized - 인증 실패**
```json
{
    "error": "AUTHENTICATION_FAILED",
    "message": "Invalid username or password"
}
```

**400 Bad Request - 잘못된 요청**
```json
{
    "error": "INVALID_REQUEST",
    "message": "Missing required fields"
}
```

**429 Too Many Requests - 요청 제한 초과**
```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Too many authentication attempts"
}
```

## 토큰 사용

### GraphQL API 요청 시 인증
발급받은 토큰을 Authorization 헤더에 포함하여 GraphQL API를 호출합니다.

```
Authorization: Bearer {token}
```

### 예시 요청
```http
GET /v1/graphql?query=query{item(key:"W000000"){name,model}}
Host: api-sandbox.ownerclan.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 구현 예제

### JavaScript (jQuery)
```javascript
var authData = {
    service: "ownerclan",
    userType: "seller",
    username: "판매사ID",
    password: "판매사PW"
};

$.ajax({
    url: "https://auth-sandbox.ownerclan.com/auth",
    type: "POST",
    contentType: "application/json",
    processData: false,
    data: JSON.stringify(authData),
    success: function(data) {
        console.log("토큰 발급 성공:", data.token);
        // 토큰을 로컬 스토리지나 변수에 저장
        localStorage.setItem('ownerclan_token', data.token);
    },
    error: function(xhr) {
        console.error("인증 실패:", xhr.responseText, xhr.status);
    }
});
```

### JavaScript (Fetch API)
```javascript
async function authenticateOwnerClan(username, password) {
    try {
        const response = await fetch('https://auth-sandbox.ownerclan.com/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                service: "ownerclan",
                userType: "seller",
                username: username,
                password: password
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.token;
    } catch (error) {
        console.error('인증 오류:', error);
        throw error;
    }
}

// 사용 예시
authenticateOwnerClan('your_username', 'your_password')
    .then(token => {
        console.log('토큰 발급 완료:', token);
        // GraphQL API 호출에 사용
    })
    .catch(error => {
        console.error('인증 실패:', error);
    });
```

### Node.js (axios)
```javascript
const axios = require('axios');

async function getOwnerClanToken(username, password) {
    try {
        const response = await axios.post('https://auth-sandbox.ownerclan.com/auth', {
            service: "ownerclan",
            userType: "seller",
            username: username,
            password: password
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });

        return response.data.token;
    } catch (error) {
        if (error.response) {
            console.error('인증 실패:', error.response.data);
        } else {
            console.error('네트워크 오류:', error.message);
        }
        throw error;
    }
}
```

## 보안 고려사항

### 토큰 저장
- 클라이언트 측에서는 토큰을 안전하게 저장해야 합니다
- 웹 애플리케이션: localStorage 또는 sessionStorage 사용
- 모바일 앱: Keychain (iOS) 또는 KeyStore (Android) 사용

### 토큰 만료 처리
- 토큰 만료 시 401 Unauthorized 응답을 받게 됩니다
- 자동으로 재인증을 수행하는 로직을 구현하는 것을 권장합니다

### HTTPS 사용
- 모든 인증 요청은 반드시 HTTPS를 통해 전송되어야 합니다
- 프로덕션 환경에서는 SSL/TLS 인증서가 유효한지 확인하세요

## 문제 해결

### 자주 발생하는 오류
1. **401 Unauthorized**: 사용자명 또는 비밀번호가 잘못됨
2. **400 Bad Request**: 요청 형식이 올바르지 않음
3. **429 Too Many Requests**: 너무 많은 인증 시도

### 디버깅 팁
- 요청 본문이 올바른 JSON 형식인지 확인
- Content-Type 헤더가 'application/json'으로 설정되었는지 확인
- 네트워크 탭에서 실제 전송되는 데이터 확인