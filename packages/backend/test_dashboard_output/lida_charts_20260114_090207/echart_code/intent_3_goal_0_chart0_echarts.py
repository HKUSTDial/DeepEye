import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure the 'shuffle' and 'skipped' columns are of boolean type
    data['shuffle'] = data['shuffle'].astype(bool)
    data['skipped'] = data['skipped'].astype(bool)
    
    # Group by 'shuffle' and calculate the mean of 'skipped' to find the likelihood of skipping
    agg_data = data.groupby('shuffle')['skipped'].mean().reset_index()
    x_data = agg_data['shuffle'].map({True: 'Shuffle On', False: 'Shuffle Off'}).tolist()
    y_data = (agg_data['skipped'] * 100).tolist()  # Convert to percentage
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Skip Percentage", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Effect of Shuffle Mode on Track Skipping"),
            yaxis_opts=opts.AxisOpts(name="Skip Percentage", axislabel_opts=opts.LabelOpts(formatter="{value}%")),
            xaxis_opts=opts.AxisOpts(name="Shuffle Mode")
        )
    )
    return chart