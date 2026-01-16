import pandas as pd
from pyecharts.charts import Pie
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Filter data for the year 2025
    data['sale_date'] = pd.to_datetime(data['sale_date'])
    data_2025 = data[data['sale_date'].dt.year == 2025]
    
    # Group by sentiment_label to get the distribution
    sentiment_distribution = data_2025['sentiment_label'].value_counts().reset_index()
    sentiment_distribution.columns = ['sentiment_label', 'count']
    
    # Prepare data for the pie chart
    data_pairs = [list(z) for z in zip(sentiment_distribution['sentiment_label'], sentiment_distribution['count'])]
    
    # Create pie chart
    pie_chart = (
        Pie()
        .add("", data_pairs)
        .set_global_opts(title_opts=opts.TitleOpts(title="Sentiment Distribution of Customer Comments in 2025"))
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    
    return pie_chart