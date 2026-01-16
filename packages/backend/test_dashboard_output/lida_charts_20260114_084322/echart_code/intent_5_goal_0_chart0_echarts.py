import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data: Group by 'artist_name' and sum 'ms_played'
    agg_data = data.groupby('artist_name')['ms_played'].sum().reset_index()
    
    # Sort the data to get the top artists by playtime
    agg_data = agg_data.sort_values(by='ms_played', ascending=False).head(10)
    
    # Extract x and y data
    x_data = agg_data['artist_name'].tolist()
    y_data = agg_data['ms_played'].tolist()
    
    # 2. Create chart object
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Total Playtime (ms)", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Top 10 Artists by Total Playtime"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="Total Playtime (ms)"),
        )
    )
    return chart