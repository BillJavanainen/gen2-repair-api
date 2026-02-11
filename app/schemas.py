from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, datetime
from .models import Subsystem, RepairStatus

class RepairSnapshot(BaseModel):
    ilmor_sn: Optional[str] = None
    ilmor_fw: Optional[str] = None
    icu_sn: Optional[str] = None
    orca_sn: Optional[str] = None
    battery_sns: Optional[str] = None
    camera: Optional[str] = None
    radar: Optional[bool] = None
    compass: Optional[bool] = None
    two_battery: Optional[bool] = None

class RepairCreate(BaseModel):
    hull_id: str = Field(..., examples=["R132"])
    date_opened: date
    location: Optional[str] = None
    ticket: Optional[str] = None
    technicians: Optional[str] = None
    program: Optional[str] = None
    service_type: Optional[str] = None
    root_cause_cat: Optional[str] = None
    issue_desc: Optional[str] = None

class RepairUpdate(BaseModel):
    location: Optional[str] = None
    ticket: Optional[str] = None
    technicians: Optional[str] = None
    program: Optional[str] = None
    service_type: Optional[str] = None
    root_cause_cat: Optional[str] = None
    issue_desc: Optional[str] = None
    root_cause_details: Optional[str] = None
    wiring_notes: Optional[str] = None
    structural_notes: Optional[str] = None
    verification_notes: Optional[str] = None
    final_status: Optional[RepairStatus] = None
    limitations: Optional[str] = None
    snapshot: Optional[RepairSnapshot] = None

class ComponentChangeCreate(BaseModel):
    subsystem: Subsystem
    component: str
    old_serial: Optional[str] = None
    new_serial: Optional[str] = None
    old_fw: Optional[str] = None
    new_fw: Optional[str] = None
    reason: Optional[str] = None
    performed_by: Optional[str] = None
    change_date: Optional[date] = None

class ConfigChangeCreate(BaseModel):
    system: str
    parameter: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None

class ChecklistItemOut(BaseModel):
    code: str
    label: str
    sort_order: int
    active: bool

class ChecklistUpdate(BaseModel):
    # key: checklist_items.code, value: checked boolean
    states: Dict[str, bool]

class ComponentChangeOut(ComponentChangeCreate):
    id: int
    created_at: datetime

class ConfigChangeOut(ConfigChangeCreate):
    id: int
    created_at: datetime

class RepairOut(BaseModel):
    repair_uid: str
    hull_id: str
    date_opened: date
    location: Optional[str] = None
    ticket: Optional[str] = None
    technicians: Optional[str] = None
    program: Optional[str] = None
    service_type: Optional[str] = None
    root_cause_cat: Optional[str] = None
    issue_desc: Optional[str] = None
    root_cause_details: Optional[str] = None
    wiring_notes: Optional[str] = None
    structural_notes: Optional[str] = None
    verification_notes: Optional[str] = None
    final_status: Optional[RepairStatus] = None
    limitations: Optional[str] = None
    snapshot: RepairSnapshot

    component_changes: List[ComponentChangeOut] = []
    config_changes: List[ConfigChangeOut] = []
    checklist: Dict[str, bool] = {}
