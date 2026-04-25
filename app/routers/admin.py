from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/migrate")
async def run_migrations(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Run Alembic migrations - Admin only"""
    import subprocess
    import os

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "."},
    )

    if result.returncode == 0:
        return {"status": "success", "output": result.stdout}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {result.stderr}",
        )


@router.post("/migrate-down")
async def downgrade_migrations(
    revision: str = "base",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Downgrade migrations - Admin only"""
    import subprocess
    import os

    result = subprocess.run(
        ["alembic", "downgrade", revision],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "."},
    )

    if result.returncode == 0:
        return {"status": "success", "output": result.stdout}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {result.stderr}",
        )


@router.get("/health-db")
async def health_check_db(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Check database connection"""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {str(e)}",
        )
