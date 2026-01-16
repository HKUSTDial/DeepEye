import pandas as pd
from pyecharts.charts import Pie
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data
    platform_counts = data['platform'].value_counts().reset_index()
    platform_counts.columns = ['platform', 'count']
    x_data = platform_counts['platform'].tolist()
    y_data = platform_counts['count'].tolist()
    
    # 2. Create chart object
    chart = (
        Pie()
        .add("", [list(z) for z in zip(x_data, y_data)])
        .set_global_opts(title_opts=opts.TitleOpts(title="Platform Usage for Music Playback"))
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    return chart