from sqlalchemy import (
    Column, String, Text, Date, DateTime, Boolean,
    ForeignKey, BigInteger, Enum, Integer
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class Subsystem(str, enum.Enum):
    Ilmor = "Ilmor"
    ICU = "ICU"
    HMI_Box = "HMI Box"
    Kitbox = "Kitbox"
    Orca = "Orca"
    Battery = "Battery"
    PDB = "PDB"
    MPPT = "MPPT"
    Camera = "Camera"
    Radar = "Radar"
    Compass = "Compass"
    LTE_Starlink = "LTE/Starlink"
    Harness_Cabling = "Harness/Cabling"
    Other = "Other"

class RepairStatus(str, enum.Enum):
    Operational = "Operational"
    Operational_with_Limitation = "Operational with Limitation"
    Pending_Parts = "Pending Parts"
    Out_of_Service = "Out of Service"

class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(BigInteger, primary_key=True)
    hull_id = Column(String, unique=True, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repairs = relationship("Repair", back_populates="vessel", cascade="all,delete")

class Repair(Base):
    __tablename__ = "repairs"

    id = Column(BigInteger, primary_key=True)
    repair_uid = Column(String, unique=True, nullable=False)
    vessel_id = Column(BigInteger, ForeignKey("vessels.id"), nullable=False)

    location = Column(String)
    date_opened = Column(Date, nullable=False)
    ticket = Column(String)
    technicians = Column(String)
    program = Column(String)
    service_type = Column(String)
    root_cause_cat = Column(String)
    issue_desc = Column(Text)
    root_cause_details = Column(Text)
    wiring_notes = Column(Text)
    structural_notes = Column(Text)
    verification_notes = Column(Text)
    final_status = Column(Enum(RepairStatus, name="repair_status"), nullable=True)
    limitations = Column(Text)

    snapshot_ilmor_sn = Column(String)
    snapshot_ilmor_fw = Column(String)
    snapshot_icu_sn = Column(String)
    snapshot_orca_sn = Column(String)
    snapshot_battery_sns = Column(String)
    snapshot_camera = Column(String)
    snapshot_radar = Column(Boolean)
    snapshot_compass = Column(Boolean)
    snapshot_two_battery = Column(Boolean)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    vessel = relationship("Vessel", back_populates="repairs")
    component_changes = relationship("ComponentChange", back_populates="repair", cascade="all,delete-orphan")
    config_changes = relationship("ConfigChange", back_populates="repair", cascade="all,delete-orphan")
    checklist = relationship("RepairChecklist", back_populates="repair", cascade="all,delete-orphan")

class ComponentChange(Base):
    __tablename__ = "component_changes"

    id = Column(BigInteger, primary_key=True)
    repair_id = Column(BigInteger, ForeignKey("repairs.id", ondelete="CASCADE"), nullable=False)

    subsystem = Column(Enum(Subsystem, name="subsystem"), nullable=False)
    component = Column(String, nullable=False)
    old_serial = Column(String)
    new_serial = Column(String)
    old_fw = Column(String)
    new_fw = Column(String)
    reason = Column(Text)
    performed_by = Column(String)
    change_date = Column(Date)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repair = relationship("Repair", back_populates="component_changes")

class ConfigChange(Base):
    __tablename__ = "config_changes"

    id = Column(BigInteger, primary_key=True)
    repair_id = Column(BigInteger, ForeignKey("repairs.id", ondelete="CASCADE"), nullable=False)

    system = Column(String, nullable=False)
    parameter = Column(String, nullable=False)
    old_value = Column(String)
    new_value = Column(String)
    reason = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repair = relationship("Repair", back_populates="config_changes")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(BigInteger, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    label = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    active = Column(Boolean, nullable=False, server_default="true")

    repairs = relationship("RepairChecklist", back_populates="item")

class RepairChecklist(Base):
    __tablename__ = "repair_checklist"

    repair_id = Column(BigInteger, ForeignKey("repairs.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(BigInteger, ForeignKey("checklist_items.id"), primary_key=True)

    checked = Column(Boolean, nullable=False, server_default="false")
    checked_at = Column(DateTime(timezone=True))

    repair = relationship("Repair", back_populates="checklist")
    item = relationship("ChecklistItem", back_populates="repairs")
