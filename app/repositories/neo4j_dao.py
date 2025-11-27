"""
Neo4j 数据访问对象  —— 业务 ID 统一版
"""
from typing import List, Dict, Any, Tuple, Optional
from neo4j import Session
from loguru import logger


class GraphDAO:
    """图数据库访问类"""

    def __init__(self, driver):
        self.driver = driver

    # ---------- 根节点 + 边 ----------
    def query_root(self, params: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        limit = params.get("limit", 100)
        year_start = params.get("yearStart")
        year_end   = params.get("yearEnd")
        orgs       = params.get("orgs", [])          # ["Tsinghua", "PKU"]
        author     = params.get("author", "").strip()
        # ✅ 用业务 id 作为 source/target，不再用内部数字 id
        # 根图查询：从“单位 -> 作者 -> 论文”树形结构出发，
        # 先保证所有单位-作者关系存在，再可选挂上作者-论文关系
        cypher = """
        MATCH (o:Organization)<-[r2:AFFILIATED_WITH]-(a:Author)
        OPTIONAL MATCH (a)-[r:AUTHORED]->(b:Paper)
        WHERE
        ($year_start IS NULL OR b.year >= $year_start) AND
        ($year_end   IS NULL OR b.year <= $year_end)   AND
        ($author     = ""    OR  a.name CONTAINS $author) AND
        ($orgs       = []   OR o.name IN $orgs)

        RETURN
            a.id   AS a_id,
            b.id   AS b_id,
            o.id   AS o_id,
            a      AS a_node,
            b      AS b_node,
            o      AS o_node,
            r      AS rel,
            r2     AS rel2
        LIMIT $limit
        """
        nodes: List[Dict] = []
        edges: List[Dict] = []
        node_ids = set()
        logger.info("[参数] {}", params)
        logger.info("[Cypher 参数] yearStart={} yearEnd={} orgs={} author={}", year_start, year_end, orgs, author)
        with self.driver.session() as session:
            #result = session.run(cypher, limit=limit)
            result = session.run(cypher,
                     year_start=year_start,
                     year_end=year_end,
                     author=author,
                     orgs=orgs,
                     limit=limit)
            for rec in result:
                # 节点：根据返回记录依次加入 Author / Paper / Organization
                for label, node, node_id in (
                    ("Author", rec["a_node"], rec["a_id"]),
                    ("Paper", rec["b_node"], rec["b_id"]),
                    ("Organization", rec["o_node"], rec["o_id"]),
                ):
                    if node_id and node_id not in node_ids:
                        nodes.append({
                            "id": node_id,
                            "label": list(node.labels)[0],
                            "properties": dict(node),
                        })
                        node_ids.add(node_id)

                # 边：
                # 1）真实的作者-论文关系（AUTHORED）来自 r
                if rec["rel"]:
                    rel = rec["rel"]
                    edges.append({
                        "id": str(rel.id),
                        "source": rel.start_node["id"],
                        "target": rel.end_node["id"],
                        "type": rel.type,            # "AUTHORED"
                        "properties": dict(rel),
                    })

                # 2）单位-作者关系：为保证前端一定能拿到，
                #    无论 Neo4j 中是否有显式 AFFILIATED_WITH 边，这里都根据 a_id 和 o_id 补一条逻辑边
                a_id = rec["a_id"]
                o_id = rec["o_id"]
                if a_id and o_id:
                    edges.append({
                        "id": f"{a_id}->{o_id}:AFFILIATED_WITH",
                        "source": a_id,
                        "target": o_id,
                        "type": "AFFILIATED_WITH",
                        "properties": {},
                    })
        logger.info("[返回] 节点数={} 边数={}", len(nodes), len(edges))
        return nodes, edges

    # ---------- 子节点 ----------
    def query_children(self, node_id: str) -> Tuple[List[Dict], List[Dict]]:
        # ✅ 同样用业务 id 匹配，不再 int(node_id)
        cypher = """
        MATCH (n {id: $node_id})-[r]-(m)
        WHERE m.id IS NOT NULL
        RETURN
            n.id   AS center_id,
            m.id   AS m_id,
            m      AS m_node,
            r      AS rel
        """
        nodes: List[Dict] = []
        edges: List[Dict] = []
        node_ids = set()

        with self.driver.session() as session:
            # 子图查询只需要业务 ID，不需要额外筛选参数
            result = session.run(cypher, node_id=node_id)
            for rec in result:
                m_id = rec["m_id"]
                if m_id not in node_ids:
                    nodes.append({
                        "id": m_id,
                        "label": list(rec["m_node"].labels)[0],
                        "properties": dict(rec["m_node"]),
                    })
                    node_ids.add(m_id)

                edges.append({
                    "id": str(rec["rel"].id),
                    "source": rec["center_id"],  # ✅ 业务 id
                    "target": m_id,              # ✅ 业务 id
                    "type": rec["rel"].type,
                    "properties": dict(rec["rel"]),
                })

        return nodes, edges

    # ---------- 节点详情 ----------
    def query_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (n {id: $node_id})
        RETURN n, labels(n) AS labels
        LIMIT 1
        """
        with self.driver.session() as session:
            record = session.run(cypher, node_id=node_id).single()
            if not record:
                return None
            node = record["n"]
            return {
                "id": node_id,                      # ✅ 业务 id
                "label": record["labels"][0],
                "properties": dict(node),
            }

    # ---------- 其余方法不变 ----------
    def save_layout(self, layout_data: List[Dict[str, Any]]) -> bool:
        cypher = """
        MATCH (n {id: $node_id})
        SET n.layout_x = $x, n.layout_y = $y
        """
        with self.driver.session() as session:
            for item in layout_data:
                session.run(cypher, node_id=item["node_id"], x=item["x"], y=item["y"])
        return True
    
    def save_layout(self, layout_data: List[Dict[str, Any]]) -> bool:
        """
        保存节点布局位置
        
        Args:
            layout_data: 布局数据列表
            
        Returns:
            是否成功
        """
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        SET n.layout_x = $x, n.layout_y = $y
        """
        with self.driver.session() as session:
            try:
                for item in layout_data:
                    session.run(
                        query,
                        node_id=int(item["node_id"]),
                        x=item["x"],
                        y=item["y"]
                    )
                return True
            
            except Exception as e:
                logger.error(f"保存布局失败: {e}")
                return False
    
    def create_paper_node(self, paper_data: Dict[str, Any]) -> str:
        """创建论文节点"""
        query = """
        CREATE (b:Paper $properties)
        RETURN id(b) as node_id
        """
        with self.driver.session() as session:
            result = session.run(query, properties=paper_data)
            record = result.single()
            return str(record["node_id"]) if record else None
    
    def create_author_node(self, author_data: Dict[str, Any]) -> str:
        """创建作者节点"""
        query = """
        CREATE (a:Author $properties)
        RETURN id(a) as node_id
        """
        with self.driver.session() as session:
            result = session.run(query, properties=author_data)
            record = result.single()
            return str(record["node_id"]) if record else None
    
    def create_organization_node(self, org_data: Dict[str, Any]) -> str:
        """创建单位节点"""
        query = """
        CREATE (o:Organization $properties)
        RETURN id(o) as node_id
        """
        with self.driver.session() as session:
            result = session.run(query, properties=org_data)
            record = result.single()
            return str(record["node_id"]) if record else None
    
    def create_relationship(self, start_id: str, end_id: str, rel_type: str, properties: Dict = None) -> bool:
        """创建关系"""
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $start_id AND id(b) = $end_id
        CREATE (a)-[r:{rel_type} $properties]->(b)
        RETURN r
        """
        with self.driver.session() as session:
            try:
                session.run(
                    query,
                    start_id=int(start_id),
                    end_id=int(end_id),
                    properties=properties or {}
                )
                return True
            except Exception as e:
                logger.error(f"创建关系失败: {e}")
                return False

