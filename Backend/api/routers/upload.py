import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from api.dependencies import get_pipeline
from api.services.document_service import DocumentService
from api.services.upload_service import UploadService
from api.pipeline import LegalVectorPipeline

router = APIRouter(prefix="/api", tags=["upload"])


def get_upload_service(pipeline: LegalVectorPipeline = Depends(get_pipeline)) -> UploadService:
    return UploadService(pipeline=pipeline)


def get_document_service() -> DocumentService:
    return DocumentService()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    upload_service: UploadService = Depends(get_upload_service),
    doc_service: DocumentService = Depends(get_document_service),
):
    file_content = await file.read()
    is_valid, error_msg = upload_service.validate_file(file.filename, file_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    upload_id = str(uuid.uuid4())
    file_type = "pdf" if file.filename.lower().endswith(".pdf") else "docx"
    file_size = len(file_content)

    doc_service.add_document(doc_id=doc_id, name=file.filename, file_type=file_type, size=file_size)
    file_info = upload_service.save_original_file(doc_id=doc_id, filename=file.filename, file_content=file_content)
    doc_service.update_document_file_info(doc_id=doc_id, **file_info)

    async def process_and_update():
        try:
            result = await upload_service.process_upload(upload_id, doc_id, file_content, file.filename)
            doc_service.update_document_status(doc_id, "ready", chunk_count=result.get("chunk_count", 0))
        except Exception:
            doc_service.update_document_status(doc_id, "error")

    if background_tasks:
        background_tasks.add_task(process_and_update)
    else:
        await process_and_update()

    return {
        "success": True,
        "upload_id": upload_id,
        "doc_id": doc_id,
        "file_name": file.filename,
        "file_size": file_size,
        "file_type": file_type,
        "original_file_name": file_info["original_file_name"],
        "message": "File uploaded successfully",
    }


@router.get("/upload/status/{upload_id}")
async def get_upload_status(upload_id: str, upload_service: UploadService = Depends(get_upload_service)):
    status = upload_service.get_upload_status(upload_id)
    if not status:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {
        "success": True,
        "upload_id": upload_id,
        "file_name": status["file_name"],
        "progress": status["progress"],
        "pipeline_status": status["pipeline_status"],
        "started_at": status["started_at"],
    }
