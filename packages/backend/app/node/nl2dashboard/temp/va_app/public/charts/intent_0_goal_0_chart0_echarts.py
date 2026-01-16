import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'sale_date' is in datetime format
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    
    # Filter data for the year 2025
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Extract month and calculate total revenue per month
    data_2025['month'] = data_2025['sale_date'].dt.to_period('M')
    monthly_revenue = data_2025.groupby('month')['total_amount'].sum().reset_index()
    
    # Convert month to string for x-axis
    x_data = monthly_revenue['month'].astype(str).tolist()
    y_data = monthly_revenue['total_amount'].tolist()
    
    # Create Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Total Revenue", y_data, is_smooth=True)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Total Revenue Trend by Month in 2025"),
            xaxis_opts=opts.AxisOpts(name="Month"),
            yaxis_opts=opts.AxisOpts(name="Total Revenue"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross")
        )
    )
    return chart