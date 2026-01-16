import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'sale_date' is in datetime format
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    
    # Extract year and month from 'sale_date'
    data['year_month'] = data['sale_date'].dt.to_period('M')
    
    # Filter data for the year 2025
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Group by 'year_month' and calculate the average 'cost_price'
    monthly_avg_cost = data_2025.groupby('year_month')['cost_price'].mean().reset_index()
    
    # Convert 'year_month' to string for plotting
    monthly_avg_cost['year_month'] = monthly_avg_cost['year_month'].astype(str)
    
    # Prepare data for plotting
    x_data = monthly_avg_cost['year_month'].tolist()
    y_data = monthly_avg_cost['cost_price'].tolist()
    
    # Create Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Average Cost Price", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Trend of Average Product Cost Price by Month in 2025"),
            xaxis_opts=opts.AxisOpts(name="Month"),
            yaxis_opts=opts.AxisOpts(name="Average Cost Price"),
        )
    )
    return chart