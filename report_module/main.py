# main.py
import config
from pipeline import AutoReportPipeline
import traceback

# ==========================================
# User Configurations / Inputs
# ==========================================
#CSV_FILES = ["sales.csv", "customer_feedback.csv", "products.csv"]
CSV_FILES = ["insurance.csv"]         # 输入文件名
USER_QUERY = "Generate a comprehensive report."   # 用户查询
TEMPLATE_NAME = "template_1.html"       # 指定模板: template_0.html 或 template_1.html
OUTPUT_FILE = "final_report2.html"       # 输出文件名

if __name__ == "__main__":
    # Initialize Pipeline
    pipeline = AutoReportPipeline(api_key=config.API_KEY, base_url=config.BASE_URL)

    print(f"🏁 Starting Report Generation using {TEMPLATE_NAME}...")

    try:
        pipeline.run(
            csv_paths=CSV_FILES,
            user_query=USER_QUERY,
            output_file=OUTPUT_FILE,
            template_name=TEMPLATE_NAME
        )
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        traceback.print_exc()