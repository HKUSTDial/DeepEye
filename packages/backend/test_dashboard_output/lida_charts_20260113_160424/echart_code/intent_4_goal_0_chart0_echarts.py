import pandas as pd
from pyecharts.charts import Histogram
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ms_played' is treated as numeric
    data['ms_played'] = pd.to_numeric(data['ms_played'], errors='coerce')

    # 1. Prepare data
    # We will use the 'ms_played' column to create a histogram
    playtime_data = data['ms_played'].dropna().tolist()

    # 2. Create chart object
    chart = (
        Histogram()
        .add_xaxis(playtime_data)
        .add_yaxis("Playtime Distribution", playtime_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Distribution of Playtime for Tracks"),
            xaxis_opts=opts.AxisOpts(name="Milliseconds Played"),
            yaxis_opts=opts.AxisOpts(name="Frequency"),
            datazoom_opts=[opts.DataZoomOpts()]
        )
    )
    return chart