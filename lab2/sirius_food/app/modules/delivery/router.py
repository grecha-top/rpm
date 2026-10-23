"""HTTP facade delegating delivery operations to the gRPC service."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import require_role
from app.models import User
from app.modules.delivery.grpc_client import (
    DeliveryClientConflictError,
    DeliveryClientNotFoundError,
    DeliveryClientPermissionError,
    DeliveryClientTimeoutError,
    DeliveryClientUnavailableError,
    DeliveryGrpcClient,
)
from app.schemas import DeliveryAssign


router = APIRouter()


def _client_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DeliveryClientNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DeliveryClientPermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, DeliveryClientConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, DeliveryClientTimeoutError):
        return HTTPException(status_code=504, detail="Delivery service timeout")
    return HTTPException(status_code=503, detail="Delivery service unavailable")


@router.post("/assign")
def assign_courier(
    payload: DeliveryAssign,
    current_user: User = Depends(require_role("admin", "cook")),
):
    client = DeliveryGrpcClient()
    try:
        result = client.assign_courier(payload.order_id, payload.courier_id)
        return {"status": "success", **result}
    except (
        DeliveryClientNotFoundError,
        DeliveryClientPermissionError,
        DeliveryClientConflictError,
        DeliveryClientTimeoutError,
        DeliveryClientUnavailableError,
    ) as exc:
        raise _client_error(exc) from exc
    finally:
        client.close()


@router.get("/my")
def my_deliveries(
    current_user: User = Depends(require_role("courier", "admin")),
):
    client = DeliveryGrpcClient()
    try:
        return client.list_deliveries(
            courier_id=current_user.id,
            include_all=current_user.role.name == "admin",
        )
    except (DeliveryClientTimeoutError, DeliveryClientUnavailableError) as exc:
        raise _client_error(exc) from exc
    finally:
        client.close()


@router.patch("/{delivery_id}/complete")
def complete_delivery(
    delivery_id: int,
    current_user: User = Depends(require_role("courier", "admin")),
):
    client = DeliveryGrpcClient()
    try:
        result = client.complete_delivery(
            delivery_id,
            actor_id=current_user.id,
            actor_is_admin=current_user.role.name == "admin",
        )
        return {"status": "success", "delivery_status": result["status"]}
    except (
        DeliveryClientNotFoundError,
        DeliveryClientPermissionError,
        DeliveryClientConflictError,
        DeliveryClientTimeoutError,
        DeliveryClientUnavailableError,
    ) as exc:
        raise _client_error(exc) from exc
    finally:
        client.close()


@router.get("/track/{order_id}")
def track_delivery(
    order_id: int,
    current_user: User = Depends(require_role("student", "courier", "admin")),
):
    def stream():
        client = DeliveryGrpcClient()
        try:
            for status in client.track_delivery(order_id):
                yield json.dumps(status, ensure_ascii=False) + "\n"
        finally:
            client.close()

    return StreamingResponse(stream(), media_type="application/x-ndjson")
