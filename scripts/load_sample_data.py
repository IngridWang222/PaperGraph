"""加载示例数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, neo4j_conn
from app.models.mysql_models import PaperInfo, AuthorInfo, OrganizationInfo, PaperAuthorRelation
from app.repositories.neo4j_dao import GraphDAO
from loguru import logger

def load_sample_data():
    db = SessionLocal()
    
    try:
        logger.info("开始加载示例数据...")
        
        orgs = [
            {"org_id": "org_001", "name": "清华大学", "country": "中国", "abbreviation": "THU", "rank_score": 98.5, "paper_count": 0},
            {"org_id": "org_002", "name": "北京大学", "country": "中国", "abbreviation": "PKU", "rank_score": 97.8, "paper_count": 0},
            {"org_id": "org_003", "name": "Stanford University", "country": "美国", "abbreviation": "Stanford", "rank_score": 99.2, "paper_count": 0}
        ]
        
        for org_data in orgs:
            org = OrganizationInfo(**org_data)
            db.merge(org)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(orgs)} 个单位")
        
        authors = [
            {"author_id": "author_001", "name": "张三", "org_id": "org_001", "h_index": 25, "paper_count": 0, "orcid": "0000-0001-2345-6789", "email": "zhangsan@example.com"},
            {"author_id": "author_002", "name": "李四", "org_id": "org_002", "h_index": 18, "paper_count": 0, "orcid": "0000-0002-3456-7890", "email": "lisi@example.com"},
            {"author_id": "author_003", "name": "John Smith", "org_id": "org_003", "h_index": 42, "paper_count": 0, "orcid": "0000-0003-4567-8901", "email": "jsmith@stanford.edu"}
        ]
        
        for author_data in authors:
            author = AuthorInfo(**author_data)
            db.merge(author)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(authors)} 个作者")
        
        papers = [
            {"paper_id": "paper_001", "title": "Deep Learning for Knowledge Graph Construction", "abstract": "This paper presents a novel approach...", "year": 2023, "venue": "AAAI 2023", "doi": "10.1609/aaai.v37i1.12345", "keywords": "深度学习;知识图谱;神经网络", "url": "https://example.com/paper1", "citation_count": 25},
            {"paper_id": "paper_002", "title": "Graph Neural Networks for Scientific Publication Analysis", "abstract": "We propose a graph neural network framework...", "year": 2023, "venue": "KDD 2023", "doi": "10.1145/3580305.3599123", "keywords": "图神经网络;论文分析;科学计量", "url": "https://example.com/paper2", "citation_count": 18},
            {"paper_id": "paper_003", "title": "Knowledge Graph Embedding with Attention Mechanism", "abstract": "This work introduces an attention-based...", "year": 2022, "venue": "ACL 2022", "doi": "10.18653/v1/2022.acl-long.123", "keywords": "知识图谱嵌入;注意力机制;表示学习", "url": "https://example.com/paper3", "citation_count": 42}
        ]
        
        for paper_data in papers:
            paper = PaperInfo(**paper_data)
            db.merge(paper)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(papers)} 篇论文")
        
        relations = [
            {"paper_id": "paper_001", "author_id": "author_001", "author_order": 1, "is_corresponding": 1},
            {"paper_id": "paper_001", "author_id": "author_002", "author_order": 2, "is_corresponding": 0},
            {"paper_id": "paper_002", "author_id": "author_003", "author_order": 1, "is_corresponding": 1},
            {"paper_id": "paper_002", "author_id": "author_001", "author_order": 2, "is_corresponding": 0},
            {"paper_id": "paper_003", "author_id": "author_002", "author_order": 1, "is_corresponding": 1},
            {"paper_id": "paper_003", "author_id": "author_003", "author_order": 2, "is_corresponding": 0},
        ]
        
        for rel_data in relations:
            rel = PaperAuthorRelation(**rel_data)
            db.add(rel)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(relations)} 个论文-作者关系")
        
        logger.info("开始同步数据到 Neo4j...")
        sync_to_neo4j(db)
        
        logger.info("✓ 示例数据加载完成！")
        
    except Exception as e:
        logger.error(f"✗ 加载示例数据失败: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

def sync_to_neo4j(db):
    try:
        driver = neo4j_conn.get_driver()
        dao = GraphDAO(driver)
        
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("✓ 清空 Neo4j 现有数据")
            
            orgs = db.query(OrganizationInfo).all()
            org_node_map = {}
            for org in orgs:
                node_id = dao.create_organization_node({
                    "id": org.org_id,
                    "name": org.name,
                    "country": org.country,
                    "abbreviation": org.abbreviation,
                    "rank_score": float(org.rank_score) if org.rank_score else 0
                })
                org_node_map[org.org_id] = node_id
            logger.info(f"✓ 同步了 {len(orgs)} 个组织节点")
            
            authors = db.query(AuthorInfo).all()
            author_node_map = {}
            for author in authors:
                node_id = dao.create_author_node({
                    "id": author.author_id,
                    "name": author.name,
                    "h_index": author.h_index,
                    "orcid": author.orcid,
                    "email": author.email
                })
                author_node_map[author.author_id] = node_id
                
                if author.org_id and author.org_id in org_node_map:
                    dao.create_relationship(node_id, org_node_map[author.org_id], "AFFILIATED_WITH")
            logger.info(f"✓ 同步了 {len(authors)} 个作者节点")
            
            papers = db.query(PaperInfo).all()
            paper_node_map = {}
            for paper in papers:
                node_id = dao.create_paper_node({
                    "id": paper.paper_id,
                    "title": paper.title,
                    "year": paper.year,
                    "venue": paper.venue,
                    "doi": paper.doi,
                    "keywords": paper.keywords,
                    "citation_count": paper.citation_count
                })
                paper_node_map[paper.paper_id] = node_id
            logger.info(f"✓ 同步了 {len(papers)} 个论文节点")
            
            relations = db.query(PaperAuthorRelation).all()
            for rel in relations:
                if rel.author_id in author_node_map and rel.paper_id in paper_node_map:
                    dao.create_relationship(
                        author_node_map[rel.author_id],
                        paper_node_map[rel.paper_id],
                        "AUTHORED",
                        {"order": rel.author_order, "is_corresponding": rel.is_corresponding}
                    )
            logger.info(f"✓ 同步了 {len(relations)} 个作者-论文关系")
            
            session.close()
        
    except Exception as e:
        logger.error(f"✗ 同步到 Neo4j 失败: {e}")
        raise

def main():
    logger.info("=" * 60)
    logger.info("论文知识图谱系统 - 加载示例数据")
    logger.info("=" * 60)
    
    try:
        load_sample_data()
        logger.info("=" * 60)
        logger.info("示例数据加载成功！")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"加载失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

