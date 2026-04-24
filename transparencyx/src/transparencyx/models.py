from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class Chamber(Enum):
    HOUSE = "house"
    SENATE = "senate"


@dataclass
class DisclosureRange:
    original_label: str
    minimum: Optional[int]
    maximum: Optional[int]
    midpoint: Optional[int]


@dataclass
class MemberIdentity:
    name: str
    chamber: Chamber
    state: str
    district: Optional[str] = None


@dataclass
class FinancialAsset:
    name: str
    asset_type: str
    value_range: DisclosureRange


@dataclass
class BusinessInterest:
    name: str
    interest_type: str
    value_range: DisclosureRange


@dataclass
class OutsideIncome:
    source: str
    income_type: str
    amount_range: DisclosureRange


@dataclass
class Liability:
    creditor: str
    liability_type: str
    amount_range: DisclosureRange


@dataclass
class DisclosureReport:
    member: MemberIdentity
    year: int
    assets: List[FinancialAsset]
    business_interests: List[BusinessInterest]
    outside_incomes: List[OutsideIncome]
    liabilities: List[Liability]
