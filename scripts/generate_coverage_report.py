#!/usr/bin/env python3
"""
테스트 커버리지 리포트 자동화 스크립트

이 스크립트는 다음 기능을 제공합니다:
- 백엔드 및 프론트엔드 커버리지 수집
- HTML, JSON, XML 형식 리포트 생성
- 커버리지 트렌드 분석
- CI/CD 통합 지원
- 커버리지 임계값 체크
"""

import os
import subprocess
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import logging
import shutil
from typing import Dict, List, Optional, Tuple
import sqlite3


class CoverageReportGenerator:
    """커버리지 리포트 생성 및 관리 클래스"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.reports_dir = self.project_root / "coverage_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # 데이터베이스 초기화 (커버리지 히스토리 저장)
        self.db_path = self.reports_dir / "coverage_history.db"
        self.setup_database()
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        log_file = self.reports_dir / f"coverage_report_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """커버리지 히스토리 데이터베이스 설정"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    project_type TEXT NOT NULL,  -- 'backend' or 'frontend'
                    total_coverage REAL NOT NULL,
                    line_coverage REAL,
                    branch_coverage REAL,
                    function_coverage REAL,
                    files_covered INTEGER,
                    total_files INTEGER,
                    lines_covered INTEGER,
                    total_lines INTEGER,
                    git_commit TEXT,
                    git_branch TEXT,
                    report_data TEXT  -- JSON 형태로 저장
                )
            """)
            conn.commit()
    
    def get_git_info(self) -> Tuple[str, str]:
        """현재 Git 커밋과 브랜치 정보 가져오기"""
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.project_root,
                text=True
            ).strip()
            
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                text=True
            ).strip()
            
            return commit, branch
        except subprocess.CalledProcessError:
            return "unknown", "unknown"
    
    def generate_backend_coverage(self, output_formats: List[str] = None) -> Dict:
        """백엔드 커버리지 생성"""
        if not output_formats:
            output_formats = ["html", "json", "xml", "term"]
            
        self.logger.info("백엔드 커버리지 생성 시작")
        
        # 백엔드 디렉토리로 이동하여 테스트 실행
        os.chdir(self.backend_dir)
        
        # 기존 커버리지 데이터 정리
        coverage_dir = self.backend_dir / ".coverage"
        if coverage_dir.exists():
            shutil.rmtree(coverage_dir)
        
        htmlcov_dir = self.backend_dir / "htmlcov"
        if htmlcov_dir.exists():
            shutil.rmtree(htmlcov_dir)
        
        # pytest로 커버리지 수집
        cmd = [
            "pytest",
            "--cov=app",
            "--cov-report=html",
            "--cov-report=json",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--cov-config=.coveragerc",
            "tests/"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            if result.returncode != 0:
                self.logger.warning(f"일부 테스트가 실패했지만 커버리지는 수집되었습니다: {result.stderr}")
            
            # 커버리지 데이터 파싱
            coverage_data = self._parse_backend_coverage()
            
            # 리포트 파일들을 reports 디렉토리로 이동
            self._move_backend_reports()
            
            return coverage_data
            
        except subprocess.TimeoutExpired:
            self.logger.error("백엔드 커버리지 생성 타임아웃")
            return {}
        except Exception as e:
            self.logger.error(f"백엔드 커버리지 생성 실패: {e}")
            return {}
    
    def _parse_backend_coverage(self) -> Dict:
        """백엔드 커버리지 JSON 데이터 파싱"""
        coverage_json_path = self.backend_dir / "coverage.json"
        
        if not coverage_json_path.exists():
            self.logger.warning("백엔드 커버리지 JSON 파일을 찾을 수 없습니다")
            return {}
        
        try:
            with open(coverage_json_path, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
            
            totals = coverage_data.get("totals", {})
            
            return {
                "total_coverage": round(totals.get("percent_covered", 0), 2),
                "line_coverage": round(totals.get("percent_covered_display", 0), 2),
                "branch_coverage": round(totals.get("percent_covered_branches", 0), 2),
                "files_covered": totals.get("num_partial", 0) + totals.get("num_covered", 0),
                "total_files": totals.get("num_statements", 0),
                "lines_covered": totals.get("covered_lines", 0),
                "total_lines": totals.get("num_statements", 0),
                "missing_lines": totals.get("missing_lines", 0),
                "excluded_lines": totals.get("excluded_lines", 0),
                "raw_data": coverage_data
            }
            
        except Exception as e:
            self.logger.error(f"백엔드 커버리지 데이터 파싱 실패: {e}")
            return {}
    
    def _move_backend_reports(self):
        """백엔드 리포트 파일들을 reports 디렉토리로 이동"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backend_reports_dir = self.reports_dir / f"backend_{timestamp}"
        backend_reports_dir.mkdir(exist_ok=True)
        
        # HTML 리포트 이동
        htmlcov_src = self.backend_dir / "htmlcov"
        if htmlcov_src.exists():
            htmlcov_dst = backend_reports_dir / "htmlcov"
            shutil.copytree(htmlcov_src, htmlcov_dst)
        
        # JSON, XML 리포트 이동
        for filename in ["coverage.json", "coverage.xml"]:
            src_file = self.backend_dir / filename
            if src_file.exists():
                dst_file = backend_reports_dir / filename
                shutil.copy2(src_file, dst_file)
    
    def generate_frontend_coverage(self) -> Dict:
        """프론트엔드 커버리지 생성"""
        self.logger.info("프론트엔드 커버리지 생성 시작")
        
        os.chdir(self.frontend_dir)
        
        # 기존 커버리지 데이터 정리
        coverage_dir = self.frontend_dir / "coverage"
        if coverage_dir.exists():
            shutil.rmtree(coverage_dir)
        
        try:
            # Vitest로 커버리지 수집
            result = subprocess.run(
                ["npm", "run", "test:coverage"],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode != 0:
                self.logger.warning(f"프론트엔드 테스트 실행 중 경고: {result.stderr}")
            
            # 커버리지 데이터 파싱
            coverage_data = self._parse_frontend_coverage()
            
            # 리포트 파일들을 reports 디렉토리로 이동
            self._move_frontend_reports()
            
            return coverage_data
            
        except subprocess.TimeoutExpired:
            self.logger.error("프론트엔드 커버리지 생성 타임아웃")
            return {}
        except Exception as e:
            self.logger.error(f"프론트엔드 커버리지 생성 실패: {e}")
            return {}
    
    def _parse_frontend_coverage(self) -> Dict:
        """프론트엔드 커버리지 JSON 데이터 파싱"""
        coverage_json_path = self.frontend_dir / "coverage" / "coverage-summary.json"
        
        if not coverage_json_path.exists():
            self.logger.warning("프론트엔드 커버리지 JSON 파일을 찾을 수 없습니다")
            return {}
        
        try:
            with open(coverage_json_path, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
            
            total = coverage_data.get("total", {})
            
            return {
                "total_coverage": round(total.get("lines", {}).get("pct", 0), 2),
                "line_coverage": round(total.get("lines", {}).get("pct", 0), 2),
                "branch_coverage": round(total.get("branches", {}).get("pct", 0), 2),
                "function_coverage": round(total.get("functions", {}).get("pct", 0), 2),
                "statement_coverage": round(total.get("statements", {}).get("pct", 0), 2),
                "lines_covered": total.get("lines", {}).get("covered", 0),
                "total_lines": total.get("lines", {}).get("total", 0),
                "functions_covered": total.get("functions", {}).get("covered", 0),
                "total_functions": total.get("functions", {}).get("total", 0),
                "raw_data": coverage_data
            }
            
        except Exception as e:
            self.logger.error(f"프론트엔드 커버리지 데이터 파싱 실패: {e}")
            return {}
    
    def _move_frontend_reports(self):
        """프론트엔드 리포트 파일들을 reports 디렉토리로 이동"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        frontend_reports_dir = self.reports_dir / f"frontend_{timestamp}"
        frontend_reports_dir.mkdir(exist_ok=True)
        
        # 커버리지 디렉토리 전체 복사
        coverage_src = self.frontend_dir / "coverage"
        if coverage_src.exists():
            coverage_dst = frontend_reports_dir / "coverage"
            shutil.copytree(coverage_src, coverage_dst)
    
    def save_coverage_history(self, project_type: str, coverage_data: Dict):
        """커버리지 히스토리 저장"""
        if not coverage_data:
            return
            
        commit, branch = self.get_git_info()
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO coverage_history 
                (timestamp, project_type, total_coverage, line_coverage, branch_coverage, 
                 function_coverage, files_covered, total_files, lines_covered, total_lines,
                 git_commit, git_branch, report_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                project_type,
                coverage_data.get("total_coverage", 0),
                coverage_data.get("line_coverage", 0),
                coverage_data.get("branch_coverage", 0),
                coverage_data.get("function_coverage", 0),
                coverage_data.get("files_covered", 0),
                coverage_data.get("total_files", 0),
                coverage_data.get("lines_covered", 0),
                coverage_data.get("total_lines", 0),
                commit,
                branch,
                json.dumps(coverage_data.get("raw_data", {}))
            ))
            conn.commit()
        
        self.logger.info(f"{project_type} 커버리지 히스토리 저장 완료")
    
    def generate_trend_report(self, days: int = 30) -> Dict:
        """커버리지 트렌드 리포트 생성"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, project_type, total_coverage, line_coverage, branch_coverage
                FROM coverage_history 
                WHERE timestamp >= ? 
                ORDER BY timestamp ASC
            """, (start_date.isoformat(),))
            
            results = cursor.fetchall()
        
        # 데이터 정리
        backend_data = []
        frontend_data = []
        
        for row in results:
            data_point = {
                "timestamp": row[0],
                "total_coverage": row[2],
                "line_coverage": row[3],
                "branch_coverage": row[4]
            }
            
            if row[1] == "backend":
                backend_data.append(data_point)
            else:
                frontend_data.append(data_point)
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "backend_trend": backend_data,
            "frontend_trend": frontend_data,
            "summary": self._calculate_trend_summary(backend_data, frontend_data)
        }
    
    def _calculate_trend_summary(self, backend_data: List, frontend_data: List) -> Dict:
        """트렌드 요약 계산"""
        summary = {}
        
        for project_type, data in [("backend", backend_data), ("frontend", frontend_data)]:
            if not data:
                summary[project_type] = {"trend": "no_data"}
                continue
                
            first_coverage = data[0]["total_coverage"]
            last_coverage = data[-1]["total_coverage"]
            change = last_coverage - first_coverage
            
            summary[project_type] = {
                "first_coverage": first_coverage,
                "last_coverage": last_coverage,
                "change": round(change, 2),
                "trend": "increasing" if change > 0 else "decreasing" if change < 0 else "stable",
                "data_points": len(data)
            }
        
        return summary
    
    def generate_consolidated_report(self, backend_data: Dict, frontend_data: Dict, 
                                   trend_data: Dict = None) -> Dict:
        """통합 커버리지 리포트 생성"""
        timestamp = datetime.now().isoformat()
        commit, branch = self.get_git_info()
        
        consolidated = {
            "report_info": {
                "timestamp": timestamp,
                "git_commit": commit,
                "git_branch": branch,
                "generator": "coverage_report_automation"
            },
            "backend": backend_data,
            "frontend": frontend_data,
            "summary": {
                "overall_coverage": round(
                    (backend_data.get("total_coverage", 0) + frontend_data.get("total_coverage", 0)) / 2, 2
                ) if backend_data and frontend_data else 0,
                "backend_coverage": backend_data.get("total_coverage", 0),
                "frontend_coverage": frontend_data.get("total_coverage", 0)
            }
        }
        
        if trend_data:
            consolidated["trends"] = trend_data
        
        return consolidated
    
    def export_report(self, report_data: Dict, format_type: str = "json"):
        """리포트 내보내기"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "json":
            output_file = self.reports_dir / f"consolidated_coverage_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
                
        elif format_type == "html":
            output_file = self.reports_dir / f"consolidated_coverage_{timestamp}.html"
            html_content = self._generate_html_report(report_data)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        self.logger.info(f"통합 리포트 저장: {output_file}")
        return output_file
    
    def _generate_html_report(self, report_data: Dict) -> str:
        """HTML 리포트 생성"""
        backend = report_data.get("backend", {})
        frontend = report_data.get("frontend", {})
        summary = report_data.get("summary", {})
        
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>테스트 커버리지 통합 리포트</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .coverage-high {{ color: #28a745; font-weight: bold; }}
        .coverage-medium {{ color: #ffc107; font-weight: bold; }}
        .coverage-low {{ color: #dc3545; font-weight: bold; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 테스트 커버리지 통합 리포트</h1>
        <p><strong>생성 시간:</strong> {report_data.get("report_info", {}).get("timestamp", "")}</p>
        <p><strong>Git 브랜치:</strong> {report_data.get("report_info", {}).get("git_branch", "")}</p>
        <p><strong>Git 커밋:</strong> {report_data.get("report_info", {}).get("git_commit", "")[:8]}</p>
    </div>
    
    <div class="section">
        <h2>📊 전체 요약</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>전체 커버리지</h3>
                <div class="{self._get_coverage_class(summary.get('overall_coverage', 0))}">{summary.get('overall_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h3>백엔드 커버리지</h3>
                <div class="{self._get_coverage_class(summary.get('backend_coverage', 0))}">{summary.get('backend_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h3>프론트엔드 커버리지</h3>
                <div class="{self._get_coverage_class(summary.get('frontend_coverage', 0))}">{summary.get('frontend_coverage', 0)}%</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🔧 백엔드 상세</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h4>라인 커버리지</h4>
                <div>{backend.get('line_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h4>브랜치 커버리지</h4>
                <div>{backend.get('branch_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h4>커버된 라인</h4>
                <div>{backend.get('lines_covered', 0)} / {backend.get('total_lines', 0)}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🌐 프론트엔드 상세</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h4>라인 커버리지</h4>
                <div>{frontend.get('line_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h4>브랜치 커버리지</h4>
                <div>{frontend.get('branch_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h4>함수 커버리지</h4>
                <div>{frontend.get('function_coverage', 0)}%</div>
            </div>
            <div class="stat-card">
                <h4>커버된 함수</h4>
                <div>{frontend.get('functions_covered', 0)} / {frontend.get('total_functions', 0)}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 권장사항</h2>
        <ul>
            {self._generate_recommendations(backend, frontend)}
        </ul>
    </div>
</body>
</html>
        """
        return html
    
    def _get_coverage_class(self, coverage: float) -> str:
        """커버리지 수치에 따른 CSS 클래스 반환"""
        if coverage >= 80:
            return "coverage-high"
        elif coverage >= 60:
            return "coverage-medium"
        else:
            return "coverage-low"
    
    def _generate_recommendations(self, backend: Dict, frontend: Dict) -> str:
        """개선 권장사항 생성"""
        recommendations = []
        
        backend_coverage = backend.get("total_coverage", 0)
        frontend_coverage = frontend.get("total_coverage", 0)
        
        if backend_coverage < 80:
            recommendations.append("<li>🔧 백엔드 테스트 커버리지를 80% 이상으로 향상시키세요.</li>")
        
        if frontend_coverage < 80:
            recommendations.append("<li>🌐 프론트엔드 테스트 커버리지를 80% 이상으로 향상시키세요.</li>")
        
        if backend.get("branch_coverage", 0) < 70:
            recommendations.append("<li>🔀 백엔드 브랜치 커버리지를 개선하세요 (조건문, 반복문 테스트).</li>")
        
        if frontend.get("function_coverage", 0) < 80:
            recommendations.append("<li>⚡ 프론트엔드 함수 커버리지를 개선하세요.</li>")
        
        if not recommendations:
            recommendations.append("<li>✅ 모든 커버리지 지표가 양호합니다!</li>")
        
        return "\\n".join(recommendations)
    
    def check_coverage_thresholds(self, backend_data: Dict, frontend_data: Dict, 
                                thresholds: Dict = None) -> Tuple[bool, List[str]]:
        """커버리지 임계값 체크"""
        if not thresholds:
            thresholds = {
                "backend_total": 80.0,
                "frontend_total": 80.0,
                "backend_branch": 70.0,
                "frontend_function": 75.0
            }
        
        violations = []
        
        # 백엔드 체크
        if backend_data.get("total_coverage", 0) < thresholds["backend_total"]:
            violations.append(
                f"백엔드 전체 커버리지: {backend_data.get('total_coverage', 0)}% < {thresholds['backend_total']}%"
            )
        
        if backend_data.get("branch_coverage", 0) < thresholds["backend_branch"]:
            violations.append(
                f"백엔드 브랜치 커버리지: {backend_data.get('branch_coverage', 0)}% < {thresholds['backend_branch']}%"
            )
        
        # 프론트엔드 체크
        if frontend_data.get("total_coverage", 0) < thresholds["frontend_total"]:
            violations.append(
                f"프론트엔드 전체 커버리지: {frontend_data.get('total_coverage', 0)}% < {thresholds['frontend_total']}%"
            )
        
        if frontend_data.get("function_coverage", 0) < thresholds["frontend_function"]:
            violations.append(
                f"프론트엔드 함수 커버리지: {frontend_data.get('function_coverage', 0)}% < {thresholds['frontend_function']}%"
            )
        
        return len(violations) == 0, violations


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="테스트 커버리지 리포트 자동화 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python generate_coverage_report.py                      # 전체 리포트 생성
  python generate_coverage_report.py --backend-only       # 백엔드만
  python generate_coverage_report.py --frontend-only      # 프론트엔드만
  python generate_coverage_report.py --format html        # HTML 형식으로 출력
  python generate_coverage_report.py --trend-days 7       # 7일간 트렌드 포함
  python generate_coverage_report.py --ci                 # CI 모드
        """
    )
    
    parser.add_argument("--backend-only", action="store_true", help="백엔드 커버리지만 생성")
    parser.add_argument("--frontend-only", action="store_true", help="프론트엔드 커버리지만 생성")
    parser.add_argument("--format", choices=["json", "html", "both"], default="both", help="출력 형식")
    parser.add_argument("--trend-days", type=int, default=30, help="트렌드 분석 기간 (일)")
    parser.add_argument("--ci", action="store_true", help="CI/CD 모드")
    parser.add_argument("--threshold-config", help="커버리지 임계값 설정 JSON 파일")
    parser.add_argument("--quiet", "-q", action="store_true", help="최소한의 출력")
    
    args = parser.parse_args()
    
    try:
        generator = CoverageReportGenerator()
        
        if not args.quiet:
            print("📊 테스트 커버리지 리포트 생성 시작")
            print("=" * 60)
        
        backend_data = {}
        frontend_data = {}
        
        # 백엔드 커버리지 생성
        if not args.frontend_only:
            if not args.quiet:
                print("🔧 백엔드 커버리지 수집 중...")
            backend_data = generator.generate_backend_coverage()
            if backend_data:
                generator.save_coverage_history("backend", backend_data)
        
        # 프론트엔드 커버리지 생성
        if not args.backend_only:
            if not args.quiet:
                print("🌐 프론트엔드 커버리지 수집 중...")
            frontend_data = generator.generate_frontend_coverage()
            if frontend_data:
                generator.save_coverage_history("frontend", frontend_data)
        
        # 트렌드 데이터 생성
        trend_data = None
        if args.trend_days > 0:
            if not args.quiet:
                print(f"📈 {args.trend_days}일간 트렌드 분석 중...")
            trend_data = generator.generate_trend_report(args.trend_days)
        
        # 통합 리포트 생성
        consolidated_report = generator.generate_consolidated_report(
            backend_data, frontend_data, trend_data
        )
        
        # 커버리지 임계값 체크
        thresholds = None
        if args.threshold_config and Path(args.threshold_config).exists():
            with open(args.threshold_config, 'r') as f:
                thresholds = json.load(f)
        
        threshold_passed, violations = generator.check_coverage_thresholds(
            backend_data, frontend_data, thresholds
        )
        
        # 리포트 출력
        if args.format in ["json", "both"]:
            json_file = generator.export_report(consolidated_report, "json")
            if not args.quiet:
                print(f"📄 JSON 리포트: {json_file}")
        
        if args.format in ["html", "both"]:
            html_file = generator.export_report(consolidated_report, "html")
            if not args.quiet:
                print(f"🌐 HTML 리포트: {html_file}")
        
        # 결과 요약 출력
        if not args.quiet:
            summary = consolidated_report["summary"]
            print(f"\\n📊 커버리지 요약:")
            print(f"  전체: {summary['overall_coverage']}%")
            print(f"  백엔드: {summary['backend_coverage']}%")
            print(f"  프론트엔드: {summary['frontend_coverage']}%")
        
        # CI 모드 JSON 출력
        if args.ci:
            ci_output = {
                "success": threshold_passed,
                "coverage_summary": consolidated_report["summary"],
                "violations": violations,
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(ci_output, indent=2, ensure_ascii=False))
        
        # 임계값 체크 결과에 따른 종료 코드
        if not threshold_passed:
            if not args.quiet:
                print("\\n❌ 커버리지 임계값 미달:")
                for violation in violations:
                    print(f"  - {violation}")
            exit(1)
        else:
            if not args.quiet:
                print("\\n✅ 모든 커버리지 임계값을 충족합니다!")
            exit(0)
            
    except KeyboardInterrupt:
        print("\\n\\n⚠️  사용자에 의해 중단되었습니다.")
        exit(130)
    except Exception as e:
        print(f"\\n💥 오류 발생: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()