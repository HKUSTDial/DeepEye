import pandas as pd
from pyecharts.charts import Line
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Ensure 'sale_date' is in datetime format
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    
    # Filter data for the year 2025
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Extract month and count transactions
    data_2025['month'] = data_2025['sale_date'].dt.to_period('M')
    monthly_transactions = data_2025.groupby('month').size().reset_index(name='transaction_count')
    
    # Prepare data for plotting
    x_data = monthly_transactions['month'].astype(str).tolist()
    y_data = monthly_transactions['transaction_count'].tolist()
    
    # Create Line chart
    chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("Number of Transactions", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Monthly Trend of Transactions in 2025"),
            xaxis_opts=opts.AxisOpts(name="Month"),
            yaxis_opts=opts.AxisOpts(name="Number of Transactions"),
        )
    )
    return chart