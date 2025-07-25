# -*- coding: utf-8 -*-
"""
드롭시핑 시스템 보안 감사 (독립 실행형)
"""
import os
import re
import json
import secrets
from datetime import datetime
from typing import Dict, List, Any, Tuple

class SecurityAuditor:
    """보안 감사 클래스"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.warnings = []
        self.audit_id = secrets.token_hex(4)
        
    def log_vulnerability(self, severity: str, category: str, description: str, 
                         file_path: str = "", recommendation: str = ""):
        """취약점 기록"""
        vuln = {
            "severity": severity,
            "category": category,
            "description": description,
            "file_path": file_path,
            "recommendation": recommendation
        }
        self.vulnerabilities.append(vuln)
        
        print(f"[{severity}] {category}: {description}")
        if file_path:
            print(f"  파일: {file_path}")
        if recommendation:
            print(f"  권장사항: {recommendation}")
        print()
    
    def log_warning(self, category: str, description: str, file_path: str = ""):
        """경고 기록"""
        warning = {
            "category": category,
            "description": description,
            "file_path": file_path
        }
        self.warnings.append(warning)
        print(f"[WARNING] {category}: {description}")
    
    def check_hardcoded_secrets(self, project_root: str):
        """하드코딩된 비밀정보 검사"""
        print("1. 하드코딩된 비밀정보 검사...")
        
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', "하드코딩된 비밀번호"),
            (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "하드코딩된 API 키"),
            (r'secret_key\s*=\s*["\'][^"\']{20,}["\']', "하드코딩된 시크릿 키"),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', "하드코딩된 토큰"),
            (r'private_key\s*=\s*["\'][^"\']{50,}["\']', "하드코딩된 개인키")
        ]
        
        found_secrets = 0
        
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        for pattern, description in secret_patterns:
                            matches = list(re.finditer(pattern, content, re.IGNORECASE))
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                self.log_vulnerability(
                                    "HIGH",
                                    "하드코딩된 비밀정보",
                                    f"{description} (라인 {line_num})",
                                    file_path,
                                    "환경변수나 보안 저장소 사용"
                                )
                                found_secrets += 1
                                
                    except Exception as e:
                        pass
        
        if found_secrets == 0:
            print("  [OK] 하드코딩된 비밀정보 없음")
    
    def check_sql_injection_risks(self, project_root: str):
        """SQL 인젝션 위험 검사"""
        print("2. SQL 인젝션 위험 검사...")
        
        sql_patterns = [
            (r'execute\s*\(\s*[f"\'"][^"\']*%[^"\']*["\']', "문자열 포매팅을 사용한 SQL"),
            (r'\.format\s*\([^)]*\)', "format 메서드 사용"),
            (r'f["\'][^"\']*{[^}]*}[^"\']*["\']', "f-string 사용")
        ]
        
        found_risks = 0
        
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if file.endswith('.py') and any(keyword in file.lower() for keyword in ['model', 'crud', 'service']):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                                for pattern, description in sql_patterns:
                                    if re.search(pattern, line, re.IGNORECASE):
                                        self.log_vulnerability(
                                            "HIGH",
                                            "SQL 인젝션 위험",
                                            f"{description} (라인 {i})",
                                            file_path,
                                            "파라미터화된 쿼리 사용"
                                        )
                                        found_risks += 1
                                        
                    except Exception as e:
                        pass
        
        if found_risks == 0:
            print("  [OK] SQL 인젝션 위험 없음")
    
    def check_authentication_security(self, project_root: str):
        """인증 보안 검사"""
        print("3. 인증 보안 검사...")
        
        security_features = {
            "password_hashing": False,
            "jwt_security": False,
            "rate_limiting": False
        }
        
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if any(keyword in file.lower() for keyword in ['auth', 'login', 'security']) and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # 패스워드 해싱 확인
                        if any(keyword in content.lower() for keyword in ['bcrypt', 'scrypt', 'pbkdf2']):
                            security_features["password_hashing"] = True
                        
                        # JWT 보안 확인
                        if 'jwt' in content.lower():
                            security_features["jwt_security"] = True
                            
                            # 위험한 JWT 설정 확인
                            if 'algorithm="none"' in content.lower():
                                self.log_vulnerability(
                                    "CRITICAL",
                                    "JWT 보안",
                                    "JWT 서명 검증 비활성화",
                                    file_path,
                                    "JWT 서명 검증 활성화"
                                )
                        
                        # Rate limiting 확인
                        if any(keyword in content.lower() for keyword in ['rate_limit', 'throttle']):
                            security_features["rate_limiting"] = True
                            
                    except Exception as e:
                        pass
        
        # 미구현 기능 경고
        for feature, implemented in security_features.items():
            if not implemented:
                self.log_warning(
                    "인증 보안",
                    f"{feature.replace('_', ' ').title()} 미구현"
                )
    
    def check_data_validation(self, project_root: str):
        """데이터 검증 검사"""
        print("4. 데이터 검증 검사...")
        
        found_issues = 0
        
        for root, dirs, files in os.walk(project_root):
            if 'api' in root.lower() or 'endpoint' in root.lower():
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            # Pydantic 검증 확인
                            has_validation = 'BaseModel' in content or 'pydantic' in content.lower()
                            if not has_validation and '@router' in content:
                                self.log_warning(
                                    "데이터 검증",
                                    "API 엔드포인트에 Pydantic 검증 없음",
                                    file_path
                                )
                            
                            # 직접적인 request 사용 확인
                            if '.json()' in content and 'request' in content and not has_validation:
                                self.log_vulnerability(
                                    "MEDIUM",
                                    "입력 검증",
                                    "검증 없는 직접 request 사용",
                                    file_path,
                                    "Pydantic 모델로 검증"
                                )
                                found_issues += 1
                                
                        except Exception as e:
                            pass
        
        if found_issues == 0:
            print("  [OK] 데이터 검증 양호")
    
    def check_dependency_security(self, project_root: str):
        """의존성 보안 검사"""
        print("5. 의존성 보안 검사...")
        
        requirements_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
        
        for req_file in requirements_files:
            file_path = os.path.join(project_root, req_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    unpinned_packages = 0
                    
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('-'):
                            # 버전 고정 확인
                            if '==' not in line and '>=' not in line and '~=' not in line:
                                package_name = line.split('[')[0].split(' ')[0]
                                if package_name:
                                    self.log_warning(
                                        "의존성 보안",
                                        f"버전 미고정 패키지: {package_name}",
                                        f"{req_file}:{i}"
                                    )
                                    unpinned_packages += 1
                    
                    if unpinned_packages == 0:
                        print(f"  [OK] {req_file} 패키지 버전 고정 양호")
                        
                except Exception as e:
                    pass
    
    def check_cors_security(self, project_root: str):
        """CORS 보안 검사"""
        print("6. CORS 보안 검사...")
        
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if any(keyword in file.lower() for keyword in ['config', 'main', 'app']) and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if 'cors' in content.lower():
                            # 와일드카드 확인
                            if 'allow_origins=["*"]' in content:
                                self.log_vulnerability(
                                    "MEDIUM",
                                    "CORS 보안",
                                    "모든 Origin 허용 (*)",
                                    file_path,
                                    "특정 도메인으로 제한"
                                )
                            
                            # Credentials 확인
                            if 'allow_credentials=true' in content.lower() and '"*"' in content:
                                self.log_vulnerability(
                                    "HIGH",
                                    "CORS 보안", 
                                    "와일드카드와 함께 Credentials 허용",
                                    file_path,
                                    "와일드카드 사용 시 Credentials 비허용"
                                )
                        else:
                            print("  [OK] CORS 설정 확인됨")
                            
                    except Exception as e:
                        pass
    
    def generate_report(self) -> Dict[str, Any]:
        """보안 리포트 생성"""
        
        # 심각도별 분류
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for vuln in self.vulnerabilities:
            severity_counts[vuln["severity"]] += 1
        
        # 보안 점수 계산
        security_score = 100
        security_score -= severity_counts["CRITICAL"] * 25
        security_score -= severity_counts["HIGH"] * 15
        security_score -= severity_counts["MEDIUM"] * 8
        security_score -= severity_counts["LOW"] * 3
        security_score = max(security_score, 0)
        
        # 등급 결정
        if security_score >= 90:
            grade = "A+ 매우안전"
        elif security_score >= 80:
            grade = "A 안전"
        elif security_score >= 70:
            grade = "B+ 양호"
        elif security_score >= 60:
            grade = "B 보통"
        else:
            grade = "C 위험"
        
        return {
            "audit_id": self.audit_id,
            "audit_date": datetime.now().isoformat(),
            "security_score": security_score,
            "security_grade": grade,
            "total_vulnerabilities": len(self.vulnerabilities),
            "severity_counts": severity_counts,
            "total_warnings": len(self.warnings),
            "vulnerabilities": self.vulnerabilities,
            "warnings": self.warnings
        }

def main():
    """메인 함수"""
    print("="*60)
    print("드롭시핑 시스템 보안 감사")
    print("="*60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    auditor = SecurityAuditor()
    project_root = "."
    
    # 보안 검사 실행
    auditor.check_hardcoded_secrets(project_root)
    auditor.check_sql_injection_risks(project_root)
    auditor.check_authentication_security(project_root)
    auditor.check_data_validation(project_root)
    auditor.check_dependency_security(project_root)
    auditor.check_cors_security(project_root)
    
    # 리포트 생성
    report = auditor.generate_report()
    
    print("="*60)
    print("보안 감사 결과")
    print("="*60)
    print(f"감사 ID: {report['audit_id']}")
    print(f"보안 점수: {report['security_score']}/100")
    print(f"보안 등급: {report['security_grade']}")
    print(f"총 취약점: {report['total_vulnerabilities']}개")
    print(f"총 경고: {report['total_warnings']}개")
    
    if report['total_vulnerabilities'] > 0:
        print(f"\n심각도별 취약점:")
        for severity, count in report['severity_counts'].items():
            if count > 0:
                print(f"  {severity}: {count}개")
    
    # 권장사항
    recommendations = []
    if report['severity_counts']['CRITICAL'] > 0:
        recommendations.append("즉시 CRITICAL 취약점 수정")
    if report['severity_counts']['HIGH'] > 0:
        recommendations.append("HIGH 우선순위 취약점 수정")
    if report['total_warnings'] > 5:
        recommendations.append("경고사항 점검 및 개선")
    
    recommendations.extend([
        "정기적인 보안 감사 수행",
        "의존성 보안 업데이트",
        "보안 교육 실시",
        "코드 리뷰 강화"
    ])
    
    print(f"\n권장사항:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    # 결과 저장
    with open("security_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n상세 리포트가 'security_audit_report.json'에 저장되었습니다.")
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()