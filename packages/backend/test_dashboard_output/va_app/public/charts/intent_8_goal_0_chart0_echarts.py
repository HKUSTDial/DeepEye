import pandas as pd
from pyecharts.charts import Pie
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # 1. Prepare data
    reason_end_counts = data['reason_end'].value_counts().reset_index()
    reason_end_counts.columns = ['reason_end', 'count']
    x_data = reason_end_counts['reason_end'].tolist()
    y_data = reason_end_counts['count'].tolist()
    
    # 2. Create chart object
    chart = (
        Pie()
        .add(
            series_name="Reasons for Ending Track",
            data_pair=[(x, y) for x, y in zip(x_data, y_data)],
            radius=["40%", "75%"],
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Most Common Reasons for Ending a Track"),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%"),
        )
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    return chart