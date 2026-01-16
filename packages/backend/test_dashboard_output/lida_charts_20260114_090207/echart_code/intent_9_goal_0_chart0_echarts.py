import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Process data to find the most frequently played tracks
    track_counts = data['track_name'].value_counts().reset_index()
    track_counts.columns = ['track_name', 'play_count']
    
    # Select top 10 most frequently played tracks
    top_tracks = track_counts.head(10)
    x_data = top_tracks['track_name'].tolist()
    y_data = top_tracks['play_count'].tolist()
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Play Count", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Top 10 Most Frequently Played Tracks"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="Play Count"),
        )
    )
    return chart