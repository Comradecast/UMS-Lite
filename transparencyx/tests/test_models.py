from transparencyx.models import (
    Chamber,
    DisclosureRange,
    MemberIdentity,
    FinancialAsset,
    BusinessInterest,
    OutsideIncome,
    Liability,
    DisclosureReport
)

def test_member_identity_creation():
    member = MemberIdentity(
        name="John Doe",
        chamber=Chamber.HOUSE,
        state="CA",
        district="1"
    )
    assert member.name == "John Doe"
    assert member.chamber == Chamber.HOUSE
    assert member.state == "CA"
    assert member.district == "1"

def test_disclosure_report_creation():
    member = MemberIdentity(
        name="Jane Smith",
        chamber=Chamber.SENATE,
        state="NY"
    )

    range_obj = DisclosureRange(
        original_label="$1,001 - $15,000",
        minimum=1001,
        maximum=15000,
        midpoint=8000
    )

    asset = FinancialAsset(
        name="Index Fund",
        asset_type="Mutual Fund",
        value_range=range_obj
    )

    report = DisclosureReport(
        member=member,
        year=2023,
        assets=[asset],
        business_interests=[],
        outside_incomes=[],
        liabilities=[]
    )

    assert report.year == 2023
    assert len(report.assets) == 1
    assert report.assets[0].name == "Index Fund"
