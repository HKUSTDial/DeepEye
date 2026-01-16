import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Process data: Group by 'reason_end' and sum 'ms_played'
    agg_data = data.groupby('reason_end')['ms_played'].sum().reset_index()
    x_data = agg_data['reason_end'].tolist()
    y_data = agg_data['ms_played'].tolist()
    
    # Create Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Total Playtime (ms)", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Playtime by Reason Track Ended"),
            xaxis_opts=opts.AxisOpts(name="Reason End"),
            yaxis_opts=opts.AxisOpts(name="Total Playtime (ms)")
        )
    )
    return chart