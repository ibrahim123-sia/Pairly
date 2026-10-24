from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_store
from app.models import Store
from app.services import analytics_service, cache_service, dataset_service, insights_service, mba_service
from app.utils.filters import apply_filters, extract_filters_from_args

router = APIRouter()


def _df_or_error(db: Session, store: Store):
    df, dataset = dataset_service.get_active_dataframe(db, store)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active dataset for this store. Upload data first."
        )
    return df, dataset


@router.get("/health")
def health(
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    return {
        "status": "healthy",
        "store_id": current_store.id,
        "dataset_id": dataset.id if dataset else None,
        "data_records": int(len(df)),
        "transactions": int(df["InvoiceNo"].nunique()) if "InvoiceNo" in df.columns else 0,
        "products": int(df["Description"].nunique()) if "Description" in df.columns else 0,
        "total_revenue": float(df["TotalAmount"].sum()) if "TotalAmount" in df.columns else 0,
        "available_columns": list(df.columns),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/summary")
def summary(
    request: Request,
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    key = cache_service.make_key(current_store.id, dataset.id, "summary", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_summary(df))
    return {"success": True, "data": data, "timestamp": datetime.utcnow().isoformat()}


@router.get("/association_rules")
def association_rules_route(
    request: Request,
    min_support: float = Query(0.01),
    min_confidence: float = Query(0.3),
    min_lift: float = Query(1.0),
    limit: int = Query(50),
    simple: bool = Query(True),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    filters = extract_filters_from_args(dict(request.query_params))
    filtered = apply_filters(df, filters)

    min_support_val = max(0.001, min_support)
    min_confidence_val = max(0.1, min_confidence)
    min_lift_val = max(0.5, min_lift)
    limit_val = min(100, max(1, limit))

    key = cache_service.make_key(current_store.id, dataset.id, "association_rules", dict(request.query_params))
    result = cache_service.get_or_set(
        key,
        lambda: mba_service.compute_association_rules(filtered, min_support_val, min_confidence_val, min_lift_val, limit_val, simple),
    )
    return result


@router.get("/product_bundles_filtered")
def product_bundles(
    request: Request,
    min_support: float = Query(0.01),
    min_confidence: float = Query(0.3),
    min_lift: float = Query(1.0),
    limit: int = Query(50),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    filters = extract_filters_from_args(dict(request.query_params))
    filtered = apply_filters(df, filters)

    min_support_val = max(0.001, min_support)
    min_confidence_val = max(0.1, min_confidence)
    min_lift_val = max(0.5, min_lift)
    limit_val = min(100, max(1, limit))

    key = cache_service.make_key(current_store.id, dataset.id, "product_bundles_filtered", dict(request.query_params))
    result = cache_service.get_or_set(
        key,
        lambda: mba_service.compute_product_bundles(filtered, min_support_val, min_confidence_val, min_lift_val, limit_val, filters),
    )
    return result


@router.get("/seasonal_data")
def seasonal_data(
    request: Request,
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    key = cache_service.make_key(current_store.id, dataset.id, "seasonal_data", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_seasonal(df))
    return {"success": True, **data}


@router.get("/seasonal_product_analysis")
def seasonal_product_analysis(
    request: Request,
    product: str = Query(""),
    year: str = Query("all"),
    month: str = Query("all"),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    product_val = product.strip()
    key = cache_service.make_key(current_store.id, dataset.id, "seasonal_product", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_seasonal_product(df, product_val, year, month))
    return {"success": True, **data}


@router.get("/revenue_by_country")
def revenue_by_country(
    request: Request,
    country: str = Query("all"),
    year: str = Query("all"),
    limit: int = Query(10),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    limit_val = min(50, max(1, limit))
    key = cache_service.make_key(current_store.id, dataset.id, "revenue_by_country", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_revenue_by_country(df, country, year, limit_val))
    return {"success": True, **data}


@router.get("/frequent_itemsets")
def frequent_itemsets(
    request: Request,
    min_support: float = Query(0.02),
    limit: int = Query(20),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    min_support_val = max(0.001, min_support)
    limit_val = min(100, max(5, limit))
    key = cache_service.make_key(current_store.id, dataset.id, "frequent_itemsets", dict(request.query_params))
    result = cache_service.get_or_set(key, lambda: mba_service.compute_network_graph(df, min_support_val, limit_val))
    return result


@router.get("/top_products")
def top_products(
    request: Request,
    sort_by: str = Query("revenue"),
    limit: int = Query(20),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    filters = extract_filters_from_args(dict(request.query_params))
    filtered = apply_filters(df, filters)
    limit_val = min(100, max(1, limit))
    key = cache_service.make_key(current_store.id, dataset.id, "top_products", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_top_products(filtered, sort_by, limit_val))
    return {"success": True, **data}


@router.get("/filters")
def filters(
    request: Request,
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    key = cache_service.make_key(current_store.id, dataset.id, "filters", dict(request.query_params))
    data = cache_service.get_or_set(key, lambda: analytics_service.compute_filters(df))
    return {"success": True, "filters": data, "timestamp": datetime.utcnow().isoformat()}


@router.get("/recommendations")
def recommendations(
    request: Request,
    product: str = Query(""),
    limit: int = Query(10),
    min_co_occurrence: int = Query(3),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    product_val = product.strip()
    limit_val = min(50, max(1, limit))
    min_co = max(1, min_co_occurrence)
    key = cache_service.make_key(current_store.id, dataset.id, "recommendations", dict(request.query_params))
    result = cache_service.get_or_set(
        key, lambda: insights_service.compute_recommendations(df, product_val or None, limit_val, min_co)
    )
    return {"success": True, **result}


@router.get("/customer_segments")
def customer_segments(
    request: Request,
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    key = cache_service.make_key(current_store.id, dataset.id, "customer_segments", dict(request.query_params))
    result = cache_service.get_or_set(key, lambda: insights_service.compute_rfm(df))
    return {"success": True, **result}


@router.get("/period_comparison")
def period_comparison(
    request: Request,
    period_days: int = Query(30),
    end_date: Optional[str] = Query(None),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    period_days_val = min(365, max(1, period_days))
    key = cache_service.make_key(current_store.id, dataset.id, "period_comparison", dict(request.query_params))
    result = cache_service.get_or_set(
        key, lambda: insights_service.compute_period_comparison(df, period_days_val, end_date)
    )
    return {"success": True, **result}


@router.get("/cohort_retention")
def cohort_retention(
    request: Request,
    max_periods: int = Query(12),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    max_periods_val = min(24, max(3, max_periods))
    key = cache_service.make_key(current_store.id, dataset.id, "cohort_retention", dict(request.query_params))
    result = cache_service.get_or_set(key, lambda: insights_service.compute_cohort_retention(df, max_periods_val))
    return {"success": True, **result}


@router.post("/bundle_simulator")
async def bundle_simulator(
    request: Request,
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    try:
        data = await request.json()
    except Exception:
        data = {}
    products = data.get("products") or []
    discount_pct = float(data.get("discount_pct", 10.0))
    result = insights_service.simulate_bundle(df, products, discount_pct)
    return {"success": "error" not in result, **result}


@router.get("/product_stats")
def product_stats(
    request: Request,
    product: str = Query(""),
    current_store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    df, dataset = _df_or_error(db, current_store)
    product_name = product.strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="Product name is required")

    filters_dict = extract_filters_from_args(dict(request.query_params))
    filtered = apply_filters(df, filters_dict)
    if len(filtered) == 0:
        raise HTTPException(status_code=404, detail="No data available with current filters")

    result = analytics_service.compute_product_detail(filtered, product_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Product '{product_name}' not found")
    result["metadata"]["filters_applied"] = filters_dict
    return {"success": True, "product": result}
