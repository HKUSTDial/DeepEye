import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data
    platform_counts = data['platform'].value_counts().reset_index()
    platform_counts.columns = ['platform', 'count']
    x_data = platform_counts['platform'].tolist()
    y_data = platform_counts['count'].tolist()
    
    # 2. Create chart object
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Usage Count", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Most Frequently Used Platforms for Music Playback"),
            xaxis_opts=opts.AxisOpts(name="Platform"),
            yaxis_opts=opts.AxisOpts(name="Count"),
        )
    )
    return chart