"""Python types mirroring schema/events.sql and schema/panel.sql."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Layer(str, Enum):
    A = "A"  # deliberation
    B = "B"  # legislation
    C = "C"  # ordinances
    D = "D"  # news
    E = "E"  # mobilization
    F = "F"  # vernacular
    G = "G"  # project ledger
    H = "H"  # calibration


class Grievance(str, Enum):
    ENERGY_GRID_COST = "energy_grid_cost"
    WATER = "water"
    LAND_USE_NOISE_AESTHETICS = "land_use_noise_aesthetics"
    TAX_ABATEMENT_FISCAL = "tax_abatement_fiscal"
    JOBS_DISPLACEMENT = "jobs_displacement"
    SCHOOLS_EDUCATION = "schools_education"
    SAFETY_CONTROL = "safety_control"
    DATA_PRIVACY = "data_privacy"
    CREATIVE_WORK_IP = "creative_work_ip"


class Stance(str, Enum):
    OPPOSE = "oppose"
    SUPPORT = "support"
    MIXED = "mixed"
    NEUTRAL_DESCRIPTIVE = "neutral_descriptive"
    UNCLEAR = "unclear"


class Referent(str, Enum):
    LOCAL = "local"
    NATIONAL = "national"
    AMBIGUOUS = "ambiguous"


TAXONOMY_VERSION = "taxonomy_v0.1"


@dataclass
class Event:
    event_id: str
    state: str
    event_date: date
    event_month: str
    layer: Layer
    source: str
    county_fips: Optional[str] = None
    cbsa: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    grievance: list[Grievance] = field(default_factory=list)
    stance: Optional[Stance] = None
    referent: Optional[Referent] = None
    confidence: Optional[float] = None
    classifier_version: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    raw_payload_path: Optional[str] = None
    ingested_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if len(self.state) != 2 or not self.state.isalpha():
            raise ValueError(f"state must be USPS 2-letter, got {self.state!r}")
        self.state = self.state.upper()
        if self.county_fips is not None:
            if not (len(self.county_fips) == 5 and self.county_fips.isdigit()):
                raise ValueError(f"county_fips must be 5 digits, got {self.county_fips!r}")
        if len(self.event_month) != 7 or self.event_month[4] != "-":
            raise ValueError(f"event_month must be YYYY-MM, got {self.event_month!r}")


@dataclass
class PanelRow:
    county_fips: str
    state: str
    month: str
    n_deliberation: Optional[int] = None
    n_legislation: Optional[int] = None
    n_ordinances: Optional[int] = None
    n_news: Optional[int] = None
    n_mobilization: Optional[int] = None
    n_vernacular: Optional[int] = None
    n_project_actions: Optional[int] = None
    n_projects_proposed: Optional[int] = None
    n_projects_approved: Optional[int] = None
    n_projects_denied: Optional[int] = None
    n_projects_delayed: Optional[int] = None
    n_bills_introduced: Optional[int] = None
    n_bills_enacted: Optional[int] = None
    share_opposed_of_proposed: Optional[float] = None
    share_delayed_of_proposed: Optional[float] = None
    share_blocked_of_proposed: Optional[float] = None
    share_enacted_of_introduced: Optional[float] = None
    grievance_mix: Optional[dict[str, float]] = None
    taxonomy_version: str = TAXONOMY_VERSION
    as_of: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not (len(self.county_fips) == 5 and self.county_fips.isdigit()):
            raise ValueError(f"county_fips must be 5 digits, got {self.county_fips!r}")
        self.state = self.state.upper()
