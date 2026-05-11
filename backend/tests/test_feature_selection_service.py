import pandas as pd

from app.services.feature_selection_service import compute_feature_scores, select_top_features


def _profile_for_columns(columns: list[str]) -> list[dict[str, object]]:
    profile: list[dict[str, object]] = []
    for column in columns:
        if column in {"x", "y", "superficie_total", "superficie_afectada", "variable"}:
            semantic_type = "metric"
            is_metric = True
        elif column == "constant_metric":
            semantic_type = "constant"
            is_metric = False
        else:
            semantic_type = "categorical"
            is_metric = False
        profile.append(
            {
                "display_name": column,
                "sql_name": column,
                "semantic_type": semantic_type,
                "is_metric": is_metric,
                "usable_for_correlation": is_metric,
                "usable_for_grouping": semantic_type == "categorical",
            }
        )
    return profile


def test_compute_feature_scores_gives_zero_to_constant_columns():
    dataframe = pd.DataFrame(
        {
            "constant_metric": [5, 5, 5, 5, 5],
            "variable": [1, 2, 3, 4, 5],
        }
    )
    scores = compute_feature_scores(dataframe, _profile_for_columns(list(dataframe.columns)))
    score_by_column = {item.column: item for item in scores}

    assert score_by_column["constant_metric"].final_score == 0.0
    assert score_by_column["variable"].final_score > 0.0


def test_compute_feature_scores_rewards_correlated_numeric_columns():
    dataframe = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6],
            "y": [2, 4, 6, 8, 10, 12],
            "constant_metric": [1, 1, 1, 1, 1, 1],
        }
    )
    scores = compute_feature_scores(dataframe, _profile_for_columns(list(dataframe.columns)))
    score_by_column = {item.column: item for item in scores}

    assert score_by_column["x"].correlation_strength > 0.9
    assert score_by_column["y"].correlation_strength > 0.9
    assert score_by_column["x"].final_score > score_by_column["constant_metric"].final_score


def test_compute_feature_scores_distinguishes_categorical_entropy():
    dataframe = pd.DataFrame(
        {
            "low_entropy_category": ["A", "A", "A", "A", "B", "A"],
            "high_entropy_category": ["A", "B", "C", "D", "E", "F"],
        }
    )
    scores = compute_feature_scores(dataframe, _profile_for_columns(list(dataframe.columns)))
    score_by_column = {item.column: item for item in scores}

    assert score_by_column["high_entropy_category"].entropy > score_by_column["low_entropy_category"].entropy
    assert score_by_column["high_entropy_category"].final_score >= score_by_column["low_entropy_category"].final_score


def test_select_top_features_returns_highest_ranked_columns():
    dataframe = pd.DataFrame(
        {
            "superficie_total": [10, 20, 30, 40, 50],
            "superficie_afectada": [5, 10, 15, 20, 25],
            "low_entropy_category": ["A", "A", "A", "A", "B"],
        }
    )
    scores = compute_feature_scores(dataframe, _profile_for_columns(list(dataframe.columns)))
    top_features = select_top_features(scores, k=2)

    assert len(top_features) == 2
    assert top_features[0].final_score >= top_features[1].final_score
