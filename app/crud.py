from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import secrets

from .models import (
    Vessel, Repair, ComponentChange, ConfigChange,
    ChecklistItem, RepairChecklist
)
from .schemas import RepairCreate, RepairUpdate, RepairSnapshot

def _new_repair_uid() -> str:
    # Simple unique ID: REP-YYYYMMDD-<random>
    today = datetime.utcnow().strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()
    return f"REP-{today}-{suffix}"

def get_or_create_vessel(db: Session, hull_id: str) -> Vessel:
    v = db.execute(select(Vessel).where(Vessel.hull_id == hull_id)).scalar_one_or_none()
    if v:
        return v
    v = Vessel(hull_id=hull_id)
    db.add(v)
    db.flush()
    return v

def create_repair(db: Session, payload: RepairCreate) -> Repair:
    vessel = get_or_create_vessel(db, payload.hull_id)
    rep = Repair(
        repair_uid=_new_repair_uid(),
        vessel_id=vessel.id,
        date_opened=payload.date_opened,
        location=payload.location,
        ticket=payload.ticket,
        technicians=payload.technicians,
        program=payload.program,
        service_type=payload.service_type,
        root_cause_cat=payload.root_cause_cat,
        issue_desc=payload.issue_desc,
    )
    db.add(rep)
    db.flush()
    return rep

def get_repair_by_uid(db: Session, repair_uid: str) -> Repair | None:
    return db.execute(select(Repair).where(Repair.repair_uid == repair_uid)).scalar_one_or_none()

def list_repairs(db: Session, hull_id: str | None, date_from, date_to, limit: int):
    q = select(Repair).order_by(Repair.date_opened.desc()).limit(limit)
    if hull_id:
        q = q.join(Vessel).where(Vessel.hull_id == hull_id)
    if date_from:
        q = q.where(Repair.date_opened >= date_from)
    if date_to:
        q = q.where(Repair.date_opened <= date_to)
    return db.execute(q).scalars().all()

def update_repair(db: Session, rep: Repair, payload: RepairUpdate) -> Repair:
    data = payload.model_dump(exclude_unset=True)

    snap = data.pop("snapshot", None)
    for k, v in data.items():
        setattr(rep, k, v)

    if snap:
        # map snapshot fields
        rep.snapshot_ilmor_sn = snap.ilmor_sn
        rep.snapshot_ilmor_fw = snap.ilmor_fw
        rep.snapshot_icu_sn = snap.icu_sn
        rep.snapshot_orca_sn = snap.orca_sn
        rep.snapshot_battery_sns = snap.battery_sns
        rep.snapshot_camera = snap.camera
        rep.snapshot_radar = snap.radar
        rep.snapshot_compass = snap.compass
        rep.snapshot_two_battery = snap.two_battery

    db.add(rep)
    db.flush()
    return rep

def add_component_change(db: Session, rep: Repair, chg) -> ComponentChange:
    row = ComponentChange(repair_id=rep.id, **chg.model_dump())
    db.add(row)
    db.flush()
    return row

def delete_component_change(db: Session, change_id: int) -> bool:
    row = db.get(ComponentChange, change_id)
    if not row:
        return False
    db.delete(row)
    return True

def add_config_change(db: Session, rep: Repair, chg) -> ConfigChange:
    row = ConfigChange(repair_id=rep.id, **chg.model_dump())
    db.add(row)
    db.flush()
    return row

def delete_config_change(db: Session, change_id: int) -> bool:
    row = db.get(ConfigChange, change_id)
    if not row:
        return False
    db.delete(row)
    return True

def get_checklist_items(db: Session):
    return db.execute(select(ChecklistItem).where(ChecklistItem.active == True).order_by(ChecklistItem.sort_order.asc())).scalars().all()

def upsert_repair_checklist(db: Session, rep: Repair, states: dict[str, bool]):
    items = db.execute(select(ChecklistItem)).scalars().all()
    by_code = {i.code: i for i in items}

    for code, checked in states.items():
        item = by_code.get(code)
        if not item:
            continue
        pk = {"repair_id": rep.id, "item_id": item.id}
        row = db.get(RepairChecklist, pk)
        if not row:
            row = RepairChecklist(**pk, checked=checked, checked_at=(datetime.utcnow() if checked else None))
            db.add(row)
        else:
            row.checked = checked
            row.checked_at = datetime.utcnow() if checked else None
            db.add(row)
    db.flush()
