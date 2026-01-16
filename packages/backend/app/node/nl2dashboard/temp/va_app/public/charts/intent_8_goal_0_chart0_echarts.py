import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Filter data for the year 2025
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Aggregate total sales by product name
    agg_data = data_2025.groupby('product_name')['total_amount'].sum().reset_index()
    
    # Sort the data to get the products with the highest total sales
    agg_data = agg_data.sort_values(by='total_amount', ascending=False)
    
    # Prepare data for the chart
    x_data = agg_data['product_name'].tolist()
    y_data = agg_data['total_amount'].tolist()
    
    # Create a bar chart
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Total Sales", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Top Products by Total Sales in 2025"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="Total Sales"),
        )
    )
    return chart