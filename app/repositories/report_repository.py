"""Repository: 영속 저장·조회만 담당. 외부 API/Embedding 요청은 여기서 하지 않습니다."""
from datetime import date,datetime,timezone
from typing import Any
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.models.report import (ReportCategory,Report,ReportEmbedding,DETAIL_MODELS,DETAIL_FIELDS,
                               PromptVersion)
from app.services.errors import DomainError


def category_for_code(db:Session,code:str)->ReportCategory:
    """TODO B-05 · category_for_code() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-05: code에 대응하는 ReportCategory 1건을 조회하고 없으면 422 에러를 발생시키세요.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    category = db.scalar(
        select(ReportCategory).where(ReportCategory.code == code)
    )

    if category is None:
        raise DomainError(422, "VALIDATION_ERROR", "등록되지 않은 카테고리 입니다.")    

    return category

def get_report_and_detail(db:Session,rid:int,lock:bool=False):
    """TODO B-06 · get_report_and_detail() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-06: 공통 Report + Category + 일치하는 상세 모델을 조회하세요.
    # 잠금이 필요하면 with_for_update를
    # TODO B-06: 적용하고 없는 ID는 404.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    stmt = select(Report).where(Report.report_id == rid)
    if lock:
        stmt = stmt.with_for_update()
    report = db.scalar(stmt)
    if report is None:
        raise DomainError(404, "REPORT_NOT_FOUND", "요청한 보고서를 찾을 수 없습니다.")
    report_category = db.scalar(
        select(ReportCategory).where(ReportCategory.category_id == report.category_id)
    )
    detail_model = DETAIL_MODELS[report_category.code]
    detail = db.get(detail_model, rid)
    if detail is None:
        raise DomainError(500, "DATA_INTEGRITY_ERROR", "보고서 상세 행이 누락되었습니다.")
    return report, report_category, detail

def plain_value(obj:Any):
    """TODO B-06 · plain_value() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-06: datetime은 UTC로 변환한 ISO 8601 문자열(Z), date는 YYYY-MM-DD로 반환하세요.
    # 시간대 없는 datetime은 DATA_INTEGRITY_ERROR(500)로 구분하고 그 외 값은 그대로 반환합니다.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    if isinstance(obj, datetime):
        if obj.utcoffset() is None:
            raise DomainError(
                500,
                "DATA_INTEGRITY_ERROR",
                "시각 데이터에 시간대가 없습니다.",
            )

        utc_value = obj.astimezone(timezone.utc)
        return utc_value.isoformat().removesuffix("+00:00") + "Z"

    if isinstance(obj, date):
        return obj.isoformat()

    return obj

def serialize_report(report:Report,category:ReportCategory,detail)->dict:
    """TODO B-06 · serialize_report() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-06: report/category/detail을 API-03의 단일 응답 형식으로 묶으세요.
    # TODO B-06: title/content/author는 상세 테이블에서 가져오세요.
    # created_at/updated_at와 details의 시각도 plain_value()로 UTC 직렬화하세요.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    return {
    "report_id": report.report_id,
    "category_code": category.code,
    "title": detail.title,
    "details": {
        "experiment_date": plain_value(detail.experiment_date),
        },
    }
def read_report(db:Session,rid:int)->dict:
    """TODO B-06 · read_report() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-06: get_report_and_detail과 serialize_report를 연결해 단일 보고서를 반환하세요.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    report, category, detail = get_report_and_detail(db, rid)
    return serialize_report(report, category, detail)


def list_reports(db:Session, title:str|None,limit:int,offset:int,
                 category_code:str|None=None,updated_after:datetime|None=None)->dict:
    """TODO B-07 · list_reports() — mentor와 동일한 함수 계약을 완성하세요."""
    # TODO B-07: report_read_view를 이용해 6종 통합 제목 조회·정렬·페이지/total을 반환하세요. SQL 값은 바인딩하세요.
    # 입력·반환형과 예외·상태코드는 요구사항 명세서/API 계약을 참조합니다.
    # 정답 구현 후 아래 예외를 지우고 로직을 작성하세요.
    conditions = []
    params = {}

    if title:   
        escaped_title = title.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        conditions.append("title ILIKE :title ESCAPE '!'")
        params["title"] = f"%{escaped_title}%"

    if category_code is not None:
        conditions.append("category_code = :category_code")
        params["category_code"] = category_code

    if updated_after is not None:
        conditions.append("update_at >= :updated_after")
        params["updated_after"] = updated_after

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM report_read_view{where}"),
        params,
    ).scalar_one()

    items = db.execute(
        text(f"""
            SELECT report_id, category_code, title, revision
            FROM report_read_view{where}
            ORDER BY update_at DESC, report_id DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    return {
        "items": [dict(row) for row in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }