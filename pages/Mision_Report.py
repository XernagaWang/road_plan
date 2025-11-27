import streamlit as st # type: ignore
import pandas as pd # type: ignore
import json # type: ignore
import streamlit.components.v1 as components # type: ignore
import urllib.parse
import qrcode # type: ignore
from io import BytesIO # type: ignore
import datetime # type: ignore
import os # type: ignore

# --- 页面基础设置 ---
st.set_page_config(layout="wide", page_title="On Mission")

# --- 数据加载函数 (已参数化) ---
# @st.cache_data # 暂时禁用缓存，以便在切换策略时能正确重新加载数据
def load_data(strategy_prefix):
    """根据策略前缀 (A 或 B) 加载对应的数据文件。"""
    report_file = f"report_{strategy_prefix}_enriched.csv"
    hotel_file = f"best_hotel_info_{strategy_prefix}.json"
    
    try:
        report_df = pd.read_csv(report_file)
        all_stations_df = pd.read_csv("all_map_stations.csv") # 这个文件是共享的
        with open(hotel_file, "r") as f:
            hotel_info = json.load(f)
        return report_df, all_stations_df, hotel_info
    except FileNotFoundError as e:
        st.error(f"错误：找不到文件 {e.filename}。请确保已为两个策略都生成了报告文件。")
        return None, None, None

# --- 渲染 Kepler 地图的函数 (已参数化) ---
def render_kepler_map(map_html_file):
    """读取并渲染指定的 Kepler HTML 地图文件。"""
    try:
        with open(map_html_file, 'r', encoding='utf-8') as f:
            kepler_html = f.read()
        components.html(kepler_html, height=800)
    except FileNotFoundError:
        st.error(f"错误：找不到地图文件 '{map_html_file}'。请确保已在 Jupyter Notebook 中生成该文件。")


# --- UI 界面布局 ---
selected_strategy_name = "Plan B"
strategy_prefix = "B"

# 2. 根据选择加载数据
report_df, all_stations_df, hotel_info = load_data(strategy_prefix)

if report_df is None:
    st.stop()

# 3. 页面主标题
st.title(f"Dashboard of Charging Test: {selected_strategy_name}")
st.subheader(f"Hotel: {hotel_info.get('Hotel Name', 'N/A')}")


# 4. 侧边栏的每日筛选器
st.sidebar.header("Select days")
selected_day = st.sidebar.selectbox(
    'check:',
    options=['全部'] + sorted(report_df['第幾天'].unique().tolist()),
    index=0
)

# 根据选择筛选数据
if selected_day == '全部':
    filtered_report_df = report_df
else:
    filtered_report_df = report_df[report_df['第幾天'] == selected_day]

# 5. 顶部关键指标和进度条
total_days = report_df['第幾天'].max()
total_targets = report_df['累積目標數'].max()
tested_targets = filtered_report_df['累積目標數'].max() if not filtered_report_df.empty else 0

st.header("Mission Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Days:", f"{total_days}")
col2.metric("Total Targets", f"{total_targets}")
col3.metric("Tested Targets", f"{tested_targets}")

progress_percent = int((tested_targets / total_targets) * 100) if total_targets > 0 else 0
st.progress(progress_percent, text=f"Task Completion Rate: {progress_percent}%")


# 6. 动态渲染 Kepler 地图
st.header("Mission Path Map")
map_file_to_render = f"kepler_map_strategy_{strategy_prefix}.html"
render_kepler_map(map_file_to_render)


# 7. 地图下方的电站信息表格
st.header("Detail of Each Day")


with st.expander("現場測試記錄輸入", expanded=True):
    available_rows = filtered_report_df[
        ~filtered_report_df['目的地'].astype(str).str.contains('完成測試')
    ]
    station_options = available_rows['目的地'].unique().tolist()
    if station_options:
        selected_station = st.selectbox("選擇測試站點", station_options)
        use_case_options = ["AC_UC1_17460722", "AC_UC2_7460719", "AC_UC3_17460723", "DC_UC4_17460724",  "DC_UC5_17460720", "DC_UC6_17460721"]
        selected_use_case = st.selectbox("選擇 Use Case", use_case_options)
        test_status = st.selectbox("測試狀態", ["正常測試", "無法測試"])
        
        st.markdown("#### 充電樁信息")
        cpo_name = st.text_input("CPO Name", "")
        charger_manufacturer = st.text_input("製造商", "")
        charger_model = st.text_input("MODEL", "")
        charger_voltage = st.text_input("電壓 (V)", "")
        charger_current = st.text_input("電流 (A)", "")
        charger_power = st.text_input("功率 (kW)", "")

        # 新增：開啟電裝方法（輸入框）
        # start_method = st.text_input("開啟電裝方法", "")
        # 開啟電裝方式
        start_method_options = ["掃描 QRcode", "插卡", "APP 操作", "其他"]
        selected_start_method = st.selectbox("開啟電裝方法", start_method_options)
        start_method_other = ""
        if selected_start_method == "其他":
            start_method_other = st.text_input("請輸入其他開啟方式", "")


        # 開始時間
        if "start_time" not in st.session_state:
            st.session_state["start_time"] = ""
        if st.button("紀錄開始時間"):
            st.session_state["start_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("開始時間", value=st.session_state["start_time"], disabled=True)

        # 開始電量
        start_soc = st.text_input("開始電量 (%)", "")

        # 結束時間
        if "end_time" not in st.session_state:
            st.session_state["end_time"] = ""
        if st.button("紀錄結束時間"):
            st.session_state["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("結束時間", value=st.session_state["end_time"], disabled=True)

        # 結束電量
        end_soc = st.text_input("結束電量 (%)", "")

        # 新增：結束方法（輸入框）
        # end_method = st.text_input("結束方法", "")

        

         # 結束方法
        end_method_options = ["reached target SOC", "LAT", "CID", "RFID", "APP", "Other"]
        selected_end_method = st.selectbox("結束方法", end_method_options)
        end_method_other = ""
        if selected_end_method == "Other":
            end_method_other = st.text_input("請輸入其他結束方式", "")

        # 充電結束原因
        end_reason_options = ["手動結束", "達到目標電量", "其他"]
        selected_end_reason = st.selectbox("充電結束原因", end_reason_options)
        end_reason_other = ""
        if selected_end_reason == "其他":
            end_reason_other = st.text_input("請輸入其他結束原因", "")

        # # 新增：測試結果（Pass/Failed）
        # test_result = st.selectbox("測試結果", ["Pass", "Failed"])

        # 備註放到最下方
        # remark = st.text_area("備註", "")
        # 新增：測試結果（Pass/Failed）
        test_result = st.selectbox("測試結果", ["Pass", "Failed"])

        # 新增：Error Describe
        error_describe_options = ["GBT", "Charger", "ABK", "HVS", "CCU", "LAT", "CID", "PHUD", "Other"]
        selected_error_describe = st.selectbox("Error Describe", error_describe_options)
        error_describe_other = ""
        if selected_error_describe == "Other":
            error_describe_other = st.text_input("請輸入其他 Error Describe", "")

        # 備註放到最下方
        remark = st.text_area("備註", "")


        record = {
            "日期": datetime.datetime.now().strftime("%Y-%m-%d"),
            "站點": selected_station,
            "Use Case": selected_use_case,
            "狀態": test_status,
            "CPO Name": cpo_name,
            "製造商": charger_manufacturer,
            "MODEL": charger_model,
            "電壓(V)": charger_voltage,
            "電流(A)": charger_current,
            "功率(kW)": charger_power,
            "開啟電裝方式": selected_start_method,
            "開啟電裝方式_其他說明": start_method_other,
            "開始時間": st.session_state['start_time'],
            "開始電量(%)": start_soc,
            "結束時間": st.session_state['end_time'],
            "結束電量(%)": end_soc,
            "結束方法": selected_end_method,
            "結束方法_其他說明": end_method_other,
            "測試結果": test_result,
            "Error Describe": selected_error_describe,
            "Error Describe_其他說明": error_describe_other,
            "備註": remark
        }
        # 組合顯示內容
        def display_with_other(selected, other):
            return other if selected == "其他" and other else selected

        if st.button("提交記錄"):
            record = {
                "日期": datetime.datetime.now().strftime("%Y-%m-%d"),
                "站點": selected_station,
                "Use Case": selected_use_case,
                "狀態": test_status,
                "CPO Name": cpo_name,
                "製造商": charger_manufacturer,
                "MODEL": charger_model,
                "電壓(V)": charger_voltage,
                "電流(A)": charger_current,
                "功率(kW)": charger_power,
                "開啟電裝方式": selected_start_method,
                "開啟電裝方式_其他說明": start_method_other,
                "開始時間": st.session_state['start_time'],
                "開始電量(%)": start_soc,
                "結束時間": st.session_state['end_time'],
                "結束電量(%)": end_soc,
                "結束方法": selected_end_method,
                "結束方法_其他說明": end_method_other,
                "測試結果": test_result,
                "Error Describe": selected_error_describe,
                "Error Describe_其他說明": error_describe_other,
                "備註": remark
            }
            save_file = "mission_test_records.csv"
            file_exists = os.path.isfile(save_file)
            df = pd.DataFrame([record])
            df.to_csv(save_file, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
            st.success("已保存到檔案 mission_test_records.csv！")

            if os.path.isfile("mission_test_records.csv"):
                with open("mission_test_records.csv", "rb") as f:
                    st.download_button(
                        "下載所有測試記錄 (CSV)",
                        f,
                        file_name="mission_test_records.csv",
                        mime="text/csv"
                    )
    else:
        st.info("當前沒有可選的測試站點。")

def generate_ditu_navi_link(row):
    from_name = urllib.parse.quote(str(row['出發地']))
    to_name = urllib.parse.quote(str(row['目的地']))
    from_lnglat = f"{row['出發地經度']},{row['出發地緯度']}"
    to_lnglat = f"{row['目的地經度']},{row['目的地緯度']}"
    url = (
        f"https://ditu.amap.com/dir?type=car&policy=2"
        f"&from%5Bname%5D={from_name}&from%5Blnglat%5D={from_lnglat}"
        f"&to%5Bname%5D={to_name}&to%5Blnglat%5D={to_lnglat}"
        f"&src=yourAppName"
    )
    return url

# 生成表格并为每行添加按钮
show_cols = ['第幾天', '出發地', '目的地', '導航']
table_html = "<table><tr>"
for col in show_cols:
    table_html += f"<th>{col}</th>"
table_html += "</tr>"

# 用于存储所有导航链接
navi_links = []

filtered_navi_df = filtered_report_df[
    ~filtered_report_df['目的地'].astype(str).str.contains('完成測試')
    & ~filtered_report_df['出發地'].astype(str).str.contains('完成測試')
]

for idx, row in filtered_navi_df.iterrows():
    navi_url = generate_ditu_navi_link(row)
    cols = st.columns([2, 2, 2, 1])
    cols[0].write(row['第幾天'])
    cols[1].write(f"{row['出發地']} → {row['目的地']}")
    cols[2].write("")  # 可加其它信息
    if cols[3].button("导航二维码", key=f"qr_btn_{idx}"):
        st.session_state['current_qr_url'] = navi_url

# 侧边栏显示二维码
st.sidebar.header("QR CODE OF NAVI")

if 'current_qr_url' in st.session_state:
    # 找到当前二维码对应的行，显示出發地和目的地
    current_row = None
    for idx, row in filtered_navi_df.iterrows():
        navi_url = generate_ditu_navi_link(row)
        if navi_url == st.session_state['current_qr_url']:
            current_row = row
            break
    if current_row is not None:
        st.sidebar.info(f"**{current_row['出發地']} → {current_row['目的地']}**")
    else:
        st.sidebar.info("**QRCODE OF NAVI:**")
    qr = qrcode.make(st.session_state['current_qr_url'])
    buf = BytesIO()
    qr.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="扫码导航", width="stretch")
else:
    st.sidebar.info("**QRCODE OF NAVI:**")
    st.sidebar.image("image/qrcode/qrcode_ex.png", caption="try it!")
