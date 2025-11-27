"""数据库初始化脚本"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, neo4j_conn, redis_conn
from loguru import logger
from config import settings
# 导入模型以确保 SQLAlchemy 注册所有表
from app.models import mysql_models  # noqa: F401

def init_mysql():
    logger.info("开始初始化 MySQL 数据库...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ MySQL 表创建成功")
        
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✓ 已创建 {len(tables)} 个表: {', '.join(tables)}")
        return True
    except Exception as e:
        logger.error(f"✗ MySQL 初始化失败: {e}")
        return False

def init_neo4j():
    logger.info("开始初始化 Neo4j 数据库...")
    try:
        driver = neo4j_conn.connect()
        
        with driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✓ 创建约束: {constraint}")
                except Exception as e:
                    logger.warning(f"约束可能已存在: {e}")
            
            indexes = [
                "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
                "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
                "CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"✓ 创建索引: {index}")
                except Exception as e:
                    logger.warning(f"索引可能已存在: {e}")
        
        logger.info("✓ Neo4j 初始化成功")
        return True
    except Exception as e:
        logger.error(f"✗ Neo4j 初始化失败: {e}")
        return False
    finally:
        neo4j_conn.close()

def init_redis():
    logger.info("开始初始化 Redis...")
    import redis

    client = None
    try:
        # 只有当密码存在时才传递认证参数
        if settings.REDIS_PASSWORD:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
        else:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        if client.ping():
            logger.info("✓ Redis 连接成功")
        return True
    except redis.AuthenticationError as e:
        logger.error(f"✗ Redis 认证失败，请检查密码: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Redis 初始化失败: {e}")
        return False
    finally:
        if client:
            client.close()

def main():
    logger.info("=" * 60)
    logger.info("论文知识图谱系统 - 数据库初始化")
    logger.info("=" * 60)
    
    logger.info(f"MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    logger.info(f"Neo4j: {settings.NEO4J_URI}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
    logger.info("=" * 60)
    
    results = []
    results.append(("MySQL", init_mysql()))
    results.append(("Neo4j", init_neo4j()))
    results.append(("Redis", init_redis()))
    
    logger.info("=" * 60)
    logger.info("初始化结果:")
    for name, result in results:
        status = "✓ 成功" if result else "✗ 失败"
        logger.info(f"  {name}: {status}")
    
    logger.info("=" * 60)
    
    if all(r[1] for r in results):
        logger.info("所有数据库初始化成功！")
        return 0
    else:
        logger.error("部分数据库初始化失败，请检查配置和日志")
        return 1

if __name__ == "__main__":
    exit(main())

