import csv
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc

from . import models, schemas
from .database import Base, engine, get_db
from .rates import rate_book

# Create DB tables on startup if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Raj Art Service - Sheet Printing Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RATE / CALCULATION ENDPOINTS
# ============================================================

@app.get("/api/rates/options", response_model=schemas.RateOptions)
def get_rate_options():
    return rate_book.options()


@app.post("/api/calculate", response_model=schemas.CalculateResponse)
def calculate(payload: schemas.CalculateRequest):
    try:
        result = rate_book.calculate(
            gsm=payload.gsm,
            quantity=payload.quantity,
            printing_side=payload.printing_side,
            lamination=payload.lamination,
            use_nearest_quantity=payload.use_nearest_quantity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


# ============================================================
# ORDER (CUSTOMER DATA) ENDPOINTS - the "database" part
# ============================================================

@app.post("/api/orders", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        result = rate_book.calculate(
            gsm=payload.gsm,
            quantity=payload.quantity,
            printing_side=payload.printing_side,
            lamination=payload.lamination,
            use_nearest_quantity=payload.use_nearest_quantity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    order = models.Order(
        customer_name=(payload.customer_name or "").strip(),
        customer_phone=(payload.customer_phone or "").strip(),
        notes=(payload.notes or "").strip(),
        gsm=result["gsm"],
        quantity=result["quantity"],
        printing_side=result["printing_side"],
        lamination=result["lamination"],
        rate_quantity_used=result["rate_quantity_used"],
        used_nearest_quantity=result["used_nearest_quantity"],
        printing_min=result["printing_min"],
        printing_max=result["printing_max"],
        lamination_price=result["lamination_price"],
        final_min_per_piece=result["final_min_per_piece"],
        final_max_per_piece=result["final_max_per_piece"],
        total_min=result["total_min"],
        total_max=result["total_max"],
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/orders", response_model=list[schemas.OrderOut])
def list_orders(
    search: Optional[str] = Query(None, description="Search by customer name or phone"),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(models.Order)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (models.Order.customer_name.ilike(like))
            | (models.Order.customer_phone.ilike(like))
        )
    return query.order_by(desc(models.Order.created_at)).limit(limit).all()


@app.get("/api/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.delete("/api/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"ok": True}


@app.get("/api/orders/export/csv")
def export_orders_csv(db: Session = Depends(get_db)):
    orders = db.query(models.Order).order_by(desc(models.Order.created_at)).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID", "Date", "Customer Name", "Phone", "GSM", "Quantity",
            "Printing Side", "Lamination", "Rate Bracket Used",
            "Used Nearest?", "Final Min/Piece", "Final Max/Piece",
            "Total Min", "Total Max", "Notes",
        ]
    )
    for o in orders:
        writer.writerow(
            [
                o.id, o.created_at, o.customer_name, o.customer_phone, o.gsm,
                o.quantity, o.printing_side, o.lamination, o.rate_quantity_used,
                o.used_nearest_quantity, o.final_min_per_piece, o.final_max_per_piece,
                o.total_min, o.total_max, o.notes,
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=raj_art_orders.csv"},
    )


# ============================================================
# SERVE THE FRONTEND (static files) - one deployable service
# ============================================================

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
