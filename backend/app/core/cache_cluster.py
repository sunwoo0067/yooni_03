"""
Redis Cluster 지원 캐시 매니저
"""
import json
import hashlib
import gzip
import base64
import logging
from typing import Any, Optional, List, Dict
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import RedisError, RedisClusterException

from .config import get_settings
from .cache import CacheManager

logger = logging.getLogger(__name__)


class ClusterCacheManager(CacheManager):
    """Redis Cluster를 지원하는 캐시 매니저"""
    
    def __init__(self):
        super().__init__()
        self._cluster_client: Optional[RedisCluster] = None
        self._cluster_nodes: List[Dict[str, Any]] = []
        
    async def connect(self):
        """Redis 연결 (단일 노드 또는 클러스터)"""
        if self._connected:
            return
            
        try:
            if self.settings.REDIS_CLUSTER_ENABLED and self.settings.REDIS_CLUSTER_NODES:
                # Redis Cluster 연결
                await self._connect_cluster()
            elif self.settings.REDIS_URL:
                # 단일 Redis 연결 (부모 클래스 메서드 사용)
                await super().connect()
            else:
                # Redis가 없으면 메모리 캐시 사용
                self._redis = None
                self._memory_cache = {}
                self._connected = True
                logger.info("Using in-memory cache (no Redis configured)")
                
        except Exception as e:
            logger.error(f"Cache connection failed: {e}")
            # 연결 실패 시 메모리 캐시로 폴백
            self._redis = None
            self._cluster_client = None
            self._memory_cache = {}
            self._connected = True
            
    async def _connect_cluster(self):
        """Redis Cluster 연결"""
        try:
            # 클러스터 노드 파싱
            self._cluster_nodes = []
            for node in self.settings.REDIS_CLUSTER_NODES:
                host, port = node.split(':')
                self._cluster_nodes.append({
                    "host": host,
                    "port": int(port)
                })
            
            # 클러스터 클라이언트 생성
            cluster_password = None
            if self.settings.REDIS_CLUSTER_PASSWORD:
                cluster_password = self.settings.REDIS_CLUSTER_PASSWORD.get_secret_value()
                
            self._cluster_client = await RedisCluster(
                startup_nodes=self._cluster_nodes,
                password=cluster_password,
                decode_responses=True,
                skip_full_coverage_check=True,  # 일부 노드 장애 시에도 작동
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            # 연결 테스트
            await self._cluster_client.ping()
            
            # 클러스터 정보 로깅
            info = await self._cluster_client.cluster_info()
            logger.info(f"Connected to Redis Cluster with {len(self._cluster_nodes)} nodes")
            logger.debug(f"Cluster state: {info.get('cluster_state', 'unknown')}")
            
            self._connected = True
            
        except RedisClusterException as e:
            logger.error(f"Redis Cluster connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis Cluster: {e}")
            raise
            
    async def disconnect(self):
        """Redis 연결 종료"""
        if self._cluster_client:
            await self._cluster_client.close()
            self._cluster_client = None
        
        # 부모 클래스의 disconnect도 호출
        await super().disconnect()
        
    async def get(self, key: str, compressed: bool = True) -> Optional[Any]:
        """캐시에서 값 가져오기 (클러스터 지원)"""
        if not self._connected:
            await self.connect()
            
        try:
            # 클러스터 클라이언트 사용
            if self._cluster_client:
                value = await self._cluster_client.get(key)
                if value:
                    self._stats["hits"] += 1
                    # 압축된 데이터 처리
                    if compressed and value.startswith("gzip:"):
                        compressed_data = base64.b64decode(value[5:])
                        decompressed_data = gzip.decompress(compressed_data)
                        return json.loads(decompressed_data.decode('utf-8'))
                    else:
                        return json.loads(value)
                else:
                    self._stats["misses"] += 1
                    return None
            else:
                # 단일 노드 또는 메모리 캐시 사용 (부모 클래스 메서드)
                return await super().get(key, compressed)
                
        except RedisClusterException as e:
            self._stats["errors"] += 1
            logger.error(f"Cluster cache get failed: {e}")
            # 클러스터 장애 시 None 반환
            return None
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache get failed: {e}")
            return None
            
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        compress: Optional[bool] = None,
        compress_threshold: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장 (클러스터 지원)"""
        if not self._connected:
            await self.connect()
            
        # 설정에서 기본값 가져오기
        if compress is None:
            compress = self.settings.CACHE_COMPRESSION_ENABLED
        if compress_threshold is None:
            compress_threshold = self.settings.CACHE_COMPRESSION_THRESHOLD
            
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            
            # 압축 여부 결정
            should_compress = compress and len(json_value) > compress_threshold
            
            # 클러스터 클라이언트 사용
            if self._cluster_client:
                if should_compress:
                    # 데이터 압축
                    compressed_data = gzip.compress(
                        json_value.encode('utf-8'), 
                        compresslevel=self.settings.CACHE_COMPRESSION_LEVEL
                    )
                    encoded_data = "gzip:" + base64.b64encode(compressed_data).decode('utf-8')
                    
                    # 압축 통계 업데이트
                    self._update_compression_stats(len(json_value), len(compressed_data))
                    
                    final_value = encoded_data
                else:
                    final_value = json_value
                
                if ttl:
                    await self._cluster_client.setex(key, ttl, final_value)
                else:
                    await self._cluster_client.set(key, final_value)
                    
                self._stats["sets"] += 1
                return True
            else:
                # 단일 노드 또는 메모리 캐시 사용 (부모 클래스 메서드)
                return await super().set(key, value, ttl, compress, compress_threshold)
                
        except RedisClusterException as e:
            self._stats["errors"] += 1
            logger.error(f"Cluster cache set failed: {e}")
            return False
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache set failed: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제 (클러스터 지원)"""
        if not self._connected:
            await self.connect()
            
        try:
            if self._cluster_client:
                await self._cluster_client.delete(key)
                self._stats["deletes"] += 1
                return True
            else:
                return await super().delete(key)
                
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False
            
    async def clear_pattern(self, pattern: str) -> int:
        """패턴과 일치하는 모든 키 삭제 (클러스터 지원)"""
        if not self._connected:
            await self.connect()
            
        deleted = 0
        try:
            if self._cluster_client:
                # 클러스터의 모든 마스터 노드에서 SCAN 실행
                # 주의: 클러스터에서는 각 노드별로 SCAN을 실행해야 함
                cursor = 0
                while True:
                    cursor, keys = await self._cluster_client.scan(
                        cursor, 
                        match=pattern, 
                        count=100
                    )
                    
                    for key in keys:
                        if await self._cluster_client.delete(key):
                            deleted += 1
                    
                    if cursor == 0:
                        break
            else:
                return await super().clear_pattern(pattern)
                
        except Exception as e:
            logger.error(f"Pattern delete failed: {e}")
            
        self._stats["deletes"] += deleted
        return deleted
        
    def _update_compression_stats(self, original_size: int, compressed_size: int):
        """압축 통계 업데이트"""
        self._compression_stats["compressed_count"] += 1
        self._compression_stats["total_original_size"] += original_size
        self._compression_stats["total_compressed_size"] += compressed_size
        
        if self._compression_stats["compressed_count"] > 0:
            self._compression_stats["avg_compression_ratio"] = (
                self._compression_stats["total_compressed_size"] / 
                self._compression_stats["total_original_size"]
            )
            
        compression_ratio = compressed_size / original_size
        if compression_ratio < 0.8:  # 20% 이상 압축된 경우
            logger.debug(
                f"Cache compression: {original_size} -> {compressed_size} bytes "
                f"({compression_ratio:.2%})"
            )
            
    async def get_cluster_info(self) -> Dict[str, Any]:
        """클러스터 정보 조회"""
        if not self._cluster_client:
            return {"cluster_enabled": False}
            
        try:
            info = await self._cluster_client.cluster_info()
            nodes = await self._cluster_client.cluster_nodes()
            
            return {
                "cluster_enabled": True,
                "cluster_state": info.get("cluster_state", "unknown"),
                "cluster_size": info.get("cluster_size", 0),
                "cluster_known_nodes": info.get("cluster_known_nodes", 0),
                "cluster_slots_assigned": info.get("cluster_slots_assigned", 0),
                "cluster_slots_ok": info.get("cluster_slots_ok", 0),
                "cluster_slots_pfail": info.get("cluster_slots_pfail", 0),
                "cluster_slots_fail": info.get("cluster_slots_fail", 0),
                "nodes": self._parse_cluster_nodes(nodes)
            }
        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {
                "cluster_enabled": True,
                "error": str(e)
            }
            
    def _parse_cluster_nodes(self, nodes_info: str) -> List[Dict[str, Any]]:
        """클러스터 노드 정보 파싱"""
        nodes = []
        for line in nodes_info.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 8:
                node_info = {
                    "id": parts[0],
                    "address": parts[1],
                    "flags": parts[2].split(','),
                    "master_id": parts[3] if parts[3] != '-' else None,
                    "ping_sent": parts[4],
                    "pong_recv": parts[5],
                    "config_epoch": parts[6],
                    "link_state": parts[7],
                    "slots": parts[8:] if len(parts) > 8 else []
                }
                nodes.append(node_info)
        return nodes


# 전역 클러스터 캐시 매니저 인스턴스
cluster_cache_manager = ClusterCacheManager()