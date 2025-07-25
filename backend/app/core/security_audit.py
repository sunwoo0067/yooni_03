"""
보안 검토 및 취약점 분석 시스템
드롭시핑 시스템의 보안 상태를 체계적으로 분석하고 개선사항 제시
"""
import os
import re
import hashlib
import secrets
import base64
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("security_audit")


class SecurityAuditor:
    """보안 감사 관리자"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.security_warnings = []
        self.best_practices = []
        self.audit_results = {
            "audit_id": secrets.token_hex(8),
            "started_at": datetime.now().isoformat(),
            "findings": []
        }
    
    def add_vulnerability(self, severity: str, category: str, description: str, 
                         file_path: str = "", recommendation: str = ""):
        """취약점 추가"""
        vulnerability = {
            "id": secrets.token_hex(4),
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "category": category,
            "description": description,
            "file_path": file_path,
            "recommendation": recommendation,
            "found_at": datetime.now().isoformat()
        }
        
        self.vulnerabilities.append(vulnerability)
        self.audit_results["findings"].append(vulnerability)
        
        logger.warning(f"Security vulnerability found: {severity} - {description}")
    
    def add_warning(self, category: str, description: str, file_path: str = ""):
        """보안 경고 추가"""
        warning = {
            "category": category,
            "description": description,
            "file_path": file_path,
            "found_at": datetime.now().isoformat()
        }
        
        self.security_warnings.append(warning)
        logger.info(f"Security warning: {description}")
    
    def add_best_practice(self, category: str, description: str, implemented: bool = False):
        """보안 모범사례 추가"""
        practice = {
            "category": category,
            "description": description,
            "implemented": implemented,
            "checked_at": datetime.now().isoformat()
        }
        
        self.best_practices.append(practice)

    def check_file_permissions(self, project_root: str) -> None:
        """파일 권한 검사"""
        logger.info("Checking file permissions...")
        
        sensitive_files = [
            ".env",
            "config.py",
            "settings.py", 
            "secrets.json",
            "private_key.pem"
        ]
        
        for root, dirs, files in os.walk(project_root):
            for file in files:
                file_path = os.path.join(root, file)
                
                # 민감한 파일 권한 검사
                if any(sensitive in file.lower() for sensitive in sensitive_files):
                    try:
                        # Windows에서는 os.stat을 사용하여 권한 검사
                        stat_info = os.stat(file_path)
                        
                        # 파일이 존재하는 경우 경고
                        self.add_warning("File Permissions", 
                                       f"Sensitive file found: {file}",
                                       file_path)
                        
                    except Exception as e:
                        logger.debug(f"Cannot check permissions for {file_path}: {e}")
    
    def check_hardcoded_secrets(self, project_root: str) -> None:
        """하드코딩된 비밀정보 검사"""
        logger.info("Checking for hardcoded secrets...")
        
        # 의심스러운 패턴들
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Password"),
            (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded API Key"),
            (r'secret_key\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded Secret Key"),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded Token"),
            (r'aws_access_key_id\s*=\s*["\'][^"\']{20,}["\']', "AWS Access Key"),
            (r'private_key\s*=\s*["\'][^"\']{50,}["\']', "Private Key"),
            (r'jwt_secret\s*=\s*["\'][^"\']{20,}["\']', "JWT Secret")
        ]
        
        python_files = []
        for root, dirs, files in os.walk(project_root):
            # .git, __pycache__ 등 제외
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        self.add_vulnerability(
                            "HIGH",
                            "Hardcoded Secrets",
                            f"{description} found at line {line_num}",
                            file_path,
                            "Move secrets to environment variables or secure storage"
                        )
                        
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
    
    def check_sql_injection_risks(self, project_root: str) -> None:
        """SQL 인젝션 위험 검사"""
        logger.info("Checking for SQL injection risks...")
        
        # 위험한 SQL 패턴들
        sql_patterns = [
            (r'execute\s*\(\s*["\'][^"\']*%[^"\']*["\']', "String formatting in SQL"),
            (r'query\s*\(\s*["\'][^"\']*\+[^"\']*["\']', "String concatenation in SQL"),
            (r'\.format\s*\([^)]*\)', "Format string in SQL context"),
            (r'f["\'][^"\']*{[^}]*}[^"\']*["\']', "F-string in SQL context")
        ]
        
        python_files = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py') and ('model' in file.lower() or 'crud' in file.lower() or 'service' in file.lower()):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # SQL 키워드가 있는 라인만 검사
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                        for pattern, description in sql_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                self.add_vulnerability(
                                    "HIGH",
                                    "SQL Injection Risk",
                                    f"{description} at line {i}",
                                    file_path,
                                    "Use parameterized queries or ORM"
                                )
                                
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
    
    def check_authentication_security(self, project_root: str) -> None:
        """인증 보안 검사"""
        logger.info("Checking authentication security...")
        
        # 인증 관련 파일 찾기
        auth_files = []
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if any(keyword in file.lower() for keyword in ['auth', 'login', 'security', 'jwt']):
                    if file.endswith('.py'):
                        auth_files.append(os.path.join(root, file))
        
        # 보안 체크포인트들
        security_checks = {
            "password_hashing": False,
            "jwt_security": False,
            "session_security": False,
            "rate_limiting": False
        }
        
        for file_path in auth_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 패스워드 해싱 검사
                if any(keyword in content.lower() for keyword in ['bcrypt', 'scrypt', 'argon2', 'pbkdf2']):
                    security_checks["password_hashing"] = True
                
                # JWT 보안 검사
                if 'jwt' in content.lower():
                    security_checks["jwt_security"] = True
                    
                    # JWT 취약점 검사
                    if 'algorithm="none"' in content.lower() or 'verify_signature=false' in content.lower():
                        self.add_vulnerability(
                            "CRITICAL",
                            "JWT Security",
                            "JWT signature verification disabled",
                            file_path,
                            "Enable JWT signature verification"
                        )
                
                # 세션 보안 검사
                if any(keyword in content.lower() for keyword in ['session', 'cookie']):
                    security_checks["session_security"] = True
                
                # Rate limiting 검사
                if any(keyword in content.lower() for keyword in ['rate_limit', 'throttle']):
                    security_checks["rate_limiting"] = True
                    
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
        
        # 미구현된 보안 기능들 경고
        for check, implemented in security_checks.items():
            if not implemented:
                self.add_warning(
                    "Authentication Security",
                    f"{check.replace('_', ' ').title()} not found or implemented"
                )
    
    def check_dependency_security(self, project_root: str) -> None:
        """의존성 보안 검사"""
        logger.info("Checking dependency security...")
        
        requirements_files = [
            "requirements.txt",
            "requirements-dev.txt", 
            "pyproject.toml",
            "Pipfile"
        ]
        
        for req_file in requirements_files:
            file_path = os.path.join(project_root, req_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 버전이 고정되지 않은 패키지 검사
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 버전 지정이 없는 패키지
                            if '==' not in line and '>=' not in line and '~=' not in line:
                                package_name = line.split('[')[0]  # extras 제거
                                self.add_warning(
                                    "Dependency Security",
                                    f"Package '{package_name}' version not pinned at line {i}",
                                    file_path
                                )
                    
                    # 알려진 취약한 패키지들 (예시)
                    vulnerable_packages = [
                        "pillow<8.0.0",  # 예시
                        "django<3.0.0",  # 예시
                    ]
                    
                    for vuln_package in vulnerable_packages:
                        if vuln_package.split('<')[0] in content.lower():
                            self.add_vulnerability(
                                "MEDIUM",
                                "Vulnerable Dependency",
                                f"Potentially vulnerable package: {vuln_package}",
                                file_path,
                                "Update to latest secure version"
                            )
                            
                except Exception as e:
                    logger.debug(f"Cannot read requirements file {file_path}: {e}")
    
    def check_data_validation(self, project_root: str) -> None:
        """데이터 검증 보안 검사"""
        logger.info("Checking data validation security...")
        
        # API 엔드포인트 파일들 찾기
        api_files = []
        for root, dirs, files in os.walk(project_root):
            if 'api' in root.lower() or 'endpoint' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        api_files.append(os.path.join(root, file))
        
        for file_path in api_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Pydantic 모델 사용 확인
                has_pydantic = 'BaseModel' in content or 'pydantic' in content.lower()
                if not has_pydantic:
                    self.add_warning(
                        "Data Validation",
                        "No Pydantic validation found in API file",
                        file_path
                    )
                
                # 직접적인 request.json 사용 검사
                if '.json()' in content and 'request' in content:
                    self.add_vulnerability(
                        "MEDIUM",
                        "Input Validation",
                        "Direct request.json() usage without validation",
                        file_path,
                        "Use Pydantic models for request validation"
                    )
                
                # File upload 보안 검사
                if any(keyword in content.lower() for keyword in ['upload', 'file', 'multipart']):
                    if 'content_type' not in content.lower() and 'filename' in content.lower():
                        self.add_vulnerability(
                            "HIGH",
                            "File Upload Security",
                            "File upload without proper validation",
                            file_path,
                            "Validate file types and sizes"
                        )
                        
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
    
    def check_logging_security(self, project_root: str) -> None:
        """로깅 보안 검사"""
        logger.info("Checking logging security...")
        
        python_files = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 민감한 정보 로깅 검사
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if any(log_method in line.lower() for log_method in ['log.', 'logger.', 'print(']):
                        # 민감한 키워드들
                        sensitive_keywords = ['password', 'token', 'secret', 'key', 'auth']
                        
                        for keyword in sensitive_keywords:
                            if keyword in line.lower():
                                # 실제로 변수나 값이 로깅되는지 확인
                                if any(char in line for char in ['{', '%', '+']):
                                    self.add_vulnerability(
                                        "HIGH",
                                        "Information Disclosure",
                                        f"Potential sensitive data logging at line {i}",
                                        file_path,
                                        "Remove sensitive data from logs"
                                    )
                                    
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
    
    def check_cors_security(self, project_root: str) -> None:
        """CORS 보안 검사"""
        logger.info("Checking CORS security...")
        
        config_files = []
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if any(keyword in file.lower() for keyword in ['config', 'setting', 'main', 'app']):
                    if file.endswith('.py'):
                        config_files.append(os.path.join(root, file))
        
        for file_path in config_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # CORS 설정 검사
                if 'cors' in content.lower():
                    # 와일드카드 허용 검사
                    if 'allow_origins=["*"]' in content or 'allow_origins = ["*"]' in content:
                        self.add_vulnerability(
                            "MEDIUM",
                            "CORS Security",
                            "CORS allows all origins (*)",
                            file_path,
                            "Restrict CORS to specific domains"
                        )
                    
                    # Credentials 허용 검사
                    if 'allow_credentials=true' in content.lower() and '"*"' in content:
                        self.add_vulnerability(
                            "HIGH",
                            "CORS Security",
                            "CORS allows credentials with wildcard origins",
                            file_path,
                            "Do not allow credentials with wildcard origins"
                        )
                        
            except Exception as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
    
    def generate_security_report(self) -> Dict[str, Any]:
        """보안 리포트 생성"""
        self.audit_results["completed_at"] = datetime.now().isoformat()
        
        # 취약점 심각도별 분류
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for vuln in self.vulnerabilities:
            severity_counts[vuln["severity"]] += 1
        
        # 카테고리별 분류
        category_counts = {}
        for vuln in self.vulnerabilities:
            category = vuln["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 보안 점수 계산 (100점 만점)
        security_score = 100
        security_score -= severity_counts["CRITICAL"] * 20
        security_score -= severity_counts["HIGH"] * 10
        security_score -= severity_counts["MEDIUM"] * 5
        security_score -= severity_counts["LOW"] * 2
        security_score = max(security_score, 0)
        
        # 등급 결정
        if security_score >= 90:
            grade = "A+ (매우 안전)"
        elif security_score >= 80:
            grade = "A (안전)"
        elif security_score >= 70:
            grade = "B+ (양호)"
        elif security_score >= 60:
            grade = "B (보통)"
        elif security_score >= 50:
            grade = "C+ (주의)"
        else:
            grade = "C (위험)"
        
        report = {
            "audit_summary": {
                "audit_id": self.audit_results["audit_id"],
                "started_at": self.audit_results["started_at"],
                "completed_at": self.audit_results["completed_at"],
                "security_score": security_score,
                "security_grade": grade
            },
            "vulnerability_summary": {
                "total_vulnerabilities": len(self.vulnerabilities),
                "by_severity": severity_counts,
                "by_category": category_counts
            },
            "vulnerabilities": self.vulnerabilities,
            "warnings": self.security_warnings,
            "best_practices": self.best_practices,
            "recommendations": self._generate_recommendations(severity_counts)
        }
        
        return report
    
    def _generate_recommendations(self, severity_counts: Dict[str, int]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if severity_counts["CRITICAL"] > 0:
            recommendations.append("즉시 CRITICAL 취약점 수정 필요")
        
        if severity_counts["HIGH"] > 0:
            recommendations.append("HIGH 우선순위 취약점 수정")
        
        if severity_counts["MEDIUM"] > 5:
            recommendations.append("MEDIUM 취약점이 많습니다. 계획적 수정 필요")
        
        # 일반적인 보안 권장사항
        recommendations.extend([
            "정기적인 보안 감사 수행",
            "의존성 보안 업데이트",
            "보안 교육 및 코드 리뷰 강화",
            "보안 테스트 자동화",
            "침입 탐지 시스템 구축"
        ])
        
        return recommendations


def run_security_audit(project_root: str = ".") -> Dict[str, Any]:
    """보안 감사 실행"""
    auditor = SecurityAuditor()
    
    logger.info(f"Starting security audit for project: {project_root}")
    
    try:
        # 각종 보안 검사 실행
        auditor.check_file_permissions(project_root)
        auditor.check_hardcoded_secrets(project_root)
        auditor.check_sql_injection_risks(project_root)
        auditor.check_authentication_security(project_root)
        auditor.check_dependency_security(project_root)
        auditor.check_data_validation(project_root)
        auditor.check_logging_security(project_root)
        auditor.check_cors_security(project_root)
        
        # 보안 리포트 생성
        report = auditor.generate_security_report()
        
        logger.info(f"Security audit completed. Score: {report['audit_summary']['security_score']}/100")
        
        return report
        
    except Exception as e:
        logger.error(f"Security audit failed: {e}")
        return {
            "error": str(e),
            "audit_id": auditor.audit_results["audit_id"],
            "started_at": auditor.audit_results["started_at"],
            "failed_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # 보안 감사 실행
    report = run_security_audit()
    
    # 결과 출력
    print("=" * 80)
    print("🔒 보안 감사 리포트")
    print("=" * 80)
    
    if "error" in report:
        print(f"❌ 감사 실패: {report['error']}")
    else:
        summary = report["audit_summary"]
        vuln_summary = report["vulnerability_summary"]
        
        print(f"감사 ID: {summary['audit_id']}")
        print(f"보안 점수: {summary['security_score']}/100")
        print(f"보안 등급: {summary['security_grade']}")
        print(f"\n취약점 현황:")
        print(f"  - 총 취약점: {vuln_summary['total_vulnerabilities']}개")
        
        for severity, count in vuln_summary["by_severity"].items():
            if count > 0:
                print(f"  - {severity}: {count}개")
        
        if report["recommendations"]:
            print(f"\n권장사항:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")
    
    # JSON 파일로 저장
    with open("security_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 상세 리포트가 'security_audit_report.json'에 저장되었습니다.")