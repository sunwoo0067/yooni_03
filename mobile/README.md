# Yooni Dashboard Mobile App

운영 대시보드의 React Native 모바일 애플리케이션입니다.

## 🚀 주요 기능

- 📊 **실시간 대시보드**: WebSocket을 통한 실시간 메트릭 업데이트
- 🔐 **생체 인증**: Touch ID/Face ID를 이용한 빠른 로그인
- 🔔 **푸시 알림**: Firebase Cloud Messaging 기반 알림
- 📱 **오프라인 지원**: 오프라인 데이터 캐싱 및 동기화
- 📈 **대화형 차트**: react-native-chart-kit을 사용한 시각화
- 🌐 **다국어 지원**: i18next 기반 국제화
- 🎨 **다크 모드**: 시스템 설정 연동 테마
- 🔄 **OTA 업데이트**: CodePush를 통한 즉시 업데이트

## 📋 사전 요구사항

### 공통
- Node.js 18+
- React Native CLI
- Watchman (macOS/Linux)

### iOS 개발
- macOS (필수)
- Xcode 14+
- CocoaPods
- iOS Simulator 또는 실제 기기

### Android 개발  
- Android Studio
- JDK 11
- Android SDK
- Android Emulator 또는 실제 기기

## 🛠️ 설치

```bash
# 프로젝트 클론
git clone https://github.com/your-org/yooni-dashboard.git
cd yooni-dashboard/mobile

# 의존성 설치
npm install

# iOS 의존성 설치 (macOS)
cd ios && pod install && cd ..

# 환경 변수 설정
cp .env.example .env
```

## 🏃‍♂️ 실행

### Metro 번들러 시작
```bash
npm start
```

### iOS
```bash
# 시뮬레이터에서 실행
npm run ios

# 특정 시뮬레이터 지정
npm run ios -- --simulator="iPhone 14 Pro"

# 실제 기기에서 실행
npm run ios -- --device
```

### Android
```bash
# 에뮬레이터에서 실행
npm run android

# 특정 디바이스 지정
npm run android -- --deviceId="emulator-5554"

# 실제 기기에서 실행
npm run android -- --device
```

## 🏗️ 빌드

### 개발 빌드
```bash
# iOS
npm run build:ios:dev

# Android
npm run build:android:dev
```

### 프로덕션 빌드
```bash
# iOS
npm run build:ios:prod

# Android  
npm run build:android:prod
```

## 📦 배포

### App Store / Play Store
```bash
# iOS App Store
npm run deploy:ios

# Google Play Store
npm run deploy:android

# 베타 테스트
npm run deploy:beta
```

### CodePush (OTA 업데이트)
```bash
# iOS
npm run codepush:ios

# Android
npm run codepush:android

# 모든 플랫폼
npm run codepush:all
```

## 🧪 테스트

```bash
# 단위 테스트
npm test

# 테스트 커버리지
npm run test:coverage

# E2E 테스트
npm run e2e:ios
npm run e2e:android
```

## 📱 화면 구조

```
├── Auth/
│   ├── LoginScreen
│   ├── BiometricSetupScreen
│   └── ForgotPasswordScreen
├── Dashboard/
│   ├── DashboardScreen (홈)
│   ├── MetricsScreen
│   ├── AlertsScreen
│   └── SystemHealthScreen
├── Settings/
│   ├── SettingsScreen
│   ├── NotificationSettingsScreen
│   ├── SecuritySettingsScreen
│   └── AboutScreen
└── Modals/
    ├── ExportModal
    └── FilterModal
```

## 🔧 주요 설정

### 환경 변수 (.env)
```env
API_URL=https://api.yourdomain.com
WS_URL=wss://api.yourdomain.com
FIREBASE_API_KEY=your-firebase-api-key
CODEPUSH_KEY_IOS=your-ios-codepush-key
CODEPUSH_KEY_ANDROID=your-android-codepush-key
```

### 생체 인증 설정
앱 설정에서 Touch ID/Face ID를 활성화하면 다음 로그인부터 생체 인증을 사용할 수 있습니다.

### 푸시 알림 설정
- **시스템 알림**: 중요도 높음, 소리/진동 포함
- **주문 업데이트**: 기본 중요도
- **마케팅**: 중요도 낮음, 무음

## 🐛 문제 해결

### iOS 빌드 실패
```bash
cd ios
pod cache clean --all
rm -rf ~/Library/Caches/CocoaPods
rm -rf ~/Library/Developer/Xcode/DerivedData
pod install
```

### Android 빌드 실패
```bash
cd android
./gradlew clean
rm -rf ~/.gradle/caches/
./gradlew assembleDebug
```

### Metro 번들러 문제
```bash
npx react-native start --reset-cache
rm -rf $TMPDIR/metro-*
```

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

This project is licensed under the MIT License.