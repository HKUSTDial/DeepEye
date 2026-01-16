import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ts' is in datetime format
    data['ts'] = pd.to_datetime(data['ts'])
    
    # Extract date from timestamp for daily aggregation
    data['date'] = data['ts'].dt.date
    
    # Group by date and calculate the number of skipped tracks per day
    daily_skips = data[data['skipped']].groupby('date').size().reset_index(name='skips')
    
    # Prepare data for plotting
    x_data = daily_skips['date'].astype(str).tolist()
    y_data = daily_skips['skips'].tolist()
    
    # Create a Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Skipped Tracks", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Trend of Track Skipping Over Time"),
            xaxis_opts=opts.AxisOpts(name="Date", type_="category"),
            yaxis_opts=opts.AxisOpts(name="Number of Skips"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross")
        )
    )
    return chart