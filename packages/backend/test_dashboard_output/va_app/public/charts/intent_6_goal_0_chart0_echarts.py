import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ts' is in datetime format
    data['ts'] = pd.to_datetime(data['ts'])
    
    # Group by date and calculate the mean of 'skipped' to get the skipping trend
    data['date'] = data['ts'].dt.date
    skip_trend = data.groupby('date')['skipped'].mean().reset_index()
    
    # Prepare data for plotting
    x_data = skip_trend['date'].astype(str).tolist()
    y_data = skip_trend['skipped'].tolist()
    
    # Create a Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Skipping Trend", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Trend of Track Skipping Over Time"),
            xaxis_opts=opts.AxisOpts(name="Date", type_="category"),
            yaxis_opts=opts.AxisOpts(name="Skipping Rate", type_="value"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", formatter="{b}: {c}"),
        )
    )
    return chart