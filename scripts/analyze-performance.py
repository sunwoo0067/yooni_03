#!/usr/bin/env python3
"""
성능 테스트 결과 분석 스크립트.
k6 테스트 결과를 분석하여 보고서를 생성합니다.
"""
import json
import sys
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class PerformanceAnalyzer:
    """성능 테스트 결과 분석기"""
    
    def __init__(self, results_file: str):
        self.results_file = Path(results_file)
        self.results = []
        self.metrics = {}
        
    def load_results(self):
        """k6 JSON 결과 파일 로드"""
        with open(self.results_file, 'r') as f:
            for line in f:
                if line.strip():
                    self.results.append(json.loads(line))
                    
    def analyze(self):
        """결과 분석"""
        # 메트릭별로 데이터 그룹화
        for result in self.results:
            if result['type'] == 'Point':
                metric_name = result['metric']
                if metric_name not in self.metrics:
                    self.metrics[metric_name] = []
                self.metrics[metric_name].append({
                    'value': result['data']['value'],
                    'time': result['data']['time'],
                    'tags': result['data'].get('tags', {})
                })
                
    def generate_summary(self) -> Dict[str, Any]:
        """요약 통계 생성"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_requests': len(self.results),
            'metrics': {}
        }
        
        # HTTP 요청 지속 시간 분석
        if 'http_req_duration' in self.metrics:
            durations = [m['value'] for m in self.metrics['http_req_duration']]
            summary['metrics']['http_req_duration'] = {
                'count': len(durations),
                'mean': statistics.mean(durations),
                'median': statistics.median(durations),
                'min': min(durations),
                'max': max(durations),
                'p90': np.percentile(durations, 90),
                'p95': np.percentile(durations, 95),
                'p99': np.percentile(durations, 99),
                'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
            }
            
        # 에러율 계산
        if 'http_req_failed' in self.metrics:
            failures = [m['value'] for m in self.metrics['http_req_failed']]
            error_rate = sum(failures) / len(failures) if failures else 0
            summary['metrics']['error_rate'] = {
                'rate': error_rate * 100,
                'total_errors': sum(failures),
                'total_requests': len(failures)
            }
            
        # 처리량 계산
        if 'http_reqs' in self.metrics:
            reqs_data = self.metrics['http_reqs']
            if reqs_data:
                time_range = max(m['time'] for m in reqs_data) - min(m['time'] for m in reqs_data)
                if time_range > 0:
                    throughput = len(reqs_data) / (time_range / 1000)  # requests per second
                    summary['metrics']['throughput'] = {
                        'requests_per_second': throughput
                    }
                    
        # 개별 엔드포인트 분석
        endpoint_metrics = ['product_list_duration', 'product_detail_duration', 
                          'search_duration', 'order_creation_duration']
        
        for metric in endpoint_metrics:
            if metric in self.metrics:
                values = [m['value'] for m in self.metrics[metric]]
                if values:
                    summary['metrics'][metric] = {
                        'count': len(values),
                        'mean': statistics.mean(values),
                        'p95': np.percentile(values, 95),
                        'p99': np.percentile(values, 99)
                    }
                    
        return summary
        
    def check_thresholds(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """임계값 검사"""
        violations = []
        
        # 응답 시간 임계값
        if 'http_req_duration' in summary['metrics']:
            duration_stats = summary['metrics']['http_req_duration']
            if duration_stats['p95'] > 500:
                violations.append({
                    'metric': 'http_req_duration_p95',
                    'threshold': 500,
                    'actual': duration_stats['p95'],
                    'severity': 'warning'
                })
            if duration_stats['p99'] > 1000:
                violations.append({
                    'metric': 'http_req_duration_p99',
                    'threshold': 1000,
                    'actual': duration_stats['p99'],
                    'severity': 'critical'
                })
                
        # 에러율 임계값
        if 'error_rate' in summary['metrics']:
            error_rate = summary['metrics']['error_rate']['rate']
            if error_rate > 5:
                violations.append({
                    'metric': 'error_rate',
                    'threshold': 5,
                    'actual': error_rate,
                    'severity': 'critical'
                })
            elif error_rate > 1:
                violations.append({
                    'metric': 'error_rate',
                    'threshold': 1,
                    'actual': error_rate,
                    'severity': 'warning'
                })
                
        return violations
        
    def generate_charts(self, output_dir: Path):
        """차트 생성"""
        output_dir.mkdir(exist_ok=True)
        
        # 응답 시간 분포 히스토그램
        if 'http_req_duration' in self.metrics:
            durations = [m['value'] for m in self.metrics['http_req_duration']]
            
            plt.figure(figsize=(10, 6))
            plt.hist(durations, bins=50, alpha=0.7, color='blue', edgecolor='black')
            plt.axvline(np.percentile(durations, 95), color='red', linestyle='--', 
                       label=f'P95: {np.percentile(durations, 95):.2f}ms')
            plt.axvline(np.percentile(durations, 99), color='orange', linestyle='--', 
                       label=f'P99: {np.percentile(durations, 99):.2f}ms')
            plt.xlabel('Response Time (ms)')
            plt.ylabel('Frequency')
            plt.title('Response Time Distribution')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(output_dir / 'response_time_distribution.png', dpi=150, bbox_inches='tight')
            plt.close()
            
        # 시간별 응답 시간 추이
        if 'http_req_duration' in self.metrics:
            data = self.metrics['http_req_duration']
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df = df.set_index('time').sort_index()
            
            # 1분 단위로 리샘플링
            resampled = df['value'].resample('1T').agg(['mean', 'max', 'count'])
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            
            # 응답 시간 추이
            ax1.plot(resampled.index, resampled['mean'], label='Mean', color='blue')
            ax1.plot(resampled.index, resampled['max'], label='Max', color='red', alpha=0.7)
            ax1.set_ylabel('Response Time (ms)')
            ax1.set_title('Response Time Over Time')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 요청 수 추이
            ax2.plot(resampled.index, resampled['count'], color='green')
            ax2.set_ylabel('Requests per Minute')
            ax2.set_xlabel('Time')
            ax2.set_title('Request Rate Over Time')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / 'response_time_timeline.png', dpi=150, bbox_inches='tight')
            plt.close()
            
        # 엔드포인트별 성능 비교
        endpoint_metrics = {
            'product_list_duration': 'Product List',
            'product_detail_duration': 'Product Detail',
            'search_duration': 'Search',
            'order_creation_duration': 'Order Creation'
        }
        
        endpoint_data = []
        for metric_key, label in endpoint_metrics.items():
            if metric_key in self.metrics:
                values = [m['value'] for m in self.metrics[metric_key]]
                if values:
                    endpoint_data.append({
                        'endpoint': label,
                        'mean': statistics.mean(values),
                        'p95': np.percentile(values, 95),
                        'p99': np.percentile(values, 99)
                    })
                    
        if endpoint_data:
            df = pd.DataFrame(endpoint_data)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            x = np.arange(len(df))
            width = 0.25
            
            ax.bar(x - width, df['mean'], width, label='Mean', color='skyblue')
            ax.bar(x, df['p95'], width, label='P95', color='orange')
            ax.bar(x + width, df['p99'], width, label='P99', color='red')
            
            ax.set_xlabel('Endpoint')
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('Performance by Endpoint')
            ax.set_xticks(x)
            ax.set_xticklabels(df['endpoint'], rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            plt.savefig(output_dir / 'endpoint_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()
            
    def generate_html_report(self, summary: Dict[str, Any], violations: List[Dict[str, Any]]):
        """HTML 보고서 생성"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #333;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #007bff;
        }}
        .metric-title {{
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .violation {{
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
        }}
        .violation.warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
        }}
        .violation.critical {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
        }}
        .chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .success {{
            color: #28a745;
        }}
        .warning {{
            color: #ffc107;
        }}
        .danger {{
            color: #dc3545;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Performance Test Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 Summary</h2>
        <div class="summary">
"""
        
        # 주요 메트릭 카드
        if 'http_req_duration' in summary['metrics']:
            duration = summary['metrics']['http_req_duration']
            html_content += f"""
            <div class="metric-card">
                <div class="metric-title">Average Response Time</div>
                <div class="metric-value">{duration['mean']:.2f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">95th Percentile</div>
                <div class="metric-value">{duration['p95']:.2f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">99th Percentile</div>
                <div class="metric-value">{duration['p99']:.2f} ms</div>
            </div>
"""
        
        if 'error_rate' in summary['metrics']:
            error_rate = summary['metrics']['error_rate']
            error_class = 'success' if error_rate['rate'] < 1 else 'warning' if error_rate['rate'] < 5 else 'danger'
            html_content += f"""
            <div class="metric-card">
                <div class="metric-title">Error Rate</div>
                <div class="metric-value {error_class}">{error_rate['rate']:.2f}%</div>
            </div>
"""
        
        if 'throughput' in summary['metrics']:
            throughput = summary['metrics']['throughput']
            html_content += f"""
            <div class="metric-card">
                <div class="metric-title">Throughput</div>
                <div class="metric-value">{throughput['requests_per_second']:.2f} req/s</div>
            </div>
"""
        
        html_content += """
        </div>
        
        <h2>⚠️ Threshold Violations</h2>
"""
        
        if violations:
            for violation in violations:
                html_content += f"""
        <div class="violation {violation['severity']}">
            <strong>{violation['metric']}</strong>: 
            Expected ≤ {violation['threshold']}, but got {violation['actual']:.2f}
        </div>
"""
        else:
            html_content += "<p class='success'>✅ All thresholds passed!</p>"
            
        # 엔드포인트별 성능
        html_content += """
        <h2>🔍 Endpoint Performance</h2>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>Requests</th>
                <th>Avg Response Time</th>
                <th>P95</th>
                <th>P99</th>
            </tr>
"""
        
        endpoint_metrics = {
            'product_list_duration': 'Product List',
            'product_detail_duration': 'Product Detail',
            'search_duration': 'Search',
            'order_creation_duration': 'Order Creation'
        }
        
        for metric_key, label in endpoint_metrics.items():
            if metric_key in summary['metrics']:
                data = summary['metrics'][metric_key]
                html_content += f"""
            <tr>
                <td>{label}</td>
                <td>{data['count']}</td>
                <td>{data['mean']:.2f} ms</td>
                <td>{data['p95']:.2f} ms</td>
                <td>{data['p99']:.2f} ms</td>
            </tr>
"""
        
        html_content += """
        </table>
        
        <h2>📈 Performance Charts</h2>
        <div class="chart">
            <h3>Response Time Distribution</h3>
            <img src="charts/response_time_distribution.png" alt="Response Time Distribution">
        </div>
        
        <div class="chart">
            <h3>Response Time Timeline</h3>
            <img src="charts/response_time_timeline.png" alt="Response Time Timeline">
        </div>
        
        <div class="chart">
            <h3>Endpoint Comparison</h3>
            <img src="charts/endpoint_comparison.png" alt="Endpoint Comparison">
        </div>
    </div>
</body>
</html>
"""
        
        with open('performance-report.html', 'w') as f:
            f.write(html_content)
            
    def generate_recommendations(self, summary: Dict[str, Any], violations: List[Dict[str, Any]]) -> List[str]:
        """성능 개선 권장사항 생성"""
        recommendations = []
        
        # 응답 시간 기반 권장사항
        if 'http_req_duration' in summary['metrics']:
            duration = summary['metrics']['http_req_duration']
            if duration['p95'] > 500:
                recommendations.append("🔸 P95 응답 시간이 500ms를 초과합니다. 다음을 검토하세요:")
                recommendations.append("  - 데이터베이스 쿼리 최적화")
                recommendations.append("  - 캐싱 전략 개선")
                recommendations.append("  - API 응답 페이로드 크기 축소")
                
            if duration['max'] > 5000:
                recommendations.append("🔸 일부 요청이 5초 이상 걸립니다. 타임아웃이 발생할 수 있습니다.")
                
        # 에러율 기반 권장사항
        if 'error_rate' in summary['metrics']:
            error_rate = summary['metrics']['error_rate']['rate']
            if error_rate > 5:
                recommendations.append("🔸 높은 에러율이 감지되었습니다:")
                recommendations.append("  - 서버 로그 확인")
                recommendations.append("  - 리소스 제한 확인 (메모리, CPU)")
                recommendations.append("  - 외부 서비스 상태 확인")
                
        # 엔드포인트별 권장사항
        slow_endpoints = []
        for metric in ['product_list_duration', 'search_duration']:
            if metric in summary['metrics']:
                if summary['metrics'][metric]['p95'] > 300:
                    slow_endpoints.append(metric.replace('_duration', ''))
                    
        if slow_endpoints:
            recommendations.append(f"🔸 다음 엔드포인트가 느립니다: {', '.join(slow_endpoints)}")
            recommendations.append("  - 인덱스 추가 검토")
            recommendations.append("  - N+1 쿼리 문제 확인")
            
        return recommendations


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze-performance.py <results.json>")
        sys.exit(1)
        
    results_file = sys.argv[1]
    
    print(f"Analyzing performance results from: {results_file}")
    
    analyzer = PerformanceAnalyzer(results_file)
    analyzer.load_results()
    analyzer.analyze()
    
    # 요약 생성
    summary = analyzer.generate_summary()
    print("\n=== Performance Summary ===")
    print(json.dumps(summary, indent=2))
    
    # 임계값 검사
    violations = analyzer.check_thresholds(summary)
    if violations:
        print("\n=== Threshold Violations ===")
        for violation in violations:
            print(f"❌ {violation['metric']}: {violation['actual']:.2f} (threshold: {violation['threshold']})")
    else:
        print("\n✅ All thresholds passed!")
        
    # 차트 생성
    charts_dir = Path('charts')
    analyzer.generate_charts(charts_dir)
    print(f"\nCharts saved to: {charts_dir}")
    
    # HTML 보고서 생성
    analyzer.generate_html_report(summary, violations)
    print("\nHTML report saved to: performance-report.html")
    
    # 권장사항 생성
    recommendations = analyzer.generate_recommendations(summary, violations)
    if recommendations:
        print("\n=== Recommendations ===")
        for rec in recommendations:
            print(rec)
            
    # 종료 코드 결정
    if any(v['severity'] == 'critical' for v in violations):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()