import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ts' is a datetime object
    data['ts'] = pd.to_datetime(data['ts'])
    
    # Group by date and calculate the number of skips
    data['date'] = data['ts'].dt.date
    skip_trend = data.groupby('date')['skipped'].sum().reset_index()
    
    # Prepare data for plotting
    x_data = skip_trend['date'].astype(str).tolist()
    y_data = skip_trend['skipped'].tolist()
    
    # Create a Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Number of Skips", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Trend of Track Skipping Over Time"),
            xaxis_opts=opts.AxisOpts(name="Date", type_="category"),
            yaxis_opts=opts.AxisOpts(name="Number of Skips"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross")
        )
    )
    return chart