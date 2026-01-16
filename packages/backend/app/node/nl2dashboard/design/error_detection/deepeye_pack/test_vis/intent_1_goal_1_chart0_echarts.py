from pyecharts import options as opts
from pyecharts.charts import Bar
import pandas as pd
import numpy as np

def plot(data: pd.DataFrame) -> Bar:
    """Plot a stacked bar chart showing the impact of product category on sales quantities during high sales days.
    
    Args:
        data: A DataFrame containing transaction data with columns 'transaction_date', 'product_category', and 'transaction_qty'.
    
    Returns:
        Bar: The ECharts Bar chart object
    """
    
    # Convert transaction_date to datetime and filter out invalid dates
    data['transaction_date'] = pd.to_datetime(data['transaction_date'], errors='coerce')
    data = data.dropna(subset=['transaction_date'])
    
    # Group by transaction_date and product_category, summing transaction_qty
    grouped_data = data.groupby(['transaction_date', 'product_category'])['transaction_qty'].sum().unstack(fill_value=0)
    
    # Identify high sales days (e.g., top 10% of sales days)
    total_sales_per_day = grouped_data.sum(axis=1)
    threshold = np.percentile(total_sales_per_day, 90)
    high_sales_days = total_sales_per_day[total_sales_per_day >= threshold].index
    
    # Filter for high sales days
    high_sales_data = grouped_data.loc[high_sales_days]
    
    # Create Bar chart
    chart = Bar()
    chart.add_xaxis(high_sales_data.index.strftime('%Y-%m-%d').tolist())
    
    # Add data for each product category
    for category in high_sales_data.columns:
        chart.add_yaxis(category, high_sales_data[category].tolist(), stack="stack1")
    
    # Set global options for the chart
    chart.set_global_opts(
        title_opts=opts.TitleOpts(
            title="Impact of Product Category on Sales Quantities During High Sales Days",
            pos_top="5%",
            title_textstyle_opts=opts.TextStyleOpts(font_size=16, font_weight='bold')
        ),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
        xaxis_opts=opts.AxisOpts(
            type_="category",
            name="Transaction Date",
            name_location="center",
            name_gap=35,
            axislabel_opts=opts.LabelOpts(rotate=45, margin=20)
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value", 
            name="Total Quantity Sold",
            name_location="center",
            name_gap=45
        ),
        legend_opts=opts.LegendOpts(pos_top="15%")
    )
    
    return chart