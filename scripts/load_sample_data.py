"""加载示例数据"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, neo4j_conn
from app.models.mysql_models import PaperInfo, AuthorInfo, OrganizationInfo, PaperAuthorRelation
from app.repositories.neo4j_dao import GraphDAO
from loguru import logger

def load_sample_data():
    db = SessionLocal()
    
    try:
        logger.info("开始加载示例数据...")

        # 先清空 MySQL 中旧的业务数据，避免多次执行脚本时数据叠加
        logger.info("清空 MySQL 中旧的单位 / 作者 / 论文 / 关系数据...")
        # 先删关联表，再删主表，避免外键约束问题
        db.query(PaperAuthorRelation).delete(synchronize_session=False)
        db.query(PaperInfo).delete(synchronize_session=False)
        db.query(AuthorInfo).delete(synchronize_session=False)
        db.query(OrganizationInfo).delete(synchronize_session=False)
        db.commit()
        logger.info("✓ 已清空 MySQL 旧数据")

        # ==== 构造 5 个单位 ====
        org_templates = [
            ("清华大学", "中国", "THU", 98.5),
            ("北京大学", "中国", "PKU", 97.8),
            ("上海交通大学", "中国", "SJTU", 96.1),
            ("复旦大学", "中国", "FDU", 95.4),
            ("浙江大学", "中国", "ZJU", 95.0),
        ]

        orgs = []
        for idx, (name, country, abbr, score) in enumerate(org_templates, start=1):
            orgs.append(
                {
                    "org_id": f"org_{idx:03d}",
                    "name": name,
                    "country": country,
                    "abbreviation": abbr,
                    "rank_score": score,
                    "paper_count": 0,
                }
            )
        
        for org_data in orgs:
            org = OrganizationInfo(**org_data)
            db.merge(org)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(orgs)} 个单位")

        # ==== 构造更多作者，分布在不同单位 ====
        cn_family_names = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
        cn_given_names = ["伟", "芳", "娜", "敏", "静", "磊", "洋", "艳", "勇", "军"]
        en_first_names = ["John", "Mary", "Alice", "Bob", "David", "Emily", "Michael", "Sarah"]
        en_last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller"]

        authors = []
        org_ids = [o["org_id"] for o in orgs]

        # 先为每个单位准备作者列表，形成“单位 -> 10 个作者”的树干
        org_to_authors: dict[str, list[str]] = {org_id: [] for org_id in org_ids}

        author_index = 1
        for org_id in org_ids:
            for _ in range(10):  # 每个单位 10 个作者
                # 中英文名字混合
                if author_index % 2 == 0:
                    name = random.choice(cn_family_names) + random.choice(cn_given_names)
                else:
                    name = f"{random.choice(en_first_names)} {random.choice(en_last_names)}"

                h_index = random.randint(5, 60)
                paper_count = 0

                author_id = f"author_{author_index:03d}"
                authors.append(
                    {
                        "author_id": author_id,
                        "name": name,
                        "org_id": org_id,
                        "h_index": h_index,
                        "paper_count": paper_count,
                        "orcid": f"0000-0000-{author_index:04d}-{random.randint(1000, 9999)}",
                        "email": f"author{author_index:03d}@example.com",
                    }
                )
                org_to_authors[org_id].append(author_id)
                author_index += 1

        for author_data in authors:
            author = AuthorInfo(**author_data)
            db.merge(author)

        db.commit()
        logger.info(f"✓ 创建了 {len(authors)} 个作者")
        
        # 生成 5 * 10 * 10 = 500 篇示例论文：
        # 每个单位有 10 个作者，每个作者有 10 篇论文，形成严格的“单位 -> 作者 -> 论文”树
        papers = []
        num_papers = 0
        venues = ["AAAI", "KDD", "ACL", "ICML", "NeurIPS", "WWW", "CIKM"]
        base_year = 2018

        paper_index = 1
        paper_main_org: dict[str, str] = {}

        # 严格保证：每个作者恰好 10 篇论文
        for org in orgs:
            org_id = org["org_id"]
            org_abbr = org["abbreviation"]
            for author_id in org_to_authors[org_id]:
                for _ in range(10):  # 每个作者 10 篇论文
                    paper_id = f"paper_{paper_index:03d}"
                    year = base_year + (paper_index % 8)  # 在最近几年内循环
                    venue = f"{random.choice(venues)} {year}"
                    citation_count = random.randint(0, 200)

                    papers.append(
                        {
                            "paper_id": paper_id,
                            "title": f"[{org_abbr}] Sample Paper {paper_index} on Knowledge Graphs and AI",
                            "abstract": (
                                f"This is a synthetic sample paper #{paper_index} generated for testing the "
                                f"knowledge graph system, focusing on topics like knowledge graphs, "
                                f"graph neural networks and scientific publication analysis."
                            ),
                            "year": year,
                            "venue": venue,
                            "doi": f"10.1234/example.{paper_index:04d}",
                            "keywords": "知识图谱;图神经网络;科学计量;表示学习",
                            "url": f"https://example.com/sample_paper_{paper_index}",
                            "citation_count": citation_count,
                        }
                    )
                    paper_main_org[paper_id] = org_id
                    paper_index += 1
                    num_papers += 1

        for paper_data in papers:
            paper = PaperInfo(**paper_data)
            db.merge(paper)

        db.commit()
        logger.info(f"✓ 创建了 {len(papers)} 篇论文")

        # 为每篇论文分配作者：每篇论文唯一对应一个作者（形成严格的树而非网状）
        relations = []

        # 建立 author_id 到 org_id 的映射，方便校验
        author_org_map = {a["author_id"]: a["org_id"] for a in authors}

        paper_idx = 0
        for org in orgs:
            org_id = org["org_id"]
            for author_id in org_to_authors[org_id]:
                # 当前作者的 10 篇论文在 papers 列表中的起止范围
                for _ in range(10):
                    paper = papers[paper_idx]
                    paper_id = paper["paper_id"]
                    relations.append(
                        {
                            "paper_id": paper_id,
                            "author_id": author_id,
                            "author_order": 1,
                            "is_corresponding": 1,
                        }
                    )
                    paper_idx += 1

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

