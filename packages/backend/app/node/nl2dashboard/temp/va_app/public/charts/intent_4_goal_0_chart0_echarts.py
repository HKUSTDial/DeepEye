import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Process data to get the distribution of sales quantity across different product categories
    # Filter data for the year 2025
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Group by category and sum the quantities
    agg_data = data_2025.groupby('category')['quantity'].sum().reset_index()
    x_data = agg_data['category'].tolist()
    y_data = agg_data['quantity'].tolist()
    
    # Create a Bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Quantity", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Distribution of Sales Quantity Across Product Categories in 2025"),
            xaxis_opts=opts.AxisOpts(name="Category"),
            yaxis_opts=opts.AxisOpts(name="Quantity"),
        )
    )
    return chart