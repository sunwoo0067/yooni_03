#!/usr/bin/env python3
"""
보안 스캔 결과를 종합하여 리포트를 생성하는 스크립트
"""

import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityReportGenerator:
    """보안 리포트 생성기"""
    
    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = Path(artifacts_dir)
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_issues': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            },
            'scans': {}
        }
    
    def parse_bandit_report(self, file_path: Path) -> Dict:
        """Bandit 스캔 결과 파싱"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            issues = []
            for result in data.get('results', []):
                issues.append({
                    'file': result.get('filename'),
                    'line': result.get('line_number'),
                    'severity': result.get('issue_severity', 'UNKNOWN').lower(),
                    'confidence': result.get('issue_confidence', 'UNKNOWN').lower(),
                    'title': result.get('test_name'),
                    'description': result.get('issue_text'),
                    'cwe': result.get('test_id')
                })
            
            return {
                'tool': 'Bandit',
                'issues': issues,
                'summary': data.get('metrics', {}),
                'total_issues': len(issues)
            }
        except Exception as e:
            logger.error(f"Error parsing Bandit report: {e}")
            return {'tool': 'Bandit', 'issues': [], 'error': str(e)}
    
    def parse_semgrep_report(self, file_path: Path) -> Dict:
        """Semgrep 스캔 결과 파싱"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            issues = []
            for result in data.get('results', []):
                severity_map = {
                    'ERROR': 'high',
                    'WARNING': 'medium',
                    'INFO': 'low'
                }
                
                issues.append({
                    'file': result.get('path'),
                    'line': result.get('start', {}).get('line'),
                    'severity': severity_map.get(result.get('extra', {}).get('severity', 'INFO'), 'low'),
                    'title': result.get('check_id'),
                    'description': result.get('extra', {}).get('message', ''),
                    'rule_id': result.get('check_id')
                })
            
            return {
                'tool': 'Semgrep',
                'issues': issues,
                'total_issues': len(issues)
            }
        except Exception as e:
            logger.error(f"Error parsing Semgrep report: {e}")
            return {'tool': 'Semgrep', 'issues': [], 'error': str(e)}
    
    def parse_trivy_report(self, file_path: Path) -> Dict:
        """Trivy SARIF 결과 파싱"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            issues = []
            for run in data.get('runs', []):
                for result in run.get('results', []):
                    for location in result.get('locations', []):
                        issues.append({
                            'file': location.get('physicalLocation', {}).get('artifactLocation', {}).get('uri'),
                            'severity': result.get('level', 'info'),
                            'title': result.get('ruleId'),
                            'description': result.get('message', {}).get('text', ''),
                            'rule_id': result.get('ruleId')
                        })
            
            return {
                'tool': 'Trivy',
                'issues': issues,
                'total_issues': len(issues)
            }
        except Exception as e:
            logger.error(f"Error parsing Trivy report: {e}")
            return {'tool': 'Trivy', 'issues': [], 'error': str(e)}
    
    def parse_safety_report(self, file_path: Path) -> Dict:
        """Safety 스캔 결과 파싱"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            issues = []
            for vuln in data:
                issues.append({
                    'package': vuln.get('package'),
                    'version': vuln.get('installed_version'),
                    'severity': 'high',  # Safety는 모든 취약점을 높은 위험도로 분류
                    'title': f"Vulnerable package: {vuln.get('package')}",
                    'description': vuln.get('vulnerability'),
                    'cve': vuln.get('vulnerability_id')
                })
            
            return {
                'tool': 'Safety',
                'issues': issues,
                'total_issues': len(issues)
            }
        except Exception as e:
            logger.error(f"Error parsing Safety report: {e}")
            return {'tool': 'Safety', 'issues': [], 'error': str(e)}
    
    def parse_gitleaks_report(self, file_path: Path) -> Dict:
        """GitLeaks 결과 파싱"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            issues = []
            for leak in data:
                issues.append({
                    'file': leak.get('File'),
                    'line': leak.get('StartLine'),
                    'severity': 'critical',  # 시크릿은 모두 치명적
                    'title': f"Secret detected: {leak.get('RuleID')}",
                    'description': leak.get('Description', ''),
                    'rule_id': leak.get('RuleID'),
                    'commit': leak.get('Commit')
                })
            
            return {
                'tool': 'GitLeaks',
                'issues': issues,
                'total_issues': len(issues)
            }
        except Exception as e:
            logger.error(f"Error parsing GitLeaks report: {e}")
            return {'tool': 'GitLeaks', 'issues': [], 'error': str(e)}
    
    def collect_reports(self):
        """모든 보안 스캔 결과 수집"""
        report_parsers = {
            'bandit-report.json': self.parse_bandit_report,
            'semgrep-report.json': self.parse_semgrep_report,
            'safety-report.json': self.parse_safety_report,
            'gitleaks-report.json': self.parse_gitleaks_report
        }
        
        # 일반 리포트 파일들 처리
        for pattern, parser in report_parsers.items():
            for report_file in self.artifacts_dir.rglob(pattern):
                logger.info(f"Processing {report_file}")
                scan_result = parser(report_file)
                self.report_data['scans'][scan_result['tool']] = scan_result
                self.update_summary(scan_result)
        
        # Trivy SARIF 파일들 처리
        for sarif_file in self.artifacts_dir.rglob('trivy-*.sarif'):
            logger.info(f"Processing {sarif_file}")
            scan_result = self.parse_trivy_report(sarif_file)
            component = sarif_file.stem.replace('trivy-', '')
            self.report_data['scans'][f'Trivy-{component}'] = scan_result
            self.update_summary(scan_result)
    
    def update_summary(self, scan_result: Dict):
        """요약 정보 업데이트"""
        if 'issues' not in scan_result:
            return
        
        for issue in scan_result['issues']:
            severity = issue.get('severity', 'info').lower()
            if severity in ['critical', 'high', 'medium', 'low', 'info']:
                self.report_data['summary'][severity] += 1
                self.report_data['summary']['total_issues'] += 1
    
    def generate_html_report(self, output_file: str):
        """HTML 리포트 생성"""
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Scan Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1, h2 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; flex: 1; }}
        .metric.critical {{ background: #f8d7da; color: #721c24; }}
        .metric.high {{ background: #fff3cd; color: #856404; }}
        .metric.medium {{ background: #d1ecf1; color: #0c5460; }}
        .metric.low {{ background: #d4edda; color: #155724; }}
        .scan-section {{ margin: 30px 0; }}
        .scan-title {{ background: #007bff; color: white; padding: 10px; border-radius: 5px 5px 0 0; }}
        .issues {{ border: 1px solid #ddd; border-top: none; }}
        .issue {{ padding: 15px; border-bottom: 1px solid #eee; }}
        .issue:last-child {{ border-bottom: none; }}
        .issue-title {{ font-weight: bold; margin-bottom: 5px; }}
        .issue-meta {{ font-size: 0.9em; color: #666; margin-bottom: 10px; }}
        .severity {{ padding: 2px 8px; border-radius: 3px; color: white; font-size: 0.8em; }}
        .severity.critical {{ background: #dc3545; }}
        .severity.high {{ background: #fd7e14; }}
        .severity.medium {{ background: #ffc107; color: #000; }}
        .severity.low {{ background: #28a745; }}
        .severity.info {{ background: #17a2b8; }}
        .no-issues {{ text-align: center; padding: 40px; color: #666; }}
        .error {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Security Scan Report</h1>
        <p><strong>Generated:</strong> {timestamp}</p>
        
        <h2>📊 Summary</h2>
        <div class="summary">
            <div class="metric">
                <h3>{total_issues}</h3>
                <p>Total Issues</p>
            </div>
            <div class="metric critical">
                <h3>{critical}</h3>
                <p>Critical</p>
            </div>
            <div class="metric high">
                <h3>{high}</h3>
                <p>High</p>
            </div>
            <div class="metric medium">
                <h3>{medium}</h3>
                <p>Medium</p>
            </div>
            <div class="metric low">
                <h3>{low}</h3>
                <p>Low</p>
            </div>
            <div class="metric">
                <h3>{info}</h3>
                <p>Info</p>
            </div>
        </div>
        
        <h2>🔍 Scan Results</h2>
        {scan_sections}
    </div>
</body>
</html>
"""
        
        # 각 스캔 섹션 생성
        scan_sections = ""
        for tool_name, scan_data in self.report_data['scans'].items():
            if 'error' in scan_data:
                scan_sections += f"""
                <div class="scan-section">
                    <div class="scan-title">{tool_name}</div>
                    <div class="error">Error: {scan_data['error']}</div>
                </div>
                """
                continue
            
            issues_html = ""
            if scan_data['issues']:
                for issue in scan_data['issues']:
                    severity = issue.get('severity', 'info')
                    issues_html += f"""
                    <div class="issue">
                        <div class="issue-title">{issue.get('title', 'Unknown Issue')}</div>
                        <div class="issue-meta">
                            <span class="severity {severity}">{severity.upper()}</span>
                            {f"File: {issue['file']}" if issue.get('file') else ""}
                            {f"Line: {issue['line']}" if issue.get('line') else ""}
                        </div>
                        <div class="issue-description">{issue.get('description', '')}</div>
                    </div>
                    """
            else:
                issues_html = '<div class="no-issues">✅ No issues found</div>'
            
            scan_sections += f"""
            <div class="scan-section">
                <div class="scan-title">{tool_name} ({scan_data.get('total_issues', 0)} issues)</div>
                <div class="issues">
                    {issues_html}
                </div>
            </div>
            """
        
        # HTML 템플릿에 데이터 삽입
        html_content = html_template.format(
            timestamp=self.report_data['timestamp'],
            total_issues=self.report_data['summary']['total_issues'],
            critical=self.report_data['summary']['critical'],
            high=self.report_data['summary']['high'],
            medium=self.report_data['summary']['medium'],
            low=self.report_data['summary']['low'],
            info=self.report_data['summary']['info'],
            scan_sections=scan_sections
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {output_file}")
    
    def generate_json_report(self, output_file: str):
        """JSON 리포트 생성"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report generated: {output_file}")
    
    def generate_markdown_report(self, output_file: str):
        """Markdown 리포트 생성"""
        md_content = f"""# 🔒 Security Scan Report

**Generated:** {self.report_data['timestamp']}

## 📊 Summary

| Severity | Count |
|----------|-------|
| Total    | {self.report_data['summary']['total_issues']} |
| Critical | {self.report_data['summary']['critical']} |
| High     | {self.report_data['summary']['high']} |
| Medium   | {self.report_data['summary']['medium']} |
| Low      | {self.report_data['summary']['low']} |
| Info     | {self.report_data['summary']['info']} |

## 🔍 Scan Results

"""
        
        for tool_name, scan_data in self.report_data['scans'].items():
            md_content += f"\n### {tool_name}\n\n"
            
            if 'error' in scan_data:
                md_content += f"❌ **Error:** {scan_data['error']}\n\n"
                continue
            
            if scan_data['issues']:
                md_content += f"**Issues found:** {scan_data.get('total_issues', 0)}\n\n"
                for issue in scan_data['issues'][:10]:  # 처음 10개만 표시
                    severity_emoji = {
                        'critical': '🔴',
                        'high': '🟡',
                        'medium': '🟠',
                        'low': '🔵',
                        'info': '⚪'
                    }.get(issue.get('severity', 'info'), '⚪')
                    
                    md_content += f"- {severity_emoji} **{issue.get('title', 'Unknown')}**\n"
                    if issue.get('file'):
                        md_content += f"  - File: `{issue['file']}`"
                        if issue.get('line'):
                            md_content += f":{issue['line']}"
                        md_content += "\n"
                    if issue.get('description'):
                        md_content += f"  - {issue['description']}\n"
                    md_content += "\n"
                
                if scan_data.get('total_issues', 0) > 10:
                    md_content += f"... and {scan_data['total_issues'] - 10} more issues\n\n"
            else:
                md_content += "✅ No issues found\n\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Markdown report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive security report')
    parser.add_argument('--artifacts-dir', default='.', help='Directory containing scan artifacts')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--format', choices=['html', 'json', 'markdown'], default='html', help='Output format')
    
    args = parser.parse_args()
    
    generator = SecurityReportGenerator(args.artifacts_dir)
    generator.collect_reports()
    
    if args.format == 'html':
        generator.generate_html_report(args.output)
    elif args.format == 'json':
        generator.generate_json_report(args.output)
    elif args.format == 'markdown':
        generator.generate_markdown_report(args.output)
    
    # 요약 정보 출력
    summary = generator.report_data['summary']
    logger.info(f"Security scan completed:")
    logger.info(f"  Total issues: {summary['total_issues']}")
    logger.info(f"  Critical: {summary['critical']}")
    logger.info(f"  High: {summary['high']}")
    logger.info(f"  Medium: {summary['medium']}")
    logger.info(f"  Low: {summary['low']}")
    
    # 임계값을 초과하면 종료 코드 설정
    if summary['critical'] > 0:
        exit(2)
    elif summary['high'] > 5:
        exit(1)

if __name__ == '__main__':
    main()