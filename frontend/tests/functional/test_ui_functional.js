/**
 * Yooni Dropshipping System - 프론트엔드 UI 기능 테스트
 */

const puppeteer = require('puppeteer');

class UIFunctionalTestRunner {
  constructor(baseUrl = 'http://localhost:3002') {
    this.baseUrl = baseUrl;
    this.testResults = [];
  }

  async init() {
    this.browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    this.page = await this.browser.newPage();
    await this.page.setViewport({ width: 1280, height: 800 });
  }

  async cleanup() {
    await this.browser.close();
  }

  logTest(category, testName, status, message = '') {
    const result = {
      category,
      testName,
      status,
      message,
      timestamp: new Date().toISOString()
    };
    this.testResults.push(result);

    const statusSymbol = status === 'PASS' ? '✓' : status === 'FAIL' ? '✗' : '⚠';
    const color = status === 'PASS' ? '\x1b[32m' : status === 'FAIL' ? '\x1b[31m' : '\x1b[33m';
    console.log(`${color}${statusSymbol} ${category} - ${testName}${message ? ': ' + message : ''}\x1b[0m`);
  }

  async testHomePage() {
    try {
      await this.page.goto(this.baseUrl, { waitUntil: 'networkidle0' });
      await this.page.waitForSelector('body', { timeout: 5000 });
      this.logTest('페이지 로드', '홈페이지', 'PASS');
    } catch (error) {
      this.logTest('페이지 로드', '홈페이지', 'FAIL', error.message);
    }
  }

  async testDashboardPage() {
    try {
      await this.page.goto(`${this.baseUrl}/dashboard`, { waitUntil: 'networkidle0' });
      
      // 대시보드 타이틀 확인
      const title = await this.page.$eval('h4', el => el.textContent);
      if (title.includes('대시보드')) {
        this.logTest('대시보드', '페이지 렌더링', 'PASS');
      } else {
        this.logTest('대시보드', '페이지 렌더링', 'FAIL', '타이틀을 찾을 수 없음');
      }

      // 통계 카드 확인
      const statCards = await this.page.$$('.MuiCard-root');
      if (statCards.length >= 4) {
        this.logTest('대시보드', '통계 카드 표시', 'PASS');
      } else {
        this.logTest('대시보드', '통계 카드 표시', 'FAIL', `카드 개수: ${statCards.length}`);
      }
    } catch (error) {
      this.logTest('대시보드', '페이지 접근', 'FAIL', error.message);
    }
  }

  async testProductsPage() {
    try {
      await this.page.goto(`${this.baseUrl}/products`, { waitUntil: 'networkidle0' });
      await this.page.waitForSelector('body', { timeout: 5000 });
      
      // Coming Soon 메시지 확인
      const pageContent = await this.page.content();
      if (pageContent.includes('Coming Soon') || pageContent.includes('상품')) {
        this.logTest('상품 관리', '페이지 접근', 'PASS');
      } else {
        this.logTest('상품 관리', '페이지 접근', 'FAIL', '콘텐츠를 찾을 수 없음');
      }
    } catch (error) {
      this.logTest('상품 관리', '페이지 접근', 'FAIL', error.message);
    }
  }

  async testOrdersPage() {
    try {
      await this.page.goto(`${this.baseUrl}/orders`, { waitUntil: 'networkidle0' });
      await this.page.waitForSelector('body', { timeout: 5000 });
      this.logTest('주문 관리', '페이지 접근', 'PASS');
    } catch (error) {
      this.logTest('주문 관리', '페이지 접근', 'FAIL', error.message);
    }
  }

  async testResponsiveDesign() {
    try {
      // 모바일 뷰포트
      await this.page.setViewport({ width: 375, height: 667 });
      await this.page.goto(`${this.baseUrl}/dashboard`, { waitUntil: 'networkidle0' });
      
      // 사이드바가 숨겨져 있는지 확인
      const sidebarVisible = await this.page.$eval('[class*="MuiDrawer"]', el => {
        return window.getComputedStyle(el).display !== 'none';
      }).catch(() => false);
      
      if (!sidebarVisible) {
        this.logTest('반응형 디자인', '모바일 뷰', 'PASS');
      } else {
        this.logTest('반응형 디자인', '모바일 뷰', 'WARN', '사이드바가 표시됨');
      }

      // 데스크톱 뷰포트 복원
      await this.page.setViewport({ width: 1280, height: 800 });
    } catch (error) {
      this.logTest('반응형 디자인', '모바일 뷰', 'FAIL', error.message);
    }
  }

  async testNavigation() {
    try {
      await this.page.goto(`${this.baseUrl}/dashboard`, { waitUntil: 'networkidle0' });
      
      // 네비게이션 메뉴 클릭
      const menuItems = await this.page.$$('[class*="MuiListItem"]');
      if (menuItems.length > 0) {
        this.logTest('네비게이션', '메뉴 아이템 표시', 'PASS');
      } else {
        this.logTest('네비게이션', '메뉴 아이템 표시', 'FAIL', '메뉴를 찾을 수 없음');
      }
    } catch (error) {
      this.logTest('네비게이션', '메뉴 테스트', 'FAIL', error.message);
    }
  }

  async runAllTests() {
    console.log('\n=== Yooni Dropshipping System 프론트엔드 UI 기능 테스트 시작 ===\n');

    await this.init();

    // 각 테스트 실행
    await this.testHomePage();
    await this.testDashboardPage();
    await this.testProductsPage();
    await this.testOrdersPage();
    await this.testResponsiveDesign();
    await this.testNavigation();

    await this.cleanup();

    // 결과 요약
    this.printSummary();
    this.saveResults();
  }

  printSummary() {
    const total = this.testResults.length;
    const passed = this.testResults.filter(r => r.status === 'PASS').length;
    const failed = this.testResults.filter(r => r.status === 'FAIL').length;
    const warned = this.testResults.filter(r => r.status === 'WARN').length;

    console.log('\n=== 테스트 결과 요약 ===');
    console.log(`총 테스트: ${total}`);
    console.log(`\x1b[32m성공: ${passed}\x1b[0m`);
    console.log(`\x1b[31m실패: ${failed}\x1b[0m`);
    console.log(`\x1b[33m경고: ${warned}\x1b[0m`);
    console.log(`성공률: ${(passed / total * 100).toFixed(1)}%`);

    if (failed > 0) {
      console.log('\n실패한 테스트:');
      this.testResults
        .filter(r => r.status === 'FAIL')
        .forEach(r => console.log(`  - ${r.category}: ${r.testName} - ${r.message}`));
    }
  }

  saveResults() {
    const fs = require('fs');
    const filename = `ui_functional_test_results_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    
    fs.writeFileSync(filename, JSON.stringify({
      testRun: new Date().toISOString(),
      baseUrl: this.baseUrl,
      results: this.testResults,
      summary: {
        total: this.testResults.length,
        passed: this.testResults.filter(r => r.status === 'PASS').length,
        failed: this.testResults.filter(r => r.status === 'FAIL').length,
        warned: this.testResults.filter(r => r.status === 'WARN').length
      }
    }, null, 2));

    console.log(`\n결과 저장됨: ${filename}`);
  }
}

// 실행
if (require.main === module) {
  const runner = new UIFunctionalTestRunner();
  runner.runAllTests().catch(console.error);
}

module.exports = UIFunctionalTestRunner;