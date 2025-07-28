# Redis Cluster 설정 가이드

## 개요

이 문서는 Yooni Dropshipping System에서 Redis Cluster를 설정하고 사용하는 방법을 설명합니다.

## Redis Cluster 설정

### 1. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```env
# Redis Cluster 활성화
REDIS_CLUSTER_ENABLED=true

# 클러스터 노드 목록 (최소 3개의 마스터 노드 필요)
REDIS_CLUSTER_NODES=["redis-node1:7000","redis-node2:7001","redis-node3:7002"]

# 클러스터 비밀번호 (선택사항)
REDIS_CLUSTER_PASSWORD=your-cluster-password
```

### 2. Docker Compose를 사용한 로컬 클러스터 설정

개발 환경에서 Redis Cluster를 테스트하려면:

```yaml
# docker-compose.redis-cluster.yml
version: '3.8'

services:
  redis-node-1:
    image: redis:7-alpine
    command: redis-server --port 7000 --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7000:7000"
    volumes:
      - redis-node-1-data:/data

  redis-node-2:
    image: redis:7-alpine
    command: redis-server --port 7001 --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7001:7001"
    volumes:
      - redis-node-2-data:/data

  redis-node-3:
    image: redis:7-alpine
    command: redis-server --port 7002 --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7002:7002"
    volumes:
      - redis-node-3-data:/data

  redis-cluster-init:
    image: redis:7-alpine
    depends_on:
      - redis-node-1
      - redis-node-2
      - redis-node-3
    command: >
      sh -c "
        sleep 5;
        redis-cli --cluster create
          redis-node-1:7000
          redis-node-2:7001
          redis-node-3:7002
          --cluster-replicas 0
          --cluster-yes
      "

volumes:
  redis-node-1-data:
  redis-node-2-data:
  redis-node-3-data:
```

### 3. 클러스터 시작

```bash
# Redis Cluster 시작
docker-compose -f docker-compose.redis-cluster.yml up -d

# 클러스터 상태 확인
docker exec -it redis-node-1 redis-cli -p 7000 cluster info
```

## 기능 및 장점

### 1. 자동 샤딩
- 데이터가 여러 노드에 자동으로 분산됨
- 16384개의 해시 슬롯을 사용하여 키 분배

### 2. 고가용성
- 마스터 노드 장애 시 자동 페일오버
- 일부 노드 장애 시에도 서비스 지속

### 3. 선형 확장성
- 노드 추가/제거로 용량 및 처리량 증가
- 온라인 리샤딩 지원

### 4. 압축 지원
- 1KB 이상의 데이터는 자동으로 gzip 압축
- 네트워크 대역폭 및 메모리 사용량 감소

## 모니터링

### 클러스터 상태 확인

```bash
# API를 통한 클러스터 정보 조회
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/monitoring/cache/cluster/info
```

응답 예시:
```json
{
  "cluster_enabled": true,
  "cluster_state": "ok",
  "cluster_size": 3,
  "cluster_known_nodes": 3,
  "cluster_slots_assigned": 16384,
  "cluster_slots_ok": 16384,
  "nodes": [
    {
      "id": "node-id-1",
      "address": "192.168.1.1:7000",
      "flags": ["master"],
      "link_state": "connected",
      "slots": ["0-5460"]
    }
  ]
}
```

### 캐시 통계 확인

```bash
# 압축 통계 포함 캐시 정보
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/monitoring/cache/stats
```

## 주의사항

1. **최소 요구사항**
   - 최소 3개의 마스터 노드 필요
   - 프로덕션에서는 각 마스터당 1개 이상의 레플리카 권장

2. **네트워크 고려사항**
   - 클러스터 노드 간 낮은 지연시간 필요
   - 방화벽에서 클러스터 포트 개방 필요 (기본: 노드포트 + 10000)

3. **키 설계**
   - 해시 태그 사용으로 관련 키를 같은 노드에 저장 가능
   - 예: `{user:123}:profile`, `{user:123}:orders`

4. **트랜잭션 제한**
   - 다중 키 작업은 같은 해시 슬롯에 있는 키만 가능
   - MGET, MSET 등은 같은 노드의 키만 처리 가능

## 문제 해결

### 클러스터 연결 실패
```bash
# 노드 상태 확인
docker logs redis-node-1

# 클러스터 노드 확인
docker exec -it redis-node-1 redis-cli -p 7000 cluster nodes
```

### 성능 최적화
1. 적절한 maxmemory 설정
2. 키 만료 정책 구성
3. 클러스터 노드 간 네트워크 최적화

## 프로덕션 배포

프로덕션 환경에서는 다음을 고려하세요:

1. **AWS ElastiCache for Redis (Cluster Mode)**
   ```env
   REDIS_CLUSTER_ENABLED=true
   REDIS_CLUSTER_NODES=["cluster.xxxxx.cache.amazonaws.com:6379"]
   ```

2. **Google Cloud Memorystore**
   ```env
   REDIS_CLUSTER_ENABLED=true
   REDIS_CLUSTER_NODES=["10.0.0.1:6379","10.0.0.2:6379","10.0.0.3:6379"]
   ```

3. **자체 관리 클러스터**
   - Redis Sentinel 또는 Redis Cluster 사용
   - 모니터링 및 백업 전략 수립
   - 자동 페일오버 구성