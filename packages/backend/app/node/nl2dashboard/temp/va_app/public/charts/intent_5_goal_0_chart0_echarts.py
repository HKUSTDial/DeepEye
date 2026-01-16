import pandas as pd
from pyecharts.charts import Scatter
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure the 'sale_date' is in datetime format
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    
    # Filter data for the year 2025
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Prepare data for the scatter plot
    x_data = data_2025['total_amount'].tolist()
    y_data = data_2025['profit'].tolist()
    
    # Create scatter plot
    scatter = (
        Scatter()
        .add_xaxis(x_data)
        .add_yaxis("Profit vs Total Amount", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Total Amount vs Profit in 2025"),
            xaxis_opts=opts.AxisOpts(type_="value", name="Total Amount"),
            yaxis_opts=opts.AxisOpts(type_="value", name="Profit"),
            tooltip_opts=opts.TooltipOpts(formatter="{b}: ({c})")
        )
    )
    return scatter