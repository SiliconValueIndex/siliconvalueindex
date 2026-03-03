import pandas as pd
from src.scoring import compute_cost_per_fps

def test_cost_per_fps_basic():
    df = pd.DataFrame([{
        "gpu_model": "RTX 5090",
        "avg_fps_1440p": 100,
        "new_price": 500,
        "used_price": 400,
    }])
    out = compute_cost_per_fps(df)
    assert out.loc[0, "new_cost_per_fps"] == 5
    assert out.loc[0, "used_cost_per_fps"] == 4