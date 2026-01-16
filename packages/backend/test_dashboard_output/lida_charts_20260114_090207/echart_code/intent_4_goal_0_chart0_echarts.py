import pandas as pd
from pyecharts.charts import Histogram
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ms_played' is treated as numeric
    data['ms_played'] = pd.to_numeric(data['ms_played'], errors='coerce')

    # 1. Prepare data
    # Create bins for the histogram
    bins = [0, 60000, 180000, 300000, 600000, 900000, 1200000, 1500000, 1800000]
    labels = ['0-1 min', '1-3 min', '3-5 min', '5-10 min', '10-15 min', '15-20 min', '20-25 min', '25-30 min']
    data['playtime_range'] = pd.cut(data['ms_played'], bins=bins, labels=labels, right=False)

    # Count the number of tracks in each bin
    agg_data = data['playtime_range'].value_counts().sort_index().reset_index()
    x_data = agg_data['index'].tolist()
    y_data = agg_data['playtime_range'].tolist()

    # 2. Create chart object
    chart = (
        Histogram()
        .add_xaxis(x_data)
        .add_yaxis("Number of Tracks", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Distribution of Playtime for Tracks"),
            xaxis_opts=opts.AxisOpts(name="Playtime Range"),
            yaxis_opts=opts.AxisOpts(name="Number of Tracks"),
        )
    )
    return chart