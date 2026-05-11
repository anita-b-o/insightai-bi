from app.services.sql_analysis_service import analyze_sql


def test_detects_sum_group_by():
    result = analyze_sql("SELECT product, SUM(revenue) AS total_revenue FROM sales GROUP BY product")

    assert result.is_aggregated is True
    assert result.aggregation_functions == ["SUM"]
    assert result.group_by_columns == ["product"]
    assert result.selected_columns == ["product", "total_revenue"]
    assert result.has_group_by is True


def test_detects_count_group_by_temporal():
    result = analyze_sql("SELECT date, COUNT(*) FROM orders GROUP BY date")

    assert result.is_aggregated is True
    assert result.aggregation_functions == ["COUNT"]
    assert result.group_by_columns == ["date"]
    assert result.selected_columns == ["date", "COUNT(*)"]


def test_detects_raw_select_with_limit():
    result = analyze_sql("SELECT * FROM sales LIMIT 100")

    assert result.is_aggregated is False
    assert result.aggregation_functions == []
    assert result.group_by_columns == []
    assert result.selected_columns == ["*"]
    assert result.has_limit is True


def test_detects_raw_select_without_aggregation():
    result = analyze_sql("SELECT product_name, revenue FROM sales")

    assert result.is_aggregated is False
    assert result.selected_columns == ["product_name", "revenue"]
    assert result.has_group_by is False


def test_detects_alias_and_lowercase_sql():
    result = analyze_sql("select product, sum(revenue) as total_revenue from sales group by product order by total_revenue desc")

    assert result.is_aggregated is True
    assert result.aggregation_functions == ["SUM"]
    assert result.selected_columns == ["product", "total_revenue"]
    assert result.has_order_by is True
