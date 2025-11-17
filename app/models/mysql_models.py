"""
MySQL 数据模型
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON, BigInteger, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from app.database import Base


class PaperInfo(Base):
    """论文信息表"""
    __tablename__ = "paper_info"
    
    paper_id = Column(String(64), primary_key=True, comment="论文唯一编号")
    title = Column(String(512), nullable=False, comment="论文题目")
    abstract = Column(Text, comment="摘要内容")
    year = Column(Integer, comment="发表年份")
    venue = Column(String(128), comment="发表会议或期刊名称")
    doi = Column(String(128), comment="数字对象标识符")
    keywords = Column(String(512), comment="关键词（以分号分隔）")
    url = Column(String(256), comment="原文链接")
    citation_count = Column(Integer, default=0, comment="被引次数")
    created_at = Column(DateTime, server_default=func.now(), comment="记录创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="最近更新时间")


class AuthorInfo(Base):
    """作者信息表"""
    __tablename__ = "author_info"
    
    author_id = Column(String(64), primary_key=True, comment="作者唯一编号")
    name = Column(String(128), nullable=False, comment="作者姓名")
    org_id = Column(String(64), ForeignKey("organization_info.org_id"), comment="所属单位编号")
    h_index = Column(Integer, default=0, comment="H指数")
    paper_count = Column(Integer, default=0, comment="发表论文数")
    orcid = Column(String(64), comment="作者ORCID号")
    email = Column(String(128), comment="邮箱")
    created_at = Column(DateTime, server_default=func.now(), comment="记录创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="最近更新时间")


class OrganizationInfo(Base):
    """单位信息表"""
    __tablename__ = "organization_info"
    
    org_id = Column(String(64), primary_key=True, comment="单位唯一编号")
    name = Column(String(256), nullable=False, comment="单位名称")
    country = Column(String(64), comment="所在国家/地区")
    abbreviation = Column(String(64), comment="单位简称")
    rank_score = Column(DECIMAL(10, 4), comment="单位综合影响力评分")
    paper_count = Column(Integer, default=0, comment="单位发表论文数")
    created_at = Column(DateTime, server_default=func.now(), comment="记录创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="最近更新时间")


class PaperAuthorRelation(Base):
    """论文-作者关联表"""
    __tablename__ = "paper_author_relation"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    paper_id = Column(String(64), ForeignKey("paper_info.paper_id"), nullable=False, comment="论文编号")
    author_id = Column(String(64), ForeignKey("author_info.author_id"), nullable=False, comment="作者编号")
    author_order = Column(Integer, comment="作者顺序（从1开始）")
    is_corresponding = Column(Integer, default=0, comment="是否通讯作者（1=是，0=否）")


class AuthorOrganizationRelation(Base):
    """作者-机构关联表"""
    __tablename__ = "author_organization_relation"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    author_id = Column(String(64), ForeignKey("author_info.author_id"), nullable=False, comment="作者编号")
    org_id = Column(String(64), ForeignKey("organization_info.org_id"), nullable=False, comment="机构编号")


class PaperCitationRelation(Base):
    """论文引用关系表"""
    __tablename__ = "paper_citation_relation"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    citing_paper_id = Column(String(64), ForeignKey("paper_info.paper_id"), nullable=False, comment="引用论文ID")
    cited_paper_id = Column(String(64), ForeignKey("paper_info.paper_id"), nullable=False, comment="被引论文ID")
    weight = Column(Float, comment="相关性权重")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class GraphNodeMapping(Base):
    """图谱节点映射表"""
    __tablename__ = "graph_node_mapping"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    node_id = Column(String(64), nullable=False, unique=True, comment="Neo4j节点ID")
    entity_type = Column(String(32), nullable=False, comment="实体类型（Paper/Author/Organization）")
    entity_id = Column(String(64), nullable=False, comment="对应MySQL实体表主键")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class StatisticsData(Base):
    """统计结果表"""
    __tablename__ = "statistics_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    metric = Column(String(64), nullable=False, comment="指标名称")
    dims_json = Column(JSON, comment="聚合维度")
    value = Column(DECIMAL(20, 6), comment="聚合值")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ExportLog(Base):
    """导出日志表"""
    __tablename__ = "export_log"
    
    job_id = Column(String(64), primary_key=True, comment="任务编号")
    user_id = Column(BigInteger, comment="用户ID")
    params = Column(JSON, comment="导出参数")
    status = Column(String(16), default="pending", comment="任务状态（pending/running/done/failed）")
    file_path = Column(String(256), comment="文件存储路径")
    error_msg = Column(Text, comment="错误信息")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

