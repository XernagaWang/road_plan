import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
import pydeck as pdk # type: ignore
import json # type: ignore
import folium # type: ignore
from streamlit_folium import st_folium # type: ignore


# --- 页面基础设置 ---
st.set_page_config(layout="wide", page_title="Mission Completed")

st.title("Mission Completed")
st.markdown("Perform data analysis and visualize the results of completed road test tasks.")

# --- 数据加载函数 ---
@st.cache_data
def load_data():
    """加载所有需要的数据文件"""
    try:
        final_report = pd.read_csv("final_mission_report.csv")
        report_a = pd.read_csv("report_A_enriched.csv")
        report_b = pd.read_csv("report_B_enriched.csv")
        with open("best_hotel_info_A.json", 'r') as f:
            hotel_a = json.load(f)
        # 策略B的最佳酒店信息也需要从模拟结果中获取，这里我们暂时复用A的作为示例
        # 在实际应用中，您应该为策略B也保存一个 best_hotel_info_B.json
        hotel_b = hotel_a 
        return final_report, report_a, report_b, hotel_a, hotel_b
    except FileNotFoundError as e:
        st.error(f"错误：缺少必要的数据文件: {e.filename}。请先在 Jupyter Notebook 中运行数据生成步骤。")
        return None, None, None, None, None

# --- 加载数据 ---
final_report_df, report_a_df, report_b_df, hotel_a_info, hotel_b_info = load_data()

if final_report_df is None:
    st.stop()

# --- 侧边栏策略选择 ---
st.sidebar.header("Report Select")
selected_strategy_name = st.sidebar.radio(
    "Please Select Plan:",
    options=['Plan A: Completeness First', 'Plan B: Counts First'],
)

# --- 根据选择筛选数据 ---
if selected_strategy_name == 'Plan A: Completeness First':
    strategy_char = 'A'
    strategy_df = final_report_df[final_report_df['strategy'] == strategy_char].copy()
    simulation_log_df = report_a_df
    hotel_info = hotel_a_info
else:
    strategy_char = 'B'
    strategy_df = final_report_df[final_report_df['strategy'] == strategy_char].copy()
    simulation_log_df = report_b_df
    hotel_info = hotel_b_info

if strategy_df.empty:
    st.warning("当前所选策略没有可用的复盘数据。")
    st.stop()

# --- 1. 顶层核心指标 (KPIs) ---
st.header(f"Core Result - {selected_strategy_name}")

total_tests = len(strategy_df)
success_count = len(strategy_df[strategy_df['status'] == '成功'])
failure_count = total_tests - success_count
success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
total_days = simulation_log_df['第幾天'].max() if not simulation_log_df.empty else 'N/A'
total_cpos = strategy_df['operator_name'].nunique()

kpi_cols = st.columns(4)
kpi_cols[0].metric("Total Tested Counts: ", f"{total_tests} 个")
kpi_cols[1].metric("Total Succese Rate", f"{success_rate:.1f} %")
kpi_cols[2].metric("Time Cost", f"{total_days} Days")
kpi_cols[3].metric("Tested CPO Counts", f"{total_cpos}")


# --- 2. 深入分析 ---
st.header("Analysis")
analysis_cols = st.columns([1, 1.5]) # 左窄右宽

# 左侧：失败归因分析
with analysis_cols[0]:
    st.subheader("Test failure reasons distribution")
    failures_df = strategy_df[strategy_df['status'] == '失败']
    if failures_df.empty:
        st.success("🎉 任务完美成功！")
    else:
        reason_counts = failures_df['failure_reason'].value_counts().reset_index()
        reason_counts.columns = ['原因', '次数']
        fig = px.pie(reason_counts, names='原因', values='次数', 
                     title='Rate of Test Failure', hole=0.4,
                     color_discrete_map={'桩端问题':'#EF553B', '车端问题':'#636EFA'})
        fig.update_layout(legend_title_text='失败来源')
        st.plotly_chart(fig, use_container_width=True)

# 右侧：运营商测试总结
with analysis_cols[1]:
    st.subheader("Test performance of CPO")
    cpo_summary = strategy_df.groupby('operator_name').agg(
        测试次数=('status', 'count'),
        成功次数=('status', lambda x: (x == '成功').sum())
    ).reset_index()
    cpo_summary['失败次数'] = cpo_summary['测试次数'] - cpo_summary['成功次数']
    cpo_summary['成功率(%)'] = (cpo_summary['成功次数'] / cpo_summary['测试次数']) * 100
    
    st.dataframe(
        cpo_summary.sort_values('成功率(%)', ascending=True), 
        use_container_width=True,
        hide_index=True,
        column_config={
            "成功率(%)": st.column_config.ProgressColumn(
                "成功率(%)",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        }
    )


# --- 3. 带有筛选的地理复盘地图 ---
st.header("Location")

if not strategy_df.empty:
    # 定义高德地图底图URL和版权信息
    gaode_tiles = "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
    gaode_attribution = "Amap"

    # 计算地图中心点
    map_center = [strategy_df['latitude'].mean(), strategy_df['longitude'].mean()]

    # --- 修改点 ---
    # 1. 创建一个不带默认底图的 Folium 地图对象
    m = folium.Map(
        location=map_center, 
        zoom_start=10, 
        tiles=None  # 关键：不在这里指定底图
    )

    # 2. 将高德地图作为一个独立的图层添加，并为其指定一个简洁的名称
    folium.TileLayer(
        tiles=gaode_tiles,
        attr=gaode_attribution,
        name="Amap"  # 关键：这个名称会显示在图层控制器中
    ).add_to(m)

    # 创建“成功”和“失败”两个图层组
    success_layer = folium.FeatureGroup(name="✅ 成功站点 (Success)", show=True).add_to(m)
    fail_layer = folium.FeatureGroup(name="❌ 失败站点 (Fail)", show=True).add_to(m)

    # 将数据点添加到对应的图层
    for _, row in strategy_df.iterrows():
        popup_html = f"""
        <b>站点名称:</b> {row['station_name']}<br>
        <b>运营商:</b> {row['operator_name']}<br>
        <b>状态:</b> {row['status']}<br>
        <b>失败原因:</b> {row['failure_reason']}
        """
        if row['status'] == '成功':
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='green', icon='check-circle')
            ).add_to(success_layer)
        else:
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='red', icon='times-circle')
            ).add_to(fail_layer)

    # 添加图层控制器，让用户可以自由勾选
    folium.LayerControl(collapsed=False).add_to(m)

    # 在 Streamlit 中渲染地图
    # st.info("您可以在地图右上角勾选图层，以筛选查看成功或失败的站点。")
    st_folium(m, width='100%', height=800)

else:
    st.warning("没有可供显示的地理数据。")