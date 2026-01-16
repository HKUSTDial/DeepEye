import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ms_played' is numeric and 'platform' is a string
    data['ms_played'] = pd.to_numeric(data['ms_played'], errors='coerce')
    data['platform'] = data['platform'].astype(str)
    
    # Group by 'platform' and calculate the average 'ms_played'
    agg_data = data.groupby('platform')['ms_played'].mean().reset_index()
    x_data = agg_data['platform'].tolist()
    y_data = agg_data['ms_played'].tolist()
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Average Playtime (ms)", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Average Playtime by Platform"),
            xaxis_opts=opts.AxisOpts(name="Platform"),
            yaxis_opts=opts.AxisOpts(name="Average Playtime (ms)")
        )
    )
    return chart