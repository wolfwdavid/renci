"""PPP Loan dataset tools for Chinatown small businesses."""

import os
import pandas as pd

# NAICS code to human-readable name mapping
NAICS_LABELS = {
    "722511": "Full-Service Restaurant",
    "722513": "Limited-Service Restaurant",
    "311811": "Bakery",
    "311520": "Ice Cream & Frozen Dessert",
    "311611": "Meat Processing",
    "445110": "Grocery Store",
    "445299": "Specialty Food/Tea Shop",
    "448140": "Family Clothing Store",
    "448310": "Jewelry Store",
    "446110": "Pharmacy/Herbal Medicine",
    "451211": "Bookstore",
    "453110": "Florist",
    "444130": "Hardware Store",
    "531120": "Mall/Shopping Center",
    "812111": "Barber/Nail Salon",
    "812199": "Spa/Personal Care",
    "812310": "Laundry/Dry Cleaning",
    "811490": "Tailor/Alteration",
}

_df: pd.DataFrame | None = None


def _load_data() -> pd.DataFrame:
    """Load the pre-filtered PPP loan dataset."""
    global _df
    if _df is None:
        # __file__ is agent/actions/ppp_data.py → go up to apps/api/
        api_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_path = os.path.join(api_root, "data", "ppp_loans_chinatown.csv")
        _df = pd.read_csv(data_path, dtype={"NAICSCode": str, "BorrowerZip": str})
    return _df


def _naics_label(code: str) -> str:
    return NAICS_LABELS.get(code, f"Other ({code})")


def lookup_ppp_data(zip_code: str, business_type: str = "") -> dict:
    """Look up PPP loan statistics for Chinatown businesses by zip code.

    Use this when the owner asks about PPP loans, COVID relief, or
    small business funding in their neighborhood.

    Args:
        zip_code: The zip code to search (e.g. "10013" or "10002").
        business_type: Optional business type filter like "restaurant", "bakery", "salon".
    """
    df = _load_data()
    filtered = df[df["BorrowerZip"] == zip_code]

    if business_type:
        bt_lower = business_type.lower()
        # Map common terms to NAICS codes
        type_map = {
            "restaurant": ["722511", "722513"],
            "bakery": ["311811"],
            "salon": ["812111"],
            "grocery": ["445110"],
            "laundry": ["812310"],
            "retail": ["448140", "448310", "453110", "444130"],
            "tea": ["445299"],
        }
        codes = type_map.get(bt_lower, [])
        if codes:
            filtered = filtered[filtered["NAICSCode"].isin(codes)]

    if filtered.empty:
        return {"status": "success", "message": f"No PPP loan data found for zip {zip_code}."}

    total_loans = len(filtered)
    total_amount = filtered["InitialApprovalAmount"].sum()
    avg_amount = filtered["InitialApprovalAmount"].mean()
    total_jobs = filtered["JobsReported"].sum()

    return {
        "status": "success",
        "zip_code": zip_code,
        "total_loans": int(total_loans),
        "total_amount": f"${total_amount:,.0f}",
        "average_loan": f"${avg_amount:,.0f}",
        "total_jobs_supported": int(total_jobs),
        "message": (
            f"In zip {zip_code}: {total_loans} businesses received PPP loans "
            f"totaling {total_amount:,.0f}. Average loan: ${avg_amount:,.0f}. "
            f"Jobs supported: {int(total_jobs)}."
        ),
    }


def compare_ppp_by_industry(zip_code: str = "") -> dict:
    """Compare PPP loan amounts by industry type in Chinatown.

    Use this when the owner asks how their industry compares to others,
    or what types of businesses received the most relief.

    Args:
        zip_code: Optional zip code filter. If empty, shows all Chinatown data.
    """
    df = _load_data()
    if zip_code:
        df = df[df["BorrowerZip"] == zip_code]

    if df.empty:
        return {"status": "success", "message": "No PPP data available."}

    grouped = df.groupby("NAICSCode").agg(
        count=("LoanNumber", "count"),
        total=("InitialApprovalAmount", "sum"),
        avg=("InitialApprovalAmount", "mean"),
    ).sort_values("total", ascending=False)

    industries = []
    for code, row in grouped.iterrows():
        industries.append({
            "industry": _naics_label(str(code)),
            "loans": int(row["count"]),
            "total": f"${row['total']:,.0f}",
            "average": f"${row['avg']:,.0f}",
        })

    return {
        "status": "success",
        "industries": industries,
        "message": "Industry breakdown of PPP loans in Chinatown:\n" + "\n".join(
            f"- {i['industry']}: {i['loans']} loans, {i['total']} total"
            for i in industries[:5]
        ),
    }


def check_ppp_forgiveness(zip_code: str) -> dict:
    """Check PPP loan forgiveness rates for Chinatown businesses.

    Use this when the owner asks about loan forgiveness or repayment
    in their neighborhood.

    Args:
        zip_code: The zip code to check (e.g. "10013" or "10002").
    """
    df = _load_data()
    filtered = df[df["BorrowerZip"] == zip_code]

    if filtered.empty:
        return {"status": "success", "message": f"No PPP data for zip {zip_code}."}

    total = len(filtered)
    forgiven = filtered[filtered["ForgivenessAmount"] > 0]
    forgiven_count = len(forgiven)
    forgiveness_rate = (forgiven_count / total) * 100
    total_forgiven = forgiven["ForgivenessAmount"].sum()

    return {
        "status": "success",
        "zip_code": zip_code,
        "total_loans": int(total),
        "loans_forgiven": int(forgiven_count),
        "forgiveness_rate": f"{forgiveness_rate:.0f}%",
        "total_forgiven": f"${total_forgiven:,.0f}",
        "message": (
            f"In zip {zip_code}: {forgiveness_rate:.0f}% of PPP loans were forgiven "
            f"({forgiven_count}/{total}). Total forgiven: ${total_forgiven:,.0f}."
        ),
    }
