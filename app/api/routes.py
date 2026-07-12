from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["nic"])


@router.post("/extract")
def extract_placeholder() -> dict[str, str]:
    return {
        "status": "pending",
        "message": "NIC extraction endpoint scaffolded. Implementation follows in later milestones.",
    }
