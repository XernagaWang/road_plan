import streamlit as st # type: ignore
import pandas as pd # type: ignore
import numpy as np # type: ignore
from streamlit_folium import st_folium # type: ignore
import folium # type: ignore
import plotly.express as px # type: ignore



# --- 页面基础设置 ---
st.set_page_config(
    layout="wide",
    page_title="ROAD PLAN",
)

# --- 数据加载 ---
@st.cache_data
def load_data():
    """加载所有需要的数据文件"""
    try:
        plan_d_stations = pd.read_csv("datasets/stations_D_gz.csv")
        national_stations = pd.read_csv("datasets/national_charge_station.csv")
        return plan_d_stations, national_stations
    except FileNotFoundError as e:
        st.error(f"❌ 错误：找不到数据文件 {e.filename}。请确保相关数据文件已准备就绪。")
        return None, None
    except KeyError:
        st.error("❌ 错误: 'stations_D_gz.csv' 文件中缺少 'power_type_final' 列。请返回Jupyter Notebook，运行预处理单元格并重新保存文件。")
        return None, None

stations_df, national_stations_df = load_data()

if stations_df is None or national_stations_df is None:
    st.stop()

# --- 核心参数定义 ---
PRIMARY_CPO_LIST = [
    "国家电网", "小桔充电", "南网电动", "蔚景云", 
    "星星充电", "云快充", "依威能源", "特来电", "逸安启"
]
FRIENDLY_BRANDS_OEM = [
    "比亚迪", "小米", "蔚来", "理想", "特斯拉", "小鹏", "广汽", "路特斯"
]
ESTIMATED_DAYS = 8
HOTEL_LOCATION = {
    "name": "广州 W 酒店",
    "latitude": 23.121988,
    "longitude": 113.328508
}

# --- 数据分析与分类 (已修改) ---
total_tasks = len(stations_df)

# CPO 分类逻辑
def classify_cpo_category(row):
    if pd.notna(row['brand_keyword']) and row['brand_keyword'] in FRIENDLY_BRANDS_OEM:
        return "友商品牌 (OEM)"
    elif row['operator_name'] in PRIMARY_CPO_LIST:
        return "主要品牌 (Primary CPO)"
    else:
        return "当地品牌 (Local CPO)"

stations_df['cpo_category'] = stations_df.apply(classify_cpo_category, axis=1)
category_counts = stations_df['cpo_category'].value_counts()

# --- 新增：CPO 覆盖率深度分析 ---
total_cpos_in_plan = stations_df['operator_name'].nunique()
total_national_cpos = national_stations_df['operator_name'].nunique()
# 筛选广州市的CPO
gz_cpos_df = national_stations_df[national_stations_df['city'] == '广州市']
total_gz_cpos = gz_cpos_df['operator_name'].nunique()
# 计算比例
gz_vs_national_percentage = (total_gz_cpos / total_national_cpos * 100) if total_national_cpos > 0 else 0
mission_vs_gz_percentage = (total_cpos_in_plan / total_gz_cpos * 100) if total_gz_cpos > 0 else 0


# 功率类型分析
power_counts = stations_df['power_type_final'].value_counts()
ac_count = power_counts.get('AC', 0)
dc_count = power_counts.get('DC', 0)
unknown_count = power_counts.get('Unknown', 0)
known_power_total = ac_count + dc_count
ac_percentage = (ac_count / known_power_total * 100) if known_power_total > 0 else 0
dc_percentage = (dc_count / known_power_total * 100) if known_power_total > 0 else 0

# --- UI 界面 (已修改) ---
st.title("Cross Country: G70 LCI I460")
st.markdown("### Mission Area: **Guangzhou**")
st.markdown("Your mission, should you choose to accept it, involves the following key intelligence:")
st.divider()

# 核心指标
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Test Targets (Stations)", value=total_tasks)
with col2:
    st.metric(label="Estimated Mission Duration", value=f"{ESTIMATED_DAYS} Days")

# --- 新增：CPO覆盖分析模块 ---
st.subheader("CPO Coverage Analysis")
cpo_col1, cpo_col2 = st.columns(2)
with cpo_col1:
    st.metric(
        label="Guangzhou CPOs vs. National",
        value=f"{total_gz_cpos} / {total_national_cpos}",
        help=f"广州市共有 {total_gz_cpos} 个充电运营商，占全国总数 ({total_national_cpos}) 的 **{gz_vs_national_percentage:.2f}%**。"
    )
with cpo_col2:
    st.metric(
        label="Mission Coverage vs. Guangzhou",
        value=f"{total_cpos_in_plan} / {total_gz_cpos}",
        help=f"本次任务计划覆盖 {total_cpos_in_plan} 个运营商，占广州市CPO总数 ({total_gz_cpos}) 的 **{mission_vs_gz_percentage:.2f}%**。"
    )

st.divider()

# 功率类型指标
st.subheader("Power Type Distribution")
power_col1, power_col2, power_col3 = st.columns(3)
with power_col1:
    st.metric(label="DC Stations (直流)", value=f"{dc_count}", help=f"占已知类型的 {dc_percentage:.1f}%")
with power_col2:
    st.metric(label="AC Stations (交流)", value=f"{ac_count}", help=f"占已知类型的 {ac_percentage:.1f}%")
with power_col3:
    st.metric(label="Unknown Power Type", value=f"{unknown_count}", help="基于 Is_AC/Is_DC 字段判断，未能明确分类的站点。")

st.divider()

# 品牌分类饼图与OEM列表
list_col1, list_col2 = st.columns([0.6, 0.4]) 

with list_col1:
    st.subheader("Target Brand Category Distribution")
    fig = px.pie(
        values=category_counts.values, 
        names=category_counts.index,
        title="充电站品牌分类",
        color=category_counts.index,
        color_discrete_map={
            "友商品牌 (OEM)": "#9467bd", 
            "主要品牌 (Primary CPO)": "#2ca02c", 
            "当地品牌 (Local CPO)": "#ff7f0e"
        }
    )
    fig.update_traces(textinfo='percent+value', textfont_size=14)
    fig.update_layout(legend_title_text='品牌类别')
    st.plotly_chart(fig, use_container_width=True)

with list_col2:
    st.subheader("Friendly Competitor Brands (OEM)")
    st.caption("Selection Logic: For each brand, one representative station from the high-rating and low-rating groups (relative to the brand's average) was selected.")
    oem_stations_in_plan = stations_df[stations_df['cpo_category'] == '友商品牌 (OEM)']
    oem_brand_display = " | ".join(oem_stations_in_plan['brand_keyword'].unique())
    st.warning(oem_brand_display)
    with st.expander("View all OEM representative stations in this mission"):
        st.dataframe(oem_stations_in_plan[['station_name', 'brand_keyword', 'rating']], use_container_width=True)

st.divider()

# 任务概览分层地图
st.subheader("Mission Targets Overview Map (Layered)")

gaode_tiles = "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
gaode_attribution = "Amap"
map_center = [stations_df['latitude'].mean(), stations_df['longitude'].mean()]
m = folium.Map(
    location=map_center, 
    zoom_start=10, 
    tiles=None
)

folium.TileLayer(
    tiles=gaode_tiles,
    attr=gaode_attribution,
    name="Amap"
).add_to(m)

layer_oem = folium.FeatureGroup(name="友商品牌 (OEM)", show=True)
layer_primary = folium.FeatureGroup(name="主要品牌 (Primary CPO)", show=True)
layer_local = folium.FeatureGroup(name="当地品牌 (Local CPO)", show=True)

category_styles = {
    "友商品牌 (OEM)": {'color': 'purple', 'icon': 'car'},
    "主要品牌 (Primary CPO)": {'color': 'green', 'icon': 'plug'},
    "当地品牌 (Local CPO)": {'color': 'orange', 'icon': 'bolt'}
}

for _, station in stations_df.iterrows():
    category = station['cpo_category']
    style = category_styles.get(category, {'color': 'gray', 'icon': 'question-sign'})
    
    marker = folium.Marker(
        location=[station['latitude'], station['longitude']],
        popup=f"<b>{station['station_name']}</b><br>Category: {category}<br>Operator: {station['operator_name']}",
        icon=folium.Icon(color=style['color'], icon=style['icon'], prefix='fa')
    )
    
    if category == "友商品牌 (OEM)":
        marker.add_to(layer_oem)
    elif category == "主要品牌 (Primary CPO)":
        marker.add_to(layer_primary)
    else:
        marker.add_to(layer_local)

layer_oem.add_to(m)
layer_primary.add_to(m)
layer_local.add_to(m)

folium.Marker(
    location=[HOTEL_LOCATION['latitude'], HOTEL_LOCATION['longitude']],
    popup=f"<b>{HOTEL_LOCATION['name']}</b><br>Type: Base of Operations",
    icon=folium.Icon(color='blue', icon='bed', prefix='fa')
).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width='100%', height=600)

st.success(
    """
    **Mission Briefing Complete.**
    Please proceed to the **Mission_Report** page from the sidebar to view the daily routes.
    """
)
st.sidebar.success("Select a page above to get started.")