from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chat_message import ChatMessage
from app.models.report import Report
from app.models.scan import Scan
from app.models.user import User
from app.schemas.report import ChatMessageIn, ChatMessageOut
from app.services.ai.report_generator import chat_about_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_owned_report(scan_id: int, db: Session, current_user: User) -> Report:
    report = (
        db.query(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Scan.target)
        .filter(Report.scan_id == scan_id, Scan.target.has(owner_id=current_user.id))
        .first()
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/{scan_id}/chat", response_model=list[ChatMessageOut])
def get_chat_history(
    scan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ChatMessage]:
    report = _get_owned_report(scan_id, db, current_user)
    return report.chat_messages


@router.post("/{scan_id}/chat", response_model=ChatMessageOut)
def ask_report_question(
    scan_id: int,
    payload: ChatMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessage:
    report = _get_owned_report(scan_id, db, current_user)

    user_message = ChatMessage(report_id=report.id, role="user", content=payload.question)
    db.add(user_message)
    db.commit()

    history = [{"role": m.role, "content": m.content} for m in report.chat_messages]
    answer = chat_about_report(report=report, history=history, question=payload.question)

    assistant_message = ChatMessage(report_id=report.id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message
