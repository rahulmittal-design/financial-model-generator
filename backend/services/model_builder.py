"""
Phase 4 – Historical Financial Model Builder

Reads approved FinancialLineItems for a project, assembles them into
IS / BS / CF statement tables, derives calculated rows, and persists
FinancialModelEntry records to the DB.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import FinancialLineItem, FinancialModelEntry, Project
from services import llm_service

logger = logging.getLogger(__name__)

# ── statement membership map ──────────────────────────────────────────────────
# Defines which standard_ids belong to each statement and their display order.

IS_ITEMS = [
    "revenue", "cost_of_goods_sold", "gross_profit",
    "selling_general_admin", "research_development", "depreciation_amortization",
    "other_operating_expenses", "operating_income",
    "interest_expense", "interest_income", "other_non_operating",
    "pre_tax_income", "income_tax_expense", "net_income",
    "earnings_per_share_basic", "earnings_per_share_diluted",
    "shares_outstanding_basic", "shares_outstanding_diluted",
    "ebitda", "ebit",
]

BS_ITEMS = [
    "cash_and_equivalents", "short_term_investments",
    "accounts_receivable", "inventory", "other_current_assets", "total_current_assets",
    "property_plant_equipment", "goodwill", "intangible_assets",
    "long_term_investments", "other_non_current_assets", "total_non_current_assets",
    "total_assets",
    "accounts_payable", "short_term_debt", "accrued_liabilities",
    "other_current_liabilities", "total_current_liabilities",
    "long_term_debt", "deferred_tax_liability", "other_non_current_liabilities",
    "total_non_current_liabilities", "total_liabilities",
    "common_stock", "retained_earnings", "other_equity",
    "total_shareholders_equity", "total_liabilities_equity",
    "book_value_per_share",
]

CF_ITEMS = [
    "net_income",
    "depreciation_amortization", "stock_based_compensation",
    "changes_in_working_capital", "other_operating_activities",
    "operating_cash_flow",
    "capital_expenditures", "acquisitions", "purchases_investments",
    "sales_investments", "other_investing_activities",
    "investing_cash_flow",
    "debt_issuance", "debt_repayment", "dividends_paid",
    "share_issuance", "share_buybacks", "other_financing_activities",
    "financing_cash_flow",
    "net_change_in_cash", "free_cash_flow",
]

STATEMENT_MAP: Dict[str, List[str]] = {
    "income_statement": IS_ITEMS,
    "balance_sheet": BS_ITEMS,
    "cash_flow": CF_ITEMS,
}


def _get_statement_type(standard_id: str) -> str:
    for stmt, items in STATEMENT_MAP.items():
        if standard_id in items:
            return stmt
    return "other"


# ── derived / calculated rows ─────────────────────────────────────────────────

def _derive_rows(
    data: Dict[str, Dict[str, Optional[float]]]  # standard_id -> period -> value
) -> Dict[str, Dict[str, Optional[float]]]:
    """Compute derived line items that may not be directly extracted."""

    def v(sid: str, period: str) -> Optional[float]:
        return data.get(sid, {}).get(period)

    periods = sorted({p for vals in data.values() for p in vals})
    derived: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)

    for p in periods:
        revenue = v("revenue", p)
        cogs = v("cost_of_goods_sold", p)
        gp = v("gross_profit", p)
        opex = v("selling_general_admin", p)
        rd = v("research_development", p)
        da = v("depreciation_amortization", p)
        oi = v("operating_income", p)
        ie = v("interest_expense", p)
        ii = v("interest_income", p)
        pti = v("pre_tax_income", p)
        tax = v("income_tax_expense", p)
        ni = v("net_income", p)

        # Gross profit
        if gp is None and revenue is not None and cogs is not None:
            derived["gross_profit"][p] = revenue - cogs

        # Operating income (EBIT)
        if oi is None:
            parts = [v("gross_profit", p) or (revenue - cogs if revenue and cogs else None)]
            deductions = [opex, rd, da]
            if all(x is not None for x in parts) and parts[0] is not None:
                deducted = sum(x for x in deductions if x is not None)
                derived["operating_income"][p] = parts[0] - deducted

        # EBIT = operating_income
        if v("ebit", p) is None and (oi or derived["operating_income"].get(p)) is not None:
            derived["ebit"][p] = oi or derived["operating_income"].get(p)

        # EBITDA
        if v("ebitda", p) is None:
            ebit_val = oi or derived.get("ebit", {}).get(p)
            da_val = da
            if ebit_val is not None and da_val is not None:
                derived["ebitda"][p] = ebit_val + da_val

        # Pre-tax income
        if pti is None:
            oi_val = oi or derived.get("operating_income", {}).get(p)
            if oi_val is not None:
                adj = (ii or 0) - (ie or 0)
                derived["pre_tax_income"][p] = oi_val + adj

        # Net income
        if ni is None:
            pti_val = pti or derived.get("pre_tax_income", {}).get(p)
            if pti_val is not None and tax is not None:
                derived["net_income"][p] = pti_val - tax

        # Free cash flow
        ocf = v("operating_cash_flow", p)
        capex = v("capital_expenditures", p)
        if v("free_cash_flow", p) is None and ocf is not None and capex is not None:
            derived["free_cash_flow"][p] = ocf - abs(capex)

    return derived


# ── key ratios ────────────────────────────────────────────────────────────────

def _compute_ratios(
    data: Dict[str, Dict[str, Optional[float]]]
) -> Dict[str, Dict[str, Optional[float]]]:
    def v(sid: str, period: str) -> Optional[float]:
        return data.get(sid, {}).get(period)

    periods = sorted({p for vals in data.values() for p in vals})
    ratios: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)

    for p in periods:
        revenue = v("revenue", p)
        gp = v("gross_profit", p)
        oi = v("operating_income", p)
        ni = v("net_income", p)
        ebitda = v("ebitda", p)
        ta = v("total_assets", p)
        tse = v("total_shareholders_equity", p)
        ltd = v("long_term_debt", p)
        ocf = v("operating_cash_flow", p)
        capex = v("capital_expenditures", p)
        fcf = v("free_cash_flow", p)

        # Profitability
        ratios["gross_margin"][p] = (gp / revenue * 100) if gp and revenue else None
        ratios["operating_margin"][p] = (oi / revenue * 100) if oi and revenue else None
        ratios["net_margin"][p] = (ni / revenue * 100) if ni and revenue else None
        ratios["ebitda_margin"][p] = (ebitda / revenue * 100) if ebitda and revenue else None

        # Returns
        ratios["return_on_assets"][p] = (ni / ta * 100) if ni and ta else None
        ratios["return_on_equity"][p] = (ni / tse * 100) if ni and tse else None

        # Leverage
        if tse and tse != 0:
            ratios["debt_to_equity"][p] = (ltd / tse) if ltd else None

        # Cash flow
        ratios["fcf_margin"][p] = (fcf / revenue * 100) if fcf and revenue else None
        ratios["capex_to_revenue"][p] = (abs(capex) / revenue * 100) if capex and revenue else None

    return {k: dict(v) for k, v in ratios.items()}


# ── main builder ──────────────────────────────────────────────────────────────

def build_financial_model(project_id: str, db: Session, use_llm: bool = True) -> Dict[str, Any]:
    """
    1. Load approved line items
    2. Optionally enhance ambiguous mappings via LLM
    3. Aggregate into IS / BS / CF tables
    4. Derive calculated rows
    5. Compute key ratios
    6. Persist FinancialModelEntry rows
    7. Return structured model dict
    """
    # 1. Load approved items
    items: List[FinancialLineItem] = (
        db.query(FinancialLineItem)
        .filter(
            FinancialLineItem.project_id == project_id,
            FinancialLineItem.review_status == "approved",
        )
        .all()
    )

    if not items:
        return {"error": "No approved line items found. Please review and approve extracted items first."}

    # 2. (Optional) LLM enhancement for low-confidence mappings
    if use_llm and llm_service.is_loaded():
        for item in items:
            if item.confidence_score is not None and item.confidence_score < 0.7:
                try:
                    result = llm_service.enhance_line_item_mapping(
                        raw_label=item.raw_label or "",
                        candidate_ids=[item.standard_id or "unknown"],
                        context=f"statement: {item.statement_type}",
                    )
                    if result.get("confidence", 0) > (item.confidence_score or 0):
                        item.standard_id = result["standard_id"]
                        item.confidence_score = result["confidence"]
                except Exception as e:
                    logger.warning(f"LLM enhancement failed for {item.id}: {e}")
        db.commit()

    # 3. Aggregate into pivot: standard_id -> period -> value
    raw_data: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for item in items:
        if not item.standard_id or not item.period:
            continue
        existing = raw_data[item.standard_id].get(item.period)
        # If duplicate, take max absolute value (usually correct for totals)
        if existing is None or (item.value is not None and abs(item.value) > abs(existing or 0)):
            raw_data[item.standard_id][item.period] = item.value

    # 4. Derive calculated rows
    derived = _derive_rows(raw_data)
    for sid, periods_dict in derived.items():
        for period, val in periods_dict.items():
            if val is not None and raw_data[sid].get(period) is None:
                raw_data[sid][period] = val

    # 5. Compute ratios
    ratios = _compute_ratios(raw_data)

    # 6. Persist to DB
    # Delete old model entries for this project first
    db.query(FinancialModelEntry).filter(FinancialModelEntry.project_id == project_id).delete()

    for sid, periods_dict in raw_data.items():
        stmt_type = _get_statement_type(sid)
        is_der = sid in derived and any(v is not None for v in derived[sid].values())
        for period, val in periods_dict.items():
            entry = FinancialModelEntry(
                project_id=project_id,
                period=period,
                statement_type=stmt_type,
                standard_id=sid,
                standard_label=sid.replace("_", " ").title(),
                value=val,
                is_derived=is_der,
                source="llm" if (is_der and use_llm and llm_service.is_loaded()) else (
                    "calculated" if is_der else "extracted"
                ),
            )
            db.add(entry)
    db.commit()

    # 7. Build response
    all_periods = sorted({p for vals in raw_data.values() for p in vals})

    def build_table(stmt_type: str, item_ids: List[str]) -> Dict[str, Any]:
        rows = []
        for sid in item_ids:
            if sid not in raw_data:
                continue
            rows.append({
                "standard_id": sid,
                "standard_label": sid.replace("_", " ").title(),
                "values": {p: raw_data[sid].get(p) for p in all_periods},
                "is_derived": sid in derived,
                "source": "calculated" if sid in derived else "extracted",
            })
        return {
            "statement_type": stmt_type,
            "periods": all_periods,
            "rows": rows,
        }

    return {
        "project_id": project_id,
        "income_statement": build_table("income_statement", IS_ITEMS),
        "balance_sheet": build_table("balance_sheet", BS_ITEMS),
        "cash_flow": build_table("cash_flow", CF_ITEMS),
        "key_ratios": {k: dict(v) for k, v in ratios.items()},
    }
