import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data: Group by 'platform' and sum 'ms_played'
    agg_data = data.groupby('platform')['ms_played'].sum().reset_index()
    x_data = agg_data['platform'].tolist()
    y_data = agg_data['ms_played'].tolist()
    
    # 2. Create chart object
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Total Playtime (ms)", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Total Playtime by Platform"),
            xaxis_opts=opts.AxisOpts(name="Platform"),
            yaxis_opts=opts.AxisOpts(name="Total Playtime (ms)")
        )
    )
    return chart