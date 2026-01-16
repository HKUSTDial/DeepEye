from pyecharts import options as opts
from pyecharts.charts import Bar
import pandas as pd

def plot(data: pd.DataFrame) -> Bar:
    """Plot sales volume by day of the week using pyecharts Bar chart.
    
    Args:
        data: A pandas DataFrame containing transaction data with columns 'transaction_date' and 'transaction_qty'.
    
    Returns:
        Bar: The ECharts Bar chart object representing sales volume by day of the week.
    """
    
    # Convert transaction_date to datetime
    data['transaction_date'] = pd.to_datetime(data['transaction_date'], errors='coerce')
    data = data[pd.notna(data['transaction_date'])]
    
    # Extract day of the week
    data['day_of_week'] = data['transaction_date'].dt.day_name()
    
    # Aggregate sales volume by day of the week
    sales_by_day = data.groupby('day_of_week')['transaction_qty'].sum().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    )
    
    # Create Bar chart
    chart = Bar()
    chart.add_xaxis(sales_by_day.index.tolist())
    chart.add_yaxis("Total Sales Volume", sales_by_day.values.tolist(), color='skyblue')
    
    chart.set_global_opts(
        title_opts=opts.TitleOpts(
            title="Which days of the week have the highest sales volume?",
            pos_top="5%"
        ),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        xaxis_opts=opts.AxisOpts(
            type_="category",
            name="Day of the Week",
            name_location="center",
            name_gap=35,
            axislabel_opts=opts.LabelOpts(rotate=45, margin=20)
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value", 
            name="Total Sales Volume",
            name_location="center",
            name_gap=45
        ),
        legend_opts=opts.LegendOpts(pos_top="15%")
    )
    
    return chart