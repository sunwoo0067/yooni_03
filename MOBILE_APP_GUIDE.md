# 모바일 앱 가이드 (Mobile App Guide)

## 개요

Yooni 드롭쉬핑 운영 대시보드의 모바일 버전입니다. React Native로 개발되어 iOS와 Android에서 동작하며, 실시간 모니터링과 알림 기능을 제공합니다.

## 주요 기능

### 1. 생체 인증
- **지문/Face ID 지원**: 빠르고 안전한 로그인
- **보안 자격 증명 저장**: Keychain/Keystore 활용
- **자동 인증**: 앱 실행 시 자동 인증 시도

### 2. 실시간 대시보드
- **주요 메트릭**: 매출, 주문, 고객 현황
- **실시간 업데이트**: WebSocket 기반 라이브 데이터
- **차트 시각화**: 대화형 차트로 트렌드 분석
- **시스템 상태**: 서비스 헬스 모니터링

### 3. 푸시 알림
- **즉각적인 알림**: 중요 이벤트 실시간 전달
- **커스텀 액션**: 알림에서 바로 처리 가능
- **알림 채널**: 우선순위별 알림 관리
- **백그라운드 처리**: 앱이 꺼져있어도 동작

### 4. 오프라인 기능
- **데이터 캐싱**: MMKV 기반 빠른 로컬 저장소
- **자동 동기화**: 네트워크 복구 시 자동 동기화
- **요청 큐잉**: 오프라인 작업 자동 대기열
- **충돌 해결**: 스마트 충돌 해결 메커니즘

## 설치 및 실행

### 사전 요구사항

```bash
# Node.js 18+ 설치
# React Native CLI 설치
npm install -g react-native-cli

# iOS 개발 (Mac 필요)
# Xcode 14+ 설치
# CocoaPods 설치
sudo gem install cocoapods

# Android 개발
# Android Studio 설치
# JDK 11 설치
```

### 프로젝트 설정

```bash
# 모바일 디렉토리로 이동
cd mobile

# 의존성 설치
npm install

# iOS 팟 설치 (Mac에서만)
cd ios && pod install && cd ..

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API_URL, WS_URL 등 설정
```

### 개발 실행

```bash
# Metro 번들러 시작
npm start

# iOS 실행 (Mac에서만)
npm run ios

# Android 실행
npm run android

# 특정 디바이스에서 실행
npm run ios -- --device="iPhone 14 Pro"
npm run android -- --deviceId="emulator-5554"
```

## 빌드 및 배포

### 개발 빌드

```bash
# iOS 개발 빌드
npm run build:ios:dev

# Android 개발 빌드
npm run build:android:dev
```

### 프로덕션 빌드

```bash
# iOS 프로덕션 빌드
npm run build:ios:prod

# Android 프로덕션 빌드  
npm run build:android:prod
```

### Fastlane 배포

```bash
# iOS App Store 배포
npm run deploy:ios

# Android Play Store 배포
npm run deploy:android

# 베타 테스트 배포
npm run deploy:beta
```

### CodePush 업데이트

```bash
# iOS CodePush 릴리스
npm run codepush:ios

# Android CodePush 릴리스
npm run codepush:android

# 모든 플랫폼 동시 릴리스
npm run codepush:all
```

## 아키텍처

### 디렉토리 구조

```
mobile/src/
├── components/          # 재사용 가능한 UI 컴포넌트
│   ├── charts/         # 차트 컴포넌트
│   ├── common/         # 공통 컴포넌트
│   └── metrics/        # 메트릭 표시 컴포넌트
├── screens/            # 화면 컴포넌트
│   ├── Dashboard/      # 대시보드 화면
│   ├── Metrics/        # 상세 메트릭 화면
│   ├── Alerts/         # 알림 관리 화면
│   └── Settings/       # 설정 화면
├── navigation/         # 네비게이션 설정
├── services/           # API 및 서비스
│   ├── api/           # REST API 클라이언트
│   ├── websocket/     # WebSocket 연결
│   ├── notification/  # 푸시 알림
│   └── offline/       # 오프라인 동기화
├── hooks/             # 커스텀 React 훅
├── store/             # Redux 상태 관리
├── types/             # TypeScript 타입 정의
└── utils/             # 유틸리티 함수
```

### 주요 기술 스택

- **React Native 0.72.7**: 크로스 플랫폼 모바일 개발
- **TypeScript**: 타입 안정성
- **Redux Toolkit**: 상태 관리
- **React Query**: 서버 상태 관리
- **React Navigation**: 화면 네비게이션
- **Firebase**: 푸시 알림, 분석, 크래시 리포팅
- **MMKV**: 고성능 로컬 저장소
- **React Native Biometrics**: 생체 인증
- **Socket.io Client**: WebSocket 통신

## 주요 화면

### 1. 로그인 화면
- 이메일/비밀번호 로그인
- 생체 인증 옵션
- 자동 로그인 설정

### 2. 대시보드 홈
- 주요 지표 카드
- 실시간 매출 차트
- 최근 알림 목록
- 빠른 액션 버튼

### 3. 상세 메트릭
- 기간별 필터링
- 플랫폼별 분석
- 상품별 성과
- CSV 내보내기

### 4. 알림 센터
- 알림 히스토리
- 알림 설정
- 우선순위 관리
- 일괄 처리

### 5. 시스템 상태
- 서비스 헬스 체크
- 리소스 사용률
- API 응답 시간
- 에러 로그

## 성능 최적화

### 1. 번들 최적화
- **코드 분할**: 화면별 lazy loading
- **트리 쉐이킹**: 사용하지 않는 코드 제거
- **이미지 최적화**: WebP 형식 사용
- **폰트 최적화**: 필요한 글리프만 포함

### 2. 런타임 최적화
- **메모이제이션**: React.memo, useMemo 활용
- **가상화 리스트**: FlatList 사용
- **이미지 캐싱**: Fast Image 라이브러리
- **애니메이션**: Reanimated 2 사용

### 3. 네트워크 최적화
- **요청 배치**: 여러 요청 합치기
- **캐시 전략**: 적절한 TTL 설정
- **압축**: Gzip 응답 처리
- **오프라인 우선**: 캐시 데이터 우선 표시

## 보안

### 1. 인증 및 권한
- **JWT 토큰**: 안전한 토큰 관리
- **자동 갱신**: 토큰 만료 전 갱신
- **생체 인증**: TouchID/FaceID
- **세션 관리**: 자동 로그아웃

### 2. 데이터 보호
- **암호화 저장**: 민감 데이터 암호화
- **SSL 피닝**: 중간자 공격 방지
- **난독화**: 프로덕션 코드 난독화
- **루팅/탈옥 감지**: 보안 위협 차단

### 3. 통신 보안
- **HTTPS**: 모든 API 통신 암호화
- **WebSocket Secure**: WSS 프로토콜
- **인증서 검증**: 서버 인증서 확인
- **API 키 보호**: 환경 변수 사용

## 테스트

### 단위 테스트
```bash
# 모든 테스트 실행
npm test

# 특정 파일 테스트
npm test -- Dashboard.test.tsx

# 커버리지 확인
npm run test:coverage
```

### E2E 테스트
```bash
# Detox E2E 테스트 실행
npm run e2e:ios
npm run e2e:android
```

## 디버깅

### React Native Debugger
```bash
# React Native Debugger 실행
open "rndebugger://set-debugger-loc?host=localhost&port=8081"
```

### Flipper
- 네트워크 검사
- 레이아웃 검사
- 데이터베이스 뷰어
- 로그 뷰어

### 원격 디버깅
- Chrome DevTools 사용
- 네트워크 요청 모니터링
- 콘솔 로그 확인

## 문제 해결

### iOS 빌드 실패
```bash
# 캐시 정리
cd ios && pod cache clean --all
rm -rf ~/Library/Caches/CocoaPods
rm -rf ~/Library/Developer/Xcode/DerivedData
pod install
```

### Android 빌드 실패
```bash
# 캐시 정리
cd android && ./gradlew clean
rm -rf ~/.gradle/caches/
./gradlew assembleDebug
```

### Metro 번들러 문제
```bash
# Metro 캐시 정리
npx react-native start --reset-cache
rm -rf $TMPDIR/metro-*
```

## 성능 모니터링

### Firebase Performance
- 앱 시작 시간 측정
- 화면 렌더링 시간
- 네트워크 요청 성능
- 커스텀 트레이스

### 크래시 리포팅
- Firebase Crashlytics 통합
- 자동 크래시 리포트
- 사용자 정의 로그
- 크래시 알림

## 릴리스 체크리스트

1. **버전 업데이트**
   - package.json 버전 수정
   - iOS Info.plist 버전 수정
   - Android build.gradle 버전 수정

2. **테스트**
   - 단위 테스트 통과
   - E2E 테스트 통과
   - 수동 테스트 완료

3. **빌드**
   - 프로덕션 빌드 생성
   - 빌드 아티팩트 검증
   - 크기 최적화 확인

4. **배포**
   - App Store Connect 업로드
   - Google Play Console 업로드
   - 릴리스 노트 작성

5. **모니터링**
   - 크래시 리포트 확인
   - 성능 메트릭 모니터링
   - 사용자 피드백 수집

## 다음 단계

1. **기능 확장**
   - 위젯 지원
   - Apple Watch 앱
   - 다크 모드 개선
   - 접근성 개선

2. **성능 개선**
   - 시작 시간 최적화
   - 메모리 사용 최적화
   - 배터리 사용 최적화
   - 네트워크 사용 최적화

3. **사용자 경험**
   - 온보딩 개선
   - 제스처 네비게이션
   - 햅틱 피드백
   - 애니메이션 개선