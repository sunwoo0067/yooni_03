"""
Performance benchmark dashboard API.
성능 벤치마크 대시보드 API.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import json

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse

from app.core.logging_utils import get_logger
from app.api.v1.dependencies.auth import get_current_admin_user
from tests.benchmarks.benchmark_framework import BenchmarkSuite


router = APIRouter()
logger = get_logger("BenchmarkDashboard")


# 벤치마크 결과 저장소 (실제로는 DB 사용)
BENCHMARK_RESULTS_PATH = Path("benchmark_results")
BENCHMARK_RESULTS_PATH.mkdir(exist_ok=True)


@router.post("/run")
async def run_benchmarks(
    benchmark_type: str = Query(..., enum=["product", "order", "ai", "all"]),
    iterations: int = Query(100, ge=10, le=1000),
    admin_user = Depends(get_current_admin_user)
):
    """
    벤치마크 실행.
    
    - **benchmark_type**: 실행할 벤치마크 유형
    - **iterations**: 반복 횟수
    """
    try:
        from tests.benchmarks.test_service_benchmarks import TestServiceBenchmarks
        
        # 벤치마크 인스턴스 생성
        test_instance = TestServiceBenchmarks()
        suite = BenchmarkSuite(f"{benchmark_type}_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 벤치마크 실행
        if benchmark_type == "product" or benchmark_type == "all":
            # 상품 서비스 벤치마크
            await test_instance.test_product_service_benchmarks(
                async_session=None,  # 실제 세션 주입
                cache_service=None,  # 실제 캐시 서비스 주입
                benchmark_suite=suite,
                test_data_factory=None  # 실제 팩토리 주입
            )
            
        if benchmark_type == "order" or benchmark_type == "all":
            # 주문 처리 벤치마크
            pass
            
        if benchmark_type == "ai" or benchmark_type == "all":
            # AI 서비스 벤치마크
            pass
            
        # 결과 저장
        result_path = BENCHMARK_RESULTS_PATH / f"{suite.name}.json"
        report = suite.generate_report(result_path)
        
        return {
            "status": "completed",
            "suite_name": suite.name,
            "result_path": str(result_path),
            "summary": json.loads(report)
        }
        
    except Exception as e:
        logger.error(f"Benchmark execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_benchmark_results(
    limit: int = Query(10, ge=1, le=100),
    benchmark_type: Optional[str] = None,
    admin_user = Depends(get_current_admin_user)
):
    """저장된 벤치마크 결과 조회"""
    try:
        results = []
        
        # 결과 파일들 읽기
        for result_file in sorted(
            BENCHMARK_RESULTS_PATH.glob("*.json"), 
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            with open(result_file) as f:
                data = json.load(f)
                
            # 필터링
            if benchmark_type and benchmark_type not in result_file.stem:
                continue
                
            results.append({
                "filename": result_file.name,
                "timestamp": data.get("timestamp"),
                "suite": data.get("suite"),
                "benchmarks": list(data.get("benchmarks", {}).keys()),
                "summary": _summarize_results(data)
            })
            
        return {
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get benchmark results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{filename}")
async def get_benchmark_detail(
    filename: str,
    admin_user = Depends(get_current_admin_user)
):
    """특정 벤치마크 결과 상세 조회"""
    try:
        result_path = BENCHMARK_RESULTS_PATH / filename
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Result not found")
            
        with open(result_path) as f:
            data = json.load(f)
            
        return data
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result not found")
    except Exception as e:
        logger.error(f"Failed to get benchmark detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_benchmarks(
    baseline: str = Query(..., description="Baseline result filename"),
    current: str = Query(..., description="Current result filename"),
    admin_user = Depends(get_current_admin_user)
):
    """두 벤치마크 결과 비교"""
    try:
        # 결과 파일 읽기
        baseline_path = BENCHMARK_RESULTS_PATH / baseline
        current_path = BENCHMARK_RESULTS_PATH / current
        
        if not baseline_path.exists() or not current_path.exists():
            raise HTTPException(status_code=404, detail="Result not found")
            
        with open(baseline_path) as f:
            baseline_data = json.load(f)
            
        with open(current_path) as f:
            current_data = json.load(f)
            
        # 비교 결과 생성
        comparison = _compare_results(baseline_data, current_data)
        
        return {
            "baseline": {
                "filename": baseline,
                "timestamp": baseline_data.get("timestamp"),
                "suite": baseline_data.get("suite")
            },
            "current": {
                "filename": current,
                "timestamp": current_data.get("timestamp"),
                "suite": current_data.get("suite")
            },
            "comparison": comparison
        }
        
    except Exception as e:
        logger.error(f"Failed to compare benchmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def benchmark_dashboard(
    admin_user = Depends(get_current_admin_user)
):
    """벤치마크 대시보드 HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Benchmark Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .metric {
                display: inline-block;
                margin: 10px;
                padding: 15px;
                background: #f0f0f0;
                border-radius: 4px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            .metric-label {
                font-size: 14px;
                color: #666;
            }
            .chart-container {
                position: relative;
                height: 400px;
                margin: 20px 0;
            }
            button {
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background: #0056b3;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f8f9fa;
                font-weight: bold;
            }
            .improvement {
                color: #28a745;
            }
            .regression {
                color: #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Performance Benchmark Dashboard</h1>
            
            <div class="card">
                <h2>Run New Benchmark</h2>
                <button onclick="runBenchmark('product')">Run Product Benchmark</button>
                <button onclick="runBenchmark('order')">Run Order Benchmark</button>
                <button onclick="runBenchmark('ai')">Run AI Benchmark</button>
                <button onclick="runBenchmark('all')">Run All Benchmarks</button>
            </div>
            
            <div class="card">
                <h2>Latest Results</h2>
                <div id="latest-results"></div>
            </div>
            
            <div class="card">
                <h2>Performance Trends</h2>
                <div class="chart-container">
                    <canvas id="trend-chart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2>Comparison Results</h2>
                <div id="comparison-results"></div>
            </div>
        </div>
        
        <script>
            async function loadResults() {
                const response = await fetch('/api/v1/benchmarks/results?limit=10');
                const data = await response.json();
                
                const container = document.getElementById('latest-results');
                container.innerHTML = '<table>' +
                    '<tr><th>Timestamp</th><th>Suite</th><th>Benchmarks</th><th>Avg Response Time</th></tr>' +
                    data.results.map(r => `
                        <tr>
                            <td>${new Date(r.timestamp).toLocaleString()}</td>
                            <td>${r.suite}</td>
                            <td>${r.benchmarks.join(', ')}</td>
                            <td>${r.summary.avg_response_time?.toFixed(2) || 'N/A'} ms</td>
                        </tr>
                    `).join('') +
                    '</table>';
            }
            
            async function runBenchmark(type) {
                const button = event.target;
                button.disabled = true;
                button.textContent = 'Running...';
                
                try {
                    const response = await fetch(`/api/v1/benchmarks/run?benchmark_type=${type}`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    
                    alert(`Benchmark completed: ${result.suite_name}`);
                    loadResults();
                } catch (error) {
                    alert(`Error: ${error.message}`);
                } finally {
                    button.disabled = false;
                    button.textContent = button.textContent.replace('Running...', 'Run');
                }
            }
            
            // 초기 로드
            loadResults();
            
            // 차트 예제
            const ctx = document.getElementById('trend-chart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['1 hour ago', '45 min', '30 min', '15 min', 'Now'],
                    datasets: [{
                        label: 'Response Time (ms)',
                        data: [45, 42, 48, 40, 38],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }, {
                        label: 'Throughput (ops/sec)',
                        data: [850, 870, 820, 890, 920],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: {
                                drawOnChartArea: false,
                            },
                        },
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


# 헬퍼 함수들
def _summarize_results(data: Dict[str, Any]) -> Dict[str, Any]:
    """벤치마크 결과 요약"""
    benchmarks = data.get("benchmarks", {})
    
    if not benchmarks:
        return {}
        
    # 평균 응답 시간 계산
    response_times = []
    throughputs = []
    
    for name, result in benchmarks.items():
        if "avg_time_ms" in result:
            response_times.append(result["avg_time_ms"])
        if "throughput_ops" in result:
            throughputs.append(result["throughput_ops"])
            
    return {
        "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
        "avg_throughput": sum(throughputs) / len(throughputs) if throughputs else 0,
        "total_benchmarks": len(benchmarks)
    }


def _compare_results(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """두 결과 비교"""
    comparison = {}
    
    baseline_benchmarks = baseline.get("benchmarks", {})
    current_benchmarks = current.get("benchmarks", {})
    
    for name in baseline_benchmarks:
        if name in current_benchmarks:
            baseline_time = baseline_benchmarks[name].get("avg_time_ms", 0)
            current_time = current_benchmarks[name].get("avg_time_ms", 0)
            
            if baseline_time > 0:
                improvement = ((baseline_time - current_time) / baseline_time) * 100
                speedup = baseline_time / current_time if current_time > 0 else 0
                
                comparison[name] = {
                    "baseline_ms": baseline_time,
                    "current_ms": current_time,
                    "improvement_percent": improvement,
                    "speedup": speedup,
                    "status": "improved" if improvement > 0 else "regressed"
                }
                
    return comparison