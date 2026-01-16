import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Filter data for the year 2025
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Aggregate profit by category
    agg_data = data_2025.groupby('category')['profit'].sum().reset_index()
    x_data = agg_data['category'].tolist()
    y_data = agg_data['profit'].tolist()
    
    # Create a bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Profit", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Profit Comparison by Product Category in 2025"),
            xaxis_opts=opts.AxisOpts(name="Category"),
            yaxis_opts=opts.AxisOpts(name="Profit"),
        )
    )
    return chart