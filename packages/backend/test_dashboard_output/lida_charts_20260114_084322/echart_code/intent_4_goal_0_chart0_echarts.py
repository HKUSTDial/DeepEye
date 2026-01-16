import pandas as pd
from pyecharts.charts import Boxplot
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'ms_played' is numeric
    data['ms_played'] = pd.to_numeric(data['ms_played'], errors='coerce')
    
    # Filter data for skipped and not skipped
    skipped_data = data[data['skipped'] == True]['ms_played'].dropna().tolist()
    not_skipped_data = data[data['skipped'] == False]['ms_played'].dropna().tolist()
    
    # Prepare data for boxplot
    boxplot_data = [skipped_data, not_skipped_data]
    categories = ['Skipped', 'Not Skipped']
    
    # Create boxplot
    boxplot = (
        Boxplot()
        .add_xaxis(categories)
        .add_yaxis("Playtime Distribution", boxplot.prepare_data(boxplot_data))
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Distribution of Playtime for Skipped vs Not Skipped Tracks"),
            yaxis_opts=opts.AxisOpts(name="Milliseconds Played"),
            xaxis_opts=opts.AxisOpts(name="Track Skipped Status")
        )
    )
    
    return boxplot