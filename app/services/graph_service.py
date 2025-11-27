"""图谱业务逻辑"""
from typing import List, Dict, Any
from app.repositories.neo4j_dao import GraphDAO
from redis import Redis
import json
from loguru import logger

class GraphService:
    def __init__(self, graph_dao: GraphDAO, cache: Redis = None):
        self.dao = graph_dao
        self.cache = cache
    
    def get_root(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取根图谱数据。

        说明：
        - 为了开发调试和保证前后端数据实时一致，这里暂时关闭 Redis 缓存，
          每次都直接从 Neo4j 读取最新结果。
        - 如需开启缓存，可恢复原有 self.cache 逻辑。
        """
        nodes, edges = self.dao.query_root(params)
        result = {"nodes": nodes, "edges": edges}
        return result
    
    def get_children(self, node_id: str) -> Dict[str, Any]:
        cache_key = f"graph:children:{node_id}"
        
        if self.cache:
            try:
                cached = self.cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"缓存读取失败: {e}")
        
        nodes, edges = self.dao.query_children(node_id)
        result = {"nodes": nodes, "edges": edges}
        
        if self.cache:
            try:
                self.cache.setex(cache_key, 1800, json.dumps(result))
            except Exception as e:
                logger.warning(f"缓存写入失败: {e}")
        
        return result
    
    def get_node_info(self, node_id: str) -> Dict[str, Any]:
        cache_key = f"graph:node:{node_id}"
        
        if self.cache:
            try:
                cached = self.cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"缓存读取失败: {e}")
        
        node_info = self.dao.query_node_info(node_id)
        
        if node_info and self.cache:
            try:
                self.cache.setex(cache_key, 3600, json.dumps(node_info))
            except Exception as e:
                logger.warning(f"缓存写入失败: {e}")
        
        return node_info
    
    def persist_layout(self, layout_data: List[Dict[str, Any]]) -> bool:
        try:
            success = self.dao.save_layout(layout_data)
            
            if success and self.cache:
                try:
                    keys = self.cache.keys("graph:root:*")
                    if keys:
                        self.cache.delete(*keys)
                except Exception as e:
                    logger.warning(f"清除缓存失败: {e}")
            
            return success
        except Exception as e:
            logger.error(f"保存布局失败: {e}")
            return False

