import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure the 'shuffle' and 'skipped' columns are of boolean type
    data['shuffle'] = data['shuffle'].astype(bool)
    data['skipped'] = data['skipped'].astype(bool)
    
    # Group by 'shuffle' and 'skipped' to count occurrences
    agg_data = data.groupby(['shuffle', 'skipped']).size().unstack(fill_value=0)
    
    # Prepare data for plotting
    x_data = ['Not Skipped', 'Skipped']
    y_data_shuffle_on = agg_data.loc[True].tolist()
    y_data_shuffle_off = agg_data.loc[False].tolist()
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Shuffle On", y_data_shuffle_on)
        .add_yaxis("Shuffle Off", y_data_shuffle_off)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Effect of Shuffle Mode on Track Skipping"),
            xaxis_opts=opts.AxisOpts(name="Skipped Status"),
            yaxis_opts=opts.AxisOpts(name="Count"),
            legend_opts=opts.LegendOpts(pos_top="5%")
        )
    )
    return chart