import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Process data to find correlation between shuffle mode and track skipping
    # Group by shuffle and skipped, then count occurrences
    agg_data = data.groupby(['shuffle', 'skipped']).size().reset_index(name='count')
    
    # Prepare data for visualization
    shuffle_modes = agg_data['shuffle'].map({True: 'Shuffle On', False: 'Shuffle Off'}).tolist()
    skip_status = agg_data['skipped'].map({True: 'Skipped', False: 'Not Skipped'}).tolist()
    counts = agg_data['count'].tolist()
    
    # Create chart object
    chart = (
        Bar()
        .add_xaxis(shuffle_modes)
        .add_yaxis("Skipped Status", counts, stack="stack1", category_gap="50%")
        .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Correlation between Shuffle Mode and Track Skipping"),
            xaxis_opts=opts.AxisOpts(name="Shuffle Mode"),
            yaxis_opts=opts.AxisOpts(name="Count"),
            legend_opts=opts.LegendOpts(pos_left="right")
        )
    )
    return chart