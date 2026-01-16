import pandas as pd
from pyecharts.charts import Pie
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Filter data for the year 2025
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Aggregate total sales by region
    agg_data = data_2025.groupby('region')['total_amount'].sum().reset_index()
    regions = agg_data['region'].tolist()
    total_sales = agg_data['total_amount'].tolist()
    
    # Create a Pie chart
    chart = (
        Pie()
        .add(
            series_name="Total Sales",
            data_pair=[(region, sales) for region, sales in zip(regions, total_sales)],
            radius=["40%", "75%"],
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Total Sales Distribution Across Regions in 2025"),
            legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%"),
        )
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
    )
    return chart