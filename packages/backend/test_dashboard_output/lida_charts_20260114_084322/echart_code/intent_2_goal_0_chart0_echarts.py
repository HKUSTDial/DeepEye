import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data
    # Group by 'reason_start' and count occurrences
    reason_start_counts = data['reason_start'].value_counts().reset_index()
    reason_start_counts.columns = ['reason_start', 'count']
    
    # Extract x and y data
    x_data = reason_start_counts['reason_start'].tolist()
    y_data = reason_start_counts['count'].tolist()
    
    # 2. Create chart object
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Count", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Most Common Reasons for Starting a Track"),
            xaxis_opts=opts.AxisOpts(name="Reason Start"),
            yaxis_opts=opts.AxisOpts(name="Count"),
            toolbox_opts=opts.ToolboxOpts(),
            datazoom_opts=opts.DataZoomOpts()
        )
    )
    return chart