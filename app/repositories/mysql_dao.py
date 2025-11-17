"""MySQL 数据访问对象"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.mysql_models import (
    PaperInfo, AuthorInfo, OrganizationInfo,
    PaperAuthorRelation, AuthorOrganizationRelation, PaperCitationRelation,
    GraphNodeMapping, StatisticsData, ExportLog
)
from loguru import logger

class StatisticsDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def query_aggregated(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        metric = query_params.get("metric")
        start_year = query_params.get("start_year")
        end_year = query_params.get("end_year")
        limit = query_params.get("limit", 100)
        
        try:
            if metric == "paper_count_by_year":
                query = self.db.query(
                    PaperInfo.year,
                    func.count(PaperInfo.paper_id).label("count")
                ).group_by(PaperInfo.year)
                
                if start_year:
                    query = query.filter(PaperInfo.year >= start_year)
                if end_year:
                    query = query.filter(PaperInfo.year <= end_year)
                
                query = query.order_by(PaperInfo.year).limit(limit)
                results = query.all()
                return [{"label": str(r.year), "value": r.count} for r in results]
            
            elif metric == "top_authors":
                query = self.db.query(
                    AuthorInfo.author_id,
                    AuthorInfo.name,
                    AuthorInfo.paper_count,
                    AuthorInfo.h_index
                ).order_by(AuthorInfo.paper_count.desc()).limit(limit)
                
                results = query.all()
                return [{"label": r.name, "value": r.paper_count, "extra": {"h_index": r.h_index, "author_id": r.author_id}} for r in results]
            
            elif metric == "top_organizations":
                query = self.db.query(
                    OrganizationInfo.org_id,
                    OrganizationInfo.name,
                    OrganizationInfo.paper_count,
                    OrganizationInfo.rank_score
                ).order_by(OrganizationInfo.paper_count.desc()).limit(limit)
                
                results = query.all()
                return [{"label": r.name, "value": r.paper_count, "extra": {"rank_score": float(r.rank_score) if r.rank_score else 0, "org_id": r.org_id}} for r in results]
            
            else:
                query = self.db.query(StatisticsData).filter(StatisticsData.metric == metric).limit(limit)
                results = query.all()
                return [{"label": r.dims_json.get("label", ""), "value": float(r.value) if r.value else 0, "extra": r.dims_json} for r in results]
        
        except Exception as e:
            logger.error(f"查询统计数据失败: {e}")
            raise

class ExportDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def insert_job(self, job_id: str, user_id: Optional[int], params: Dict[str, Any]) -> bool:
        try:
            job = ExportLog(job_id=job_id, user_id=user_id, params=params, status="pending")
            self.db.add(job)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"插入导出任务失败: {e}")
            self.db.rollback()
            return False
    
    def get_job(self, job_id: str) -> Optional[ExportLog]:
        return self.db.query(ExportLog).filter(ExportLog.job_id == job_id).first()
    
    def update_status(self, job_id: str, status: str, file_path: Optional[str] = None, error_msg: Optional[str] = None) -> bool:
        try:
            job = self.get_job(job_id)
            if job:
                job.status = status
                if file_path:
                    job.file_path = file_path
                if error_msg:
                    job.error_msg = error_msg
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            self.db.rollback()
            return False
    
    def query_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.get_job(job_id)
        if job:
            return {"job_id": job.job_id, "status": job.status, "file_path": job.file_path, "error_msg": job.error_msg, "created_at": job.created_at, "updated_at": job.updated_at}
        return None

class PaperDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_papers(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[PaperInfo]:
        query = self.db.query(PaperInfo)
        if filters:
            if "year" in filters:
                query = query.filter(PaperInfo.year == filters["year"])
            if "keyword" in filters:
                query = query.filter(PaperInfo.keywords.like(f"%{filters['keyword']}%"))
        return query.limit(limit).all()

class AuthorDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_authors(self, limit: int = 100) -> List[AuthorInfo]:
        return self.db.query(AuthorInfo).limit(limit).all()

class OrganizationDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_organizations(self, limit: int = 100) -> List[OrganizationInfo]:
        return self.db.query(OrganizationInfo).limit(limit).all()
