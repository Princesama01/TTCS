from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.services.document_service import DocumentService
from api.services.upload_service import UploadService
from api.dependencies import get_pipeline

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    return DocumentService()


def get_upload_service(pipeline=Depends(get_pipeline)) -> UploadService:
    return UploadService(pipeline=pipeline)


@router.get("")
async def list_documents(doc_service: DocumentService = Depends(get_document_service)):
    docs = doc_service.get_all_documents()
    return {"success": True, "documents": docs, "total": len(docs)}


@router.get("/{doc_id}/file")
async def get_document_original_file_meta(doc_id: str, doc_service: DocumentService = Depends(get_document_service)):
    try:
        file_info = doc_service.get_original_file_info(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Original file not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return {
        "success": True,
        "doc_id": doc_id,
        "file": {
            "name": file_info["name"],
            "content_type": file_info["content_type"],
            "size": file_info["size"],
            "content_url": f"/api/documents/{doc_id}/file/content",
        },
    }


@router.get("/{doc_id}/file/content")
async def get_document_original_file_content(doc_id: str, doc_service: DocumentService = Depends(get_document_service)):
    try:
        file_info = doc_service.get_original_file_info(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Original file not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return FileResponse(
        path=file_info["absolute_path"],
        media_type=file_info["content_type"],
        filename=file_info["name"],
        headers={"Content-Disposition": f'inline; filename="{file_info["name"]}"'},
    )


@router.get("/{doc_id}/clauses")
async def get_document_clauses(doc_id: str, upload_service: UploadService = Depends(get_upload_service)):
    structure_data = upload_service.get_document_structure(doc_id)
    if not structure_data:
        raise HTTPException(status_code=404, detail="Document structure not found")

    clauses = []
    for article in structure_data.get("articles", []):
        for clause in article.get("children", []):
            clauses.append(
                {
                    "id": f"{article.get('number')}.{clause.get('number')}",
                    "article_no": article.get("number"),
                    "clause_no": clause.get("number"),
                    "number": clause.get("number"),
                    "title": clause.get("title", ""),
                    "content": clause.get("content", ""),
                    "structure_path": clause.get("structure_path", ""),
                    "level": "clause",
                    "children": clause.get("children", []),
                }
            )

    return {
        "success": True,
        "doc_id": doc_id,
        "clauses": clauses,
        "total_clauses": len(clauses),
        "structure": structure_data,
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, doc_service: DocumentService = Depends(get_document_service)):
    doc_service.delete_document(doc_id)
    return {"success": True, "message": f"Document {doc_id} deleted"}
