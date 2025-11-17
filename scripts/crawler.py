import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, neo4j_conn
from app.models.mysql_models import PaperInfo, AuthorInfo, OrganizationInfo, PaperAuthorRelation, AuthorOrganizationRelation
from app.repositories.neo4j_dao import GraphDAO
from loguru import logger

def fetch_papers_by_keyword(keyword, per_page=20):
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"title.search:{keyword}",
        "per-page": per_page
    }
    return requests.get(url, params=params).json()["results"]

def clean_paper(raw):
    return {
        "paper_id": raw["id"].split("/")[-1],
        "title": raw.get("title", ""),
        "abstract": (raw.get("abstract_inverted_index") and 
                     " ".join(raw["abstract_inverted_index"].keys())) or "",
        "year": raw.get("publication_year", None),
        "venue": raw.get("host_venue", {}).get("display_name", ""),
        "doi": raw.get("doi", ""),
        "keywords": ";".join([kw["display_name"] for kw in raw.get("keywords", [])]),
        "url": raw.get("primary_location", {}).get("landing_page_url", ""),
        "citation_count": raw.get("cited_by_count", 0)
    }

def fetch_author(author_id):
    url = f"https://api.openalex.org/authors/{author_id}"
    return requests.get(url).json()

def clean_author(raw):
    author_id = raw["id"].split("/")[-1]
    org = raw.get("last_known_institution", {}) 
    return {
        "author_id": author_id,
        "name": raw.get("display_name", ""),
        "org_id": org.get("id", "").split("/")[-1] if org else None,
        "h_index": raw.get("h_index", 0),
        "paper_count": raw.get("works_count", 0),
        "orcid": raw.get("orcid", ""),
        "email": ""  # OpenAlex 没有邮箱字段，可用其他 API补充
    }

def fetch_org(org_id):
    url = f"https://api.openalex.org/institutions/{org_id}"
    return requests.get(url).json()

def clean_org(raw):
    return {
        "org_id": raw["id"].split("/")[-1],
        "name": raw.get("display_name", ""),
        "country": raw.get("country_code", ""),
        "abbreviation": raw.get("display_name_acronyms", [""])[0],
        "rank_score": raw.get("x_concepts", [{}])[0].get("score", 0),
        "paper_count": raw.get("works_count", 0)
    }

def extract_paper_author_relations(paper_raw):
    paper_id = paper_raw["id"].split("/")[-1]
    relations = []
    for idx, auth in enumerate(paper_raw.get("authorships", [])):
        author_id = auth["author"]["id"].split("/")[-1]
        is_corr = 1 if auth.get("is_corresponding") else 0
        relation = {
            "paper_id": paper_id,
            "author_id": author_id,
            "author_order": idx + 1,
            "is_corresponding": is_corr
        }
        relations.append(relation)
    return relations

def crawl(keyword):
    papers_raw = fetch_papers_by_keyword(keyword)
    papers = []
    authors = {}
    orgs = {}
    paper_author_rels = []
    author_org_rels = []

    for p in papers_raw:
        clean_p = clean_paper(p)
        papers.append(clean_p)
        for auth in p.get("authorships", []):
            author_id = auth["author"]["id"].split("/")[-1]
            if author_id not in authors:
                raw_author = fetch_author(author_id)
                authors[author_id] = clean_author(raw_author)
                org_id = authors[author_id]["org_id"]
                if org_id and org_id not in orgs:
                    raw_org = fetch_org(org_id)
                    orgs[org_id] = clean_org(raw_org)

        paper_author_rel = extract_paper_author_relations(p)
        paper_author_rels.extend(paper_author_rel)

    return papers, list(authors.values()), list(orgs.values()), paper_author_rels

def load_data(papers, authors, orgs, paper_authors):
    db = SessionLocal()
    
    try:
        logger.info("开始加载数据...")
        
        for org_data in orgs:
            org = OrganizationInfo(**org_data)
            db.merge(org)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(orgs)} 个单位")
        
        for author_data in authors:
            author = AuthorInfo(**author_data)
            db.merge(author)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(authors)} 个作者")
        
        for paper_data in papers:
            paper = PaperInfo(**paper_data)
            db.merge(paper)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(papers)} 篇论文")
        
        for rel_data in paper_authors:
            rel = PaperAuthorRelation(**rel_data)
            db.add(rel)
        
        db.commit()
        logger.info(f"✓ 创建了 {len(paper_authors)} 个论文-作者关系")
        
        logger.info("开始同步数据到 Neo4j...")
        sync_to_neo4j(db)
        
        logger.info("✓ 数据加载完成！")
        
    except Exception as e:
        logger.error(f"✗ 加载数据失败: {e}")
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
            
            paper_author_rels = db.query(PaperAuthorRelation).all()
            for rel in paper_author_rels:
                if rel.author_id in author_node_map and rel.paper_id in paper_node_map:
                    dao.create_relationship(
                        author_node_map[rel.author_id],
                        paper_node_map[rel.paper_id],
                        "AUTHORED",
                        {"order": rel.author_order, "is_corresponding": rel.is_corresponding}
                    )
            logger.info(f"✓ 同步了 {len(paper_author_rels)} 个作者-论文关系")

            session.close()
        
    except Exception as e:
        logger.error(f"✗ 同步到 Neo4j 失败: {e}")
        raise

def main(keyword):
    print(f"查找关键词：{keyword} ...\n")
    papers, authors, orgs, paper_author_rels = crawl(keyword)
    print(f"获取了 {len(papers)} 篇论文数据: \n")
    for p in papers:
        print("==============")
        print("Paper ID: ", p["paper_id"])
        print("Title: ", p["title"])
        print("Year: ", p["year"])
        print("DOI: ", p["doi"])
        print("Keywords: ", p["keywords"])
        print("URL: ", p["url"])
        print("Citation count: ", p["citation_count"])
        print("==============\n")
        logger.info("=" * 60)
    logger.info("论文知识图谱系统 - 加载数据")
    logger.info("=" * 60)
    
    try:
        load_data(papers, authors, orgs, paper_author_rels)
        logger.info("=" * 60)
        logger.info("数据加载成功！")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"加载失败: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python crawler.py <keyword>")
        sys.exit(1)
    keyword = sys.argv[1]
    main(keyword)