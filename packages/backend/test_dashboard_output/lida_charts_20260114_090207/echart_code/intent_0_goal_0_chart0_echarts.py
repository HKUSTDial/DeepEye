import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Convert 'ts' column to datetime
    data['ts'] = pd.to_datetime(data['ts'])
    
    # Group by date and sum 'ms_played'
    data['date'] = data['ts'].dt.date
    agg_data = data.groupby('date')['ms_played'].sum().reset_index()
    
    # Prepare data for plotting
    x_data = agg_data['date'].astype(str).tolist()
    y_data = agg_data['ms_played'].tolist()
    
    # Create Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Total Playtime (ms)", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Trend of Total Music Playtime Over Time"),
            xaxis_opts=opts.AxisOpts(type_="category", name="Date"),
            yaxis_opts=opts.AxisOpts(name="Total Playtime (ms)")
        )
    )
    return chart