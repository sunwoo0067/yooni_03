#!/usr/bin/env python3
"""
Test report generator for CI/CD pipeline
"""
import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import argparse


@dataclass
class TestSuiteResult:
    """Test suite result data"""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float
    success_rate: float
    test_cases: List[Dict[str, Any]]


@dataclass
class CoverageResult:
    """Coverage result data"""
    lines_total: int
    lines_covered: int
    branches_total: int
    branches_covered: int
    functions_total: int
    functions_covered: int
    line_rate: float
    branch_rate: float
    function_rate: float


class TestReportGenerator:
    """Generate comprehensive test reports from CI/CD artifacts"""
    
    def __init__(self, artifacts_dir: str = "."):
        self.artifacts_dir = Path(artifacts_dir)
        self.test_results: List[TestSuiteResult] = []
        self.coverage_result: Optional[CoverageResult] = None
        
    def parse_junit_xml(self, xml_file: Path) -> Optional[TestSuiteResult]:
        """Parse JUnit XML test results"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Handle both testsuite and testsuites root elements
            if root.tag == "testsuites":
                testsuite = root.find("testsuite")
                if testsuite is None:
                    return None
            else:
                testsuite = root
            
            # Extract test suite metadata
            name = testsuite.get("name", xml_file.stem)
            tests = int(testsuite.get("tests", 0))
            failures = int(testsuite.get("failures", 0))
            errors = int(testsuite.get("errors", 0))
            skipped = int(testsuite.get("skipped", 0))
            time = float(testsuite.get("time", 0))
            
            success_rate = ((tests - failures - errors) / tests * 100) if tests > 0 else 0
            
            # Extract test case details
            test_cases = []
            for testcase in testsuite.findall("testcase"):
                case_data = {
                    "name": testcase.get("name", ""),
                    "classname": testcase.get("classname", ""),
                    "time": float(testcase.get("time", 0)),
                    "status": "passed"
                }
                
                # Check for failure or error
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped_elem = testcase.find("skipped")
                
                if failure is not None:
                    case_data["status"] = "failed"
                    case_data["message"] = failure.get("message", "")
                    case_data["details"] = failure.text or ""
                elif error is not None:
                    case_data["status"] = "error"
                    case_data["message"] = error.get("message", "")
                    case_data["details"] = error.text or ""
                elif skipped_elem is not None:
                    case_data["status"] = "skipped"
                    case_data["message"] = skipped_elem.get("message", "")
                
                test_cases.append(case_data)
            
            return TestSuiteResult(
                name=name,
                tests=tests,
                failures=failures,
                errors=errors,
                skipped=skipped,
                time=time,
                success_rate=success_rate,
                test_cases=test_cases
            )
            
        except Exception as e:
            print(f"Error parsing {xml_file}: {e}")
            return None
    
    def parse_coverage_xml(self, xml_file: Path) -> Optional[CoverageResult]:
        """Parse coverage XML report"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Extract coverage metrics
            lines_total = 0
            lines_covered = 0
            branches_total = 0
            branches_covered = 0
            functions_total = 0
            functions_covered = 0
            
            # Sum up coverage from all packages/classes
            for package in root.findall(".//package"):
                for class_elem in package.findall("classes/class"):
                    for line in class_elem.findall("lines/line"):
                        lines_total += 1
                        if int(line.get("hits", 0)) > 0:
                            lines_covered += 1
                        
                        # Handle branch coverage if present
                        if line.get("branch") == "true":
                            branches_total += 1
                            condition_coverage = line.get("condition-coverage", "")
                            if "100%" in condition_coverage:
                                branches_covered += 1
            
            # Calculate rates
            line_rate = (lines_covered / lines_total) if lines_total > 0 else 0
            branch_rate = (branches_covered / branches_total) if branches_total > 0 else 0
            function_rate = 0  # Would need more detailed parsing
            
            return CoverageResult(
                lines_total=lines_total,
                lines_covered=lines_covered,
                branches_total=branches_total,
                branches_covered=branches_covered,
                functions_total=functions_total,
                functions_covered=functions_covered,
                line_rate=line_rate,
                branch_rate=branch_rate,
                function_rate=function_rate
            )
            
        except Exception as e:
            print(f"Error parsing coverage {xml_file}: {e}")
            return None
    
    def collect_test_results(self):
        """Collect all test results from artifacts"""
        print("🔍 Collecting test results...")
        
        # Find all JUnit XML files
        junit_files = list(self.artifacts_dir.glob("**/junit*.xml"))
        junit_files.extend(list(self.artifacts_dir.glob("**/*test-results*.xml")))
        
        for junit_file in junit_files:
            print(f"📄 Processing {junit_file}")
            result = self.parse_junit_xml(junit_file)
            if result:
                self.test_results.append(result)
        
        # Find coverage XML
        coverage_files = list(self.artifacts_dir.glob("**/coverage.xml"))
        if coverage_files:
            print(f"📊 Processing coverage: {coverage_files[0]}")
            self.coverage_result = self.parse_coverage_xml(coverage_files[0])
        
        print(f"✅ Collected {len(self.test_results)} test suite results")
    
    def generate_html_report(self, output_file: str = "test-report.html") -> str:
        """Generate comprehensive HTML report"""
        
        # Calculate overall statistics
        total_tests = sum(r.tests for r in self.test_results)
        total_failures = sum(r.failures for r in self.test_results)
        total_errors = sum(r.errors for r in self.test_results)
        total_skipped = sum(r.skipped for r in self.test_results)
        total_time = sum(r.time for r in self.test_results)
        
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dropshipping Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        
        .metric-card h3 {{ font-size: 1.1em; margin-bottom: 10px; color: #666; }}
        .metric-card .value {{ font-size: 2em; font-weight: bold; color: #333; }}
        
        .metric-card.success {{ border-left-color: #28a745; }}
        .metric-card.success .value {{ color: #28a745; }}
        
        .metric-card.danger {{ border-left-color: #dc3545; }}
        .metric-card.danger .value {{ color: #dc3545; }}
        
        .metric-card.warning {{ border-left-color: #ffc107; }}
        .metric-card.warning .value {{ color: #ffc107; }}
        
        .section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .section-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .section-header h2 {{ font-size: 1.5em; color: #333; }}
        
        .section-content {{ padding: 20px; }}
        
        .test-suite {{
            margin-bottom: 20px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .test-suite-header {{
            background: #f8f9fa;
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .test-suite-name {{ font-weight: bold; font-size: 1.1em; }}
        
        .test-suite-stats {{
            display: flex;
            gap: 15px;
            font-size: 0.9em;
        }}
        
        .stat {{ padding: 4px 8px; border-radius: 4px; color: white; }}
        .stat.passed {{ background: #28a745; }}
        .stat.failed {{ background: #dc3545; }}
        .stat.error {{ background: #fd7e14; }}
        .stat.skipped {{ background: #6c757d; }}
        
        .test-cases {{
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .test-case {{
            padding: 10px 15px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .test-case:last-child {{ border-bottom: none; }}
        
        .test-case-name {{ flex-grow: 1; }}
        .test-case-status {{
            padding: 2px 8px;
            border-radius: 4px;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .coverage-bar {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
        
        .coverage-text {{
            text-align: center;
            margin-top: 5px;
            font-weight: bold;
        }}
        
        .failed-tests {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }}
        
        .failed-test {{
            margin-bottom: 15px;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}
        
        .failed-test h4 {{ color: #721c24; margin-bottom: 5px; }}
        .failed-test .error-message {{ color: #721c24; font-family: monospace; font-size: 0.9em; }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-top: 30px;
            color: #666;
        }}
        
        @media (max-width: 768px) {{
            .summary {{ grid-template-columns: 1fr; }}
            .test-suite-header {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
            .test-suite-stats {{ flex-wrap: wrap; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Dropshipping Test Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total execution time: {total_time:.2f} seconds</p>
        </div>
        
        <div class="summary">
            <div class="metric-card">
                <h3>Total Tests</h3>
                <div class="value">{total_tests}</div>
            </div>
            <div class="metric-card success">
                <h3>Passed</h3>
                <div class="value">{total_tests - total_failures - total_errors}</div>
            </div>
            <div class="metric-card danger">
                <h3>Failed</h3>
                <div class="value">{total_failures}</div>
            </div>
            <div class="metric-card warning">
                <h3>Errors</h3>
                <div class="value">{total_errors}</div>
            </div>
            <div class="metric-card">
                <h3>Skipped</h3>
                <div class="value">{total_skipped}</div>
            </div>
            <div class="metric-card {'success' if overall_success_rate >= 80 else 'warning' if overall_success_rate >= 60 else 'danger'}">
                <h3>Success Rate</h3>
                <div class="value">{overall_success_rate:.1f}%</div>
            </div>
        </div>
"""
        
        # Add coverage section if available
        if self.coverage_result:
            coverage_pct = self.coverage_result.line_rate * 100
            html_content += f"""
        <div class="section">
            <div class="section-header">
                <h2>📊 Code Coverage</h2>
            </div>
            <div class="section-content">
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {coverage_pct:.1f}%"></div>
                </div>
                <div class="coverage-text">{coverage_pct:.1f}% Line Coverage</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div>
                        <strong>Lines:</strong> {self.coverage_result.lines_covered}/{self.coverage_result.lines_total} 
                        ({self.coverage_result.line_rate*100:.1f}%)
                    </div>
                    <div>
                        <strong>Branches:</strong> {self.coverage_result.branches_covered}/{self.coverage_result.branches_total} 
                        ({self.coverage_result.branch_rate*100:.1f}%)
                    </div>
                </div>
            </div>
        </div>
"""
        
        # Add test suites section
        html_content += """
        <div class="section">
            <div class="section-header">
                <h2>📋 Test Suite Results</h2>
            </div>
            <div class="section-content">
"""
        
        for suite in self.test_results:
            passed = suite.tests - suite.failures - suite.errors - suite.skipped
            
            html_content += f"""
                <div class="test-suite">
                    <div class="test-suite-header">
                        <div class="test-suite-name">
                            {'✅' if suite.failures == 0 and suite.errors == 0 else '❌'} {suite.name}
                        </div>
                        <div class="test-suite-stats">
                            <span class="stat passed">{passed} passed</span>
                            {f'<span class="stat failed">{suite.failures} failed</span>' if suite.failures > 0 else ''}
                            {f'<span class="stat error">{suite.errors} errors</span>' if suite.errors > 0 else ''}
                            {f'<span class="stat skipped">{suite.skipped} skipped</span>' if suite.skipped > 0 else ''}
                            <span>{suite.time:.2f}s</span>
                        </div>
                    </div>
"""
            
            # Add failed test details if any
            failed_cases = [case for case in suite.test_cases if case["status"] in ["failed", "error"]]
            if failed_cases:
                html_content += """
                    <div class="failed-tests">
                        <h4>❌ Failed Tests:</h4>
"""
                for case in failed_cases[:5]:  # Show first 5 failures
                    html_content += f"""
                        <div class="failed-test">
                            <h4>{case['name']}</h4>
                            <div class="error-message">{case.get('message', 'No error message')}</div>
                        </div>
"""
                
                if len(failed_cases) > 5:
                    html_content += f"<p>... and {len(failed_cases) - 5} more failures</p>"
                
                html_content += "</div>"
            
            html_content += "</div>"
        
        html_content += """
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 Generated by Dropshipping Test Automation System</p>
            <p>For detailed logs and artifacts, check the CI/CD pipeline</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML report generated: {output_file}")
        return html_content
    
    def generate_markdown_summary(self, output_file: str = "test-summary.md") -> str:
        """Generate markdown summary for PR comments"""
        
        total_tests = sum(r.tests for r in self.test_results)
        total_failures = sum(r.failures for r in self.test_results)
        total_errors = sum(r.errors for r in self.test_results)
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        # Determine status emoji
        if overall_success_rate >= 90:
            status_emoji = "🟢"
        elif overall_success_rate >= 70:
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"
        
        markdown_content = f"""# {status_emoji} Test Results Summary

## Overall Results
- **Total Tests:** {total_tests}
- **Passed:** {total_tests - total_failures - total_errors}
- **Failed:** {total_failures}
- **Errors:** {total_errors}
- **Success Rate:** {overall_success_rate:.1f}%

## Test Suites
"""
        
        for suite in self.test_results:
            passed = suite.tests - suite.failures - suite.errors - suite.skipped
            status_icon = "✅" if suite.failures == 0 and suite.errors == 0 else "❌"
            
            markdown_content += f"""
### {status_icon} {suite.name}
- Tests: {suite.tests} | Passed: {passed} | Failed: {suite.failures} | Errors: {suite.errors}
- Duration: {suite.time:.2f}s
- Success Rate: {suite.success_rate:.1f}%
"""
        
        # Add coverage if available
        if self.coverage_result:
            coverage_pct = self.coverage_result.line_rate * 100
            coverage_emoji = "🟢" if coverage_pct >= 80 else "🟡" if coverage_pct >= 60 else "🔴"
            
            markdown_content += f"""
## {coverage_emoji} Code Coverage
- **Line Coverage:** {coverage_pct:.1f}%
- **Lines:** {self.coverage_result.lines_covered}/{self.coverage_result.lines_total}
- **Branches:** {self.coverage_result.branches_covered}/{self.coverage_result.branches_total} ({self.coverage_result.branch_rate*100:.1f}%)
"""
        
        # Add failed tests details
        failed_suites = [s for s in self.test_results if s.failures > 0 or s.errors > 0]
        if failed_suites:
            markdown_content += "\n## ❌ Failed Tests\n"
            
            for suite in failed_suites:
                failed_cases = [case for case in suite.test_cases if case["status"] in ["failed", "error"]]
                markdown_content += f"\n### {suite.name}\n"
                
                for case in failed_cases[:3]:  # Show first 3 failures per suite
                    markdown_content += f"- `{case['name']}`: {case.get('message', 'No error message')}\n"
                
                if len(failed_cases) > 3:
                    markdown_content += f"- ... and {len(failed_cases) - 3} more failures\n"
        
        markdown_content += f"""
---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Test Automation*
"""
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"📝 Markdown summary generated: {output_file}")
        return markdown_content
    
    def generate_json_report(self, output_file: str = "test-results.json") -> Dict[str, Any]:
        """Generate JSON report for programmatic consumption"""
        
        total_tests = sum(r.tests for r in self.test_results)
        total_failures = sum(r.failures for r in self.test_results)
        total_errors = sum(r.errors for r in self.test_results)
        total_skipped = sum(r.skipped for r in self.test_results)
        total_time = sum(r.time for r in self.test_results)
        
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_tests - total_failures - total_errors,
                "failed": total_failures,
                "errors": total_errors,
                "skipped": total_skipped,
                "success_rate": round(overall_success_rate, 2),
                "total_time": round(total_time, 2)
            },
            "test_suites": [
                {
                    "name": suite.name,
                    "tests": suite.tests,
                    "failures": suite.failures,
                    "errors": suite.errors,
                    "skipped": suite.skipped,
                    "time": round(suite.time, 2),
                    "success_rate": round(suite.success_rate, 2),
                    "test_cases": suite.test_cases
                }
                for suite in self.test_results
            ]
        }
        
        if self.coverage_result:
            json_data["coverage"] = {
                "line_rate": round(self.coverage_result.line_rate, 4),
                "branch_rate": round(self.coverage_result.branch_rate, 4),
                "lines_total": self.coverage_result.lines_total,
                "lines_covered": self.coverage_result.lines_covered,
                "branches_total": self.coverage_result.branches_total,
                "branches_covered": self.coverage_result.branches_covered
            }
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 JSON report generated: {output_file}")
        return json_data


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate comprehensive test reports")
    
    parser.add_argument(
        "--artifacts-dir", "-d",
        default=".",
        help="Directory containing test artifacts (default: current directory)"
    )
    
    parser.add_argument(
        "--output-html", 
        default="test-report.html",
        help="HTML report output file"
    )
    
    parser.add_argument(
        "--output-markdown",
        default="test-summary.md", 
        help="Markdown summary output file"
    )
    
    parser.add_argument(
        "--output-json",
        default="test-results.json",
        help="JSON report output file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = TestReportGenerator(args.artifacts_dir)
        
        # Collect results
        generator.collect_test_results()
        
        if not generator.test_results:
            print("⚠️  No test results found")
            sys.exit(1)
        
        # Generate reports
        generator.generate_html_report(args.output_html)
        generator.generate_markdown_summary(args.output_markdown)
        generator.generate_json_report(args.output_json)
        
        # Print summary
        total_tests = sum(r.tests for r in generator.test_results)
        total_failures = sum(r.failures for r in generator.test_results)
        total_errors = sum(r.errors for r in generator.test_results)
        success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*50)
        print("📊 REPORT GENERATION SUMMARY")
        print("="*50)
        print(f"Tests: {total_tests} | Passed: {total_tests - total_failures - total_errors} | Failed: {total_failures} | Errors: {total_errors}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if generator.coverage_result:
            coverage_pct = generator.coverage_result.line_rate * 100
            print(f"Coverage: {coverage_pct:.1f}%")
        
        print("="*50)
        
        # Exit with appropriate code
        sys.exit(1 if total_failures > 0 or total_errors > 0 else 0)
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()