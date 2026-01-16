import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Convert 'sale_date' to datetime to filter by year
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    
    # Filter data for the year 2025
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Group by 'region' and calculate the average 'rating'
    agg_data = data_2025.groupby('region')['rating'].mean().reset_index()
    
    # Prepare data for the chart
    x_data = agg_data['region'].tolist()
    y_data = agg_data['rating'].tolist()
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Average Rating", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Average Product Rating by Region in 2025"),
            xaxis_opts=opts.AxisOpts(name="Region"),
            yaxis_opts=opts.AxisOpts(name="Average Rating"),
        )
    )
    return chart