import pandas as pd
import streamlit as st
# import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import sys
import threading
import time
import numpy as np

# ===================== 中文字体支持配置 =====================
def setup_chinese_font_support():
    """配置Matplotlib支持中文显示"""
    # 尝试不同平台的中文字体
    font_candidates = []
    
    # Windows 字体路径
    if sys.platform.startswith('win'):
        font_candidates = [
            "C:/Windows/Fonts/simhei.ttf",      # 黑体
            "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
            "C:/Windows/Fonts/simkai.ttf",      # 楷体
        ]
    # macOS 字体路径
    elif sys.platform.startswith('darwin'):
        font_candidates = [
            "/System/Library/Fonts/PingFang.ttc",  # 苹方
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/STHeiti Light.ttc",  # 华文黑体
        ]
    # Linux 字体路径
    else:
        font_candidates = [
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Droid Sans
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",     # Noto Sans
        ]
    
    # 添加通用字体名称回退
    font_names = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'Arial Unicode MS', 'sans-serif']
    
    # 检查字体文件是否存在
    found_font = None
    for font_path in font_candidates:
        if os.path.exists(font_path):
            found_font = font_path
            break
    
    # 设置字体
    if found_font:
        try:
            # 注册字体
            font_prop = mpl.font_manager.FontProperties(fname=found_font)
            font_name = font_prop.get_name()
            
            # 更新配置
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = [font_name] + font_names
            print(f"使用字体: {font_name} ({found_font})")
        except Exception as e:
            print(f"字体注册失败: {e}")
            plt.rcParams['font.sans-serif'] = font_names
    else:
        # print("未找到字体文件，使用字体名称回退")
        plt.rcParams['font.sans-serif'] = font_names
    
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False
# 调用字体设置函数
setup_chinese_font_support()
# ===================== 结束字体配置 =====================

# 配置文件路径
EXCEL_FILE = "financial_records.xlsx"

# 初始化Excel文件
def init_excel_file():
    if not os.path.exists(EXCEL_FILE):
        columns = [
            "序号", "日期", "类型", "账户", "金额", "余额", "来源", "用途", "标签", "备注"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(EXCEL_FILE, index=False)

# 读取Excel数据
def load_data():
    try:
        df  = pd.read_excel(EXCEL_FILE, parse_dates=["日期"])
            # 如果余额列不存在，添加并计算余额
        if '余额' not in df.columns:
            df = calculate_balance(df)
        
        # 添加排序 - 按序号升序
        df = df.sort_values(by='序号', ascending=True) #
        return df
    except FileNotFoundError:
        init_excel_file()
        return pd.DataFrame()

# 计算余额
def calculate_balance(df):
    """计算并更新每笔记录的余额"""
    if df.empty:
        return df
    
    # 确保账户列存在
    if '账户' not in df.columns:
        df['账户'] = '中行'  # 默认为中行账户

    # 按日期和索引排序，确保正确的计算顺序
    df = df.sort_values(by=['账户', '日期'])
    
    # 计算每笔记录的金额变动（收入为正，支出为负）
    df['变动'] = df.apply(lambda row: row['金额'] if row['类型'] == '收入' else -row['金额'], axis=1)
    
    # 计算累计余额
    df['余额'] = df.groupby('账户')['变动'].cumsum()
    
    # 删除临时列
    df = df.drop(columns=['变动'])
    
    return df

# 保存数据到Excel
def save_data(df):
    # 确保保存前余额已计算
    if '余额' not in df.columns:
        df = calculate_balance(df)
    df.to_excel(EXCEL_FILE, index=False)

# 添加新记录
def add_record(df, record):
    # 生成新序号（当前最大序号+1）
    if df.empty:
        new_id = 1
    else:
        new_id = df['序号'].max() + 1
    
    # 添加序号到记录
    record_with_id = {"序号": new_id, **record}
    
    # 添加新记录
    new_df = pd.concat([df, pd.DataFrame([record_with_id])], ignore_index=True)
    # 重新计算所有余额
    new_df = calculate_balance(new_df)
    return new_df

# 删除记录
def delete_record(df, index):
    # 删除记录
    new_df = df.drop(index).reset_index(drop=True)
    # 重新计算所有余额
    new_df = calculate_balance(new_df)
    return new_df

# 更新记录
def update_record(df, index, updated_record):
    # 更新记录
    for col in updated_record:
        df.loc[index, col] = updated_record[col]
    # 重新计算所有余额
    df = calculate_balance(df)
    return df


# ========== 日期转换辅助函数 ==========
def to_timestamp(date_obj):
    """将日期对象转换为 Pandas Timestamp"""
    return pd.Timestamp(date_obj)


def to_date(timestamp):
    """将 Pandas Timestamp 转换为 Python date 对象"""
    return timestamp.date()

# 安全退出函数 - 简化版
def safe_exit():
    st.stop()  # 停止Streamlit执行，但不退出进程

# 主应用
def main():
    # 初始化文件
    init_excel_file()
    
    # 加载数据
    df = load_data()
    
    st.title("💰 账本管理系统")
    
    # 在右上角添加退出按钮 - 使用空列保持布局
    col1, col2, col3 = st.columns([3, 3, 1])
    with col3:
        if st.button("安全退出", key="exit_button", help="保存数据并退出程序"):
            save_data(df)  # 确保数据保存
            safe_exit()
    
    st.markdown("---")

    # 显示个账户余额及总余额
    if not df.empty:
        # 获取所有账户
        accounts = df['账户'].unique()
        
        # 获取每个账户的最新余额
        account_balances = {}
        total_balance = 0
        
        for account in accounts:
            account_df = df[df['账户'] == account]
            if not account_df.empty:
                # 获取该账户最后一条记录的余额
                account_balance = account_df['余额'].iloc[-1]
                account_balances[account] = account_balance
                total_balance += account_balance
        
        # 创建列显示各账户余额
        cols = st.columns(len(accounts))  # +1 用于总余额
        
        for i, account in enumerate(accounts):
            with cols[i]:
                st.metric(f"{account}余额", f"¥{account_balances.get(account, 0):,.2f}")
        
        # 在最后一列显示总余额
        # with cols[-1]:
        #     st.metric("总余额", f"¥{total_balance:,.2f}")

        st.metric("总余额", f"¥{total_balance:,.2f}")

    else:
        st.info("暂无记录，当前余额为 ¥0.00")
    
    # 侧边栏 - 添加新记录
    with st.sidebar:
        st.header("添加新记录")
        date = st.date_input("日期", datetime.today())
        # 添加账户选择
        account = st.selectbox("账户", ["中行", "微信", "支付宝", "浦发", "建行", "其他"])
        trans_type = st.radio("类型", ["支出", "收入"])
        amount = st.number_input("金额", min_value=0.01, value=100.0, step=0.01)
        # description = st.text_input("来源", "餐饮")
        
        # 分类选项
        if trans_type == "支出":
            description = st.text_input("来源", "", key="source_input", disabled=True)
            category = st.selectbox("用途", ["饮", "零食", "吃饭", "请客", "月度", "网购", "交通", "购物", "娱乐", "住房", "医疗", "教育", "其他"], key="purpose_select")
            tags = st.text_input("标签(用逗号分隔)", "", key="tags_input")
        else:
            # 收入记录 - 禁用用途和标签
            description = st.text_input("来源", "工资", key="source_input")
            category = st.selectbox("用途", ["饮", "零食", "吃饭", "请客", "月度" ,"网购", "交通", "购物", "娱乐", "住房", "医疗", "教育", "其他"], 
                                   key="purpose_select", disabled=True)
            tags = st.text_input("标签(用逗号分隔)", "", key="tags_input", disabled=True)
        
        note = st.text_area("备注")
        
        if st.button("添加记录"):
            new_record = {
                "日期": to_timestamp(date),
                "类型": trans_type,
                "账户": account,
                "金额": amount,
                "来源": description if trans_type=='收入' else None,
                "用途": category if trans_type=='支出' else None,
                "标签": tags if trans_type=='支出' else None,
                "备注": note
            }
            df = add_record(df, new_record)
            save_data(df)
            st.success("记录添加成功!")
            # 显示更新后的余额
            # current_balance = df['余额'].iloc[-1]
            # st.success(f"当前余额更新为: ¥{current_balance:,.2f}")
            st.rerun() # 刷新显示最新余额

    # 主界面布局
    tab1, tab2, tab3, tab4 = st.tabs([ "数据管理","时间统计", "分类统计", "标签统计"])
    
    with tab1:  # 数据管理
        st.header("账本管理")

        # 添加账户筛选
        all_accounts = df['账户'].unique() if not df.empty else []
        selected_accounts = st.multiselect("选择账户", options=all_accounts, default=all_accounts)
        
        # 搜索功能
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("搜索关键词")
        with col2:
            if not df.empty:
                min_date = df["日期"].min()
                max_date = df["日期"].max()
                date_range = st.date_input("日期范围", [min_date, max_date])
            else:
                date_range = st.date_input("日期范围", [pd.Timestamp(datetime.today()), pd.Timestamp(datetime.today())])
        
        # 添加排序选项 
        sort_order = st.radio("数据排序方式", ["序号升序", "序号降序"], horizontal=True, index=0)

        # 应用筛选
        filtered_df = df.copy()
        
        if not df.empty:
            # 账户筛选
            # if selected_accounts:
            #     filtered_df = filtered_df[filtered_df['账户'].isin(selected_accounts)]

            # if search_term:
            #     filtered_df = filtered_df[
            #         filtered_df["来源"].str.contains(search_term, case=False) |
            #         filtered_df["用途"].str.contains(search_term, case=False) |
            #         filtered_df["标签"].str.contains(search_term, case=False) |
            #         filtered_df["备注"].str.contains(search_term, case=False) |
            #         filtered_df["账户"].str.contains(search_term, case=False)
            #     ]
            
            # 创建一个空的布尔序列，用于存储匹配结果
            mask = pd.Series(False, index=filtered_df.index)
            
            # 对每个可能包含搜索词的列进行检查
            for column in ["来源", "用途", "标签", "备注", "账户"]:
                # 只对非空值进行检查
                if column in filtered_df.columns:
                    # 将NaN转换为空字符串，然后检查是否包含搜索词
                    column_mask = filtered_df[column].fillna('').astype(str).str.contains(search_term, case=False, na=False)
                    mask = mask | column_mask
            
            # 应用筛选
            filtered_df = filtered_df[mask]
            
            if len(date_range) == 2:
                filtered_df = filtered_df[
                    (filtered_df["日期"] >= pd.Timestamp(date_range[0])) &
                    (filtered_df["日期"] <= pd.Timestamp(date_range[1]))
            ]
        
        # 按序号排序 
        if sort_order == "序号升序":
            filtered_df = filtered_df.sort_values(by='序号', ascending=True)
        else:
            filtered_df = filtered_df.sort_values(by='序号', ascending=False)

        # 显示数据
        if not df.empty and '余额' in filtered_df.columns:
            # 确保按日期降序排序（最新在前）
            # display_df = filtered_df.copy().sort_values(by='日期', ascending=False)
            # # 格式化余额列显示
            display_df = filtered_df.copy()
            # 格式化日期显示
            display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')
            display_df['余额'] = display_df['余额'].apply(lambda x: f"¥{x:,.2f}")
            # 将None替换为空字符串
            display_df = display_df.fillna('')
            st.dataframe(display_df,hide_index=True, height=600)
        else:
            st.dataframe(pd.DataFrame(),hide_index=True, height=600)



        # 编辑和删除功能
        if not filtered_df.empty:
            st.subheader("编辑或删除记录")
        
            # 使用自定义序号而不是DataFrame索引
            record_ids = filtered_df['序号'].tolist()
            selected_id = st.selectbox("选择记录序号", record_ids)
            # 根据选择的序号找到对应的记录
            record_index = filtered_df[filtered_df['序号'] == selected_id].index[0]
            record = df.loc[record_index]
        

            # edit_index = st.selectbox("选择记录序号", filtered_df.index)
            # record = filtered_df.loc[edit_index]
            
            # 显示当前日期（不带时分秒）
            current_date = record["日期"].to_pydatetime().date()
            new_date = st.date_input("日期", current_date)

            col1, col2 = st.columns(2)

            with col1:
                # 添加账户编辑
                new_account = st.selectbox("账户", ["中行", "微信", "支付宝", "浦发", "建行", "其他"], 
                                         index=["中行", "微信", "支付宝", "浦发", "建行", "其他"].index(record['账户']))

                if record['类型'] == "支出":
                    new_description = st.text_input("来源", ' ', disabled=True)
                    new_category = st.text_input("用途", record["用途"])
                elif record['类型'] == "收入":
                    new_description = st.text_input("来源", record["来源"])
                    new_category = st.text_input("用途", ' ', disabled=True)
            with col2:
                new_amount = st.number_input("金额", value=record["金额"])                
                if record['类型'] == "支出":
                    new_tags = st.text_input("标签", record["标签"])
                elif record['类型'] == "收入":
                    new_tags = st.text_input("标签", ' ', disabled=True)
            
            new_note = st.text_area("备注", record["备注"] if pd.notnull(record["备注"]) else '')
            
            col10, col20 = st.columns(2)
            with col10:
                if st.button("更新记录"):
                    
                    date_without_time = datetime.combine(new_date, datetime.min.time())
                    updated_record = {
                        "日期": pd.Timestamp(date_without_time),
                        "账户": new_account,
                        "来源": new_description if record['类型']=='收入' else None,
                        "用途": new_category if record['类型']=='支出' else None,
                        "金额": new_amount,
                        "标签": new_tags if record['类型']=='支出' else None,
                        "备注": new_note
                    }
                    df = update_record(df, record_index, updated_record)
                    save_data(df)
                    st.success("记录更新成功!")  
                    # 显示更新后的余额
                    # current_balance = df['余额'].iloc[-1]
                    # st.success(f"当前余额更新为: ¥{current_balance:,.2f}")
                    st.rerun()  # 刷新页面显示最新余额
            
            with col20:
                if st.button("删除记录"):
                    df = delete_record(df, record_index)
                    save_data(df)
                    st.success("记录删除成功!")
                    st.rerun()  # 刷新页面显示最新余额
        else:
            st.warning("没有可编辑的记录")
    
    with tab2:  # 时间分析
        st.header("时间维度分析")
        
        if df.empty:
            st.warning("暂无数据")
        else:
            # 添加账户筛选
            all_accounts = df['账户'].unique()
            selected_accounts = st.multiselect("选择账户（时间分析）", options=all_accounts, default=all_accounts)
            
            # 筛选数据
            time_df = df[df['账户'].isin(selected_accounts)] if selected_accounts else df
            
            # 搜索功能
            col1, col2 = st.columns(2)
            with col1:
                # 设置时间范围
                min_date = df["日期"].min()
                max_date = df["日期"].max()
                start_date, end_date = st.date_input("选择时间范围", [min_date, max_date])
            
            # 筛选数据
            time_df = time_df[(time_df["日期"] >= pd.Timestamp(start_date)) & 
                        (time_df["日期"] <= pd.Timestamp(end_date))]
            
            # 按时间频率分组
            with col2:
                freq = st.selectbox("时间频率", ["日", "周", "月",  "年"])#"季",
            freq_map = {"日": "D", "周": "W", "月": "M",  "年": "Y"} #"季": "Q",
            grouped = time_df.groupby([pd.Grouper(key="日期", freq=freq_map[freq]), "类型"])
            
            # 计算收支
            result = grouped["金额"].sum().unstack().fillna(0)
            result["净收入"] = result.get("收入", 0) - result.get("支出", 0)
            
            # 绘制图表
            fig, ax = plt.subplots(figsize=(12, 6))
            result[["收入", "支出"]].plot(kind="bar", ax=ax)
            ax.set_title(f"{freq}度收支情况")
            ax.set_ylabel("金额")
            ax.set_xlabel("日期")
                
            # 设置日期显示格式
            if freq in ["日", "周"]:
                ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%Y-%m-%d'))
            elif freq == "月":
                ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%Y-%m'))
            # elif freq == "季":
            #     ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%Y-%q'))
            elif freq == "年":
                ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%Y'))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            # 显示数据
            st.subheader("详细数据")
            st.dataframe(result)
    
    with tab3:  # 分类分析
        st.header("分类维度分析")
        
        if df.empty:
            st.warning("暂无数据")
        else:
            # 添加账户筛选
            all_accounts = df['账户'].unique()
            selected_accounts = st.multiselect("选择账户（分类分析）", options=all_accounts, default=all_accounts)
            
            # 筛选数据
            cat_df = df[df['账户'].isin(selected_accounts)] if selected_accounts else df
            
            # 选择分析类型
            analysis_type = st.radio("分析类型", ["支出分类", "收入分类"])
            target = "支出" if analysis_type == "支出分类" else "收入"
            
            # 筛选数据
            cat_df = cat_df[cat_df["类型"] == target]
            
            if cat_df.empty:
                st.warning(f"无{target}数据")
            else:
                # 确保分类字段没有空值
                cat_df = cat_df.dropna(subset=["用途"])
                
                # 分类统计
                category_stats = cat_df.groupby("用途")["金额"].sum().sort_values(ascending=False)
                
                # 检查是否有数据可展示
                if category_stats.empty:
                    st.warning(f"没有可用的{target}分类数据")
                else:
                    # 绘制饼图
                    fig1, ax1 = plt.subplots(figsize=(8, 8))
                    category_stats.plot(kind="pie", autopct="%1.1f%%", ax=ax1)
                    ax1.set_title(f"{target}分类占比")
                    ax1.set_ylabel("")
                    st.pyplot(fig1)
                    
                    # 绘制条形图 - 添加错误处理
                    try:
                        fig2, ax2 = plt.subplots(figsize=(10, 6))
                        category_stats.plot(kind="bar", ax=ax2)
                        ax2.set_title(f"{target}分类分布")
                        ax2.set_ylabel("金额")
                        
                        # 设置X轴标签旋转，避免重叠
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        
                        st.pyplot(fig2)
                    except Exception as e:
                        st.error(f"绘制条形图时出错: {str(e)}")
                        st.info("可能是因为没有足够的数据来绘制图表")
                    
                    # 显示数据
                    st.subheader("分类详细数据")
                    st.dataframe(category_stats)
    
    with tab4:  # 标签分析
        # st.header("标签维度分析")
        
        if df.empty:
            st.warning("暂无数据")
            return
        
        # 添加账户筛选
        all_accounts = df['账户'].unique()
        selected_accounts = st.multiselect("选择账户（标签分析）", options=all_accounts, default=all_accounts)
        
        # 筛选数据
        tag_df = df[df['账户'].isin(selected_accounts)] if selected_accounts else df

        # 预处理标签数据
        tag_df = (
            tag_df.assign(标签列表=df["标签"].str.split(" "))  # 拆分标签
            .explode("标签列表")  # 展开标签
            .assign(标签列表=lambda x: x["标签列表"].str.strip())  # 去除空格
            .query("标签列表 != ''")  # 过滤空标签
        )
        if tag_df.empty:
            st.warning("没有有效的标签数据")
            return

        col100, _ , col200 = st.columns([7,0.4,7])

        # with col100:
        st.header("各标签分布")
        # 标签分析参数设置
        col1, col2 = st.columns(2)
        with col1:
            tag_type = st.radio("收支类型", ["全部", "支出", "收入"])
        with col2:
            min_count = st.slider("最小出现次数", 1, 20, 1)
        
        # 筛选数据
        filtered_tag_df = tag_df.copy()
        if tag_type != "全部":
            filtered_tag_df = filtered_tag_df[filtered_tag_df["类型"] == tag_type]
        
        # 计算标签统计
        tag_stats = (
            filtered_tag_df.groupby("标签列表")["金额"]
            .agg(["sum", "count"])
            .query(f"count >= {min_count}")
            .sort_values("sum", ascending=False)
        )
        
        if tag_stats.empty:
            st.warning("没有符合条件的标签数据")
            return
        
        # 显示标签统计概览
        fig, ax = plt.subplots(figsize=(12, 8))
        tag_stats["sum"].plot(kind="bar", ax=ax)
        ax.set_title(f"标签分析 ({tag_type})")
        ax.set_ylabel("金额")
        st.pyplot(fig)
        
        st.subheader("标签详细数据")
        st.dataframe(tag_stats)

        # with col200:
        # 标签详细分析部分
        # st.markdown("---")
        st.header("特定标签")
        
        selected_tag = st.selectbox("选择要查看的标签", tag_stats.index)
        tag_records = filtered_tag_df[filtered_tag_df["标签列表"] == selected_tag]
        
        if tag_records.empty:
            st.warning(f"没有找到标签 '{selected_tag}' 的记录")
            return
        
        # 格式化显示记录
        display_records = (
            tag_records.assign(
                日期=lambda x: x["日期"].dt.strftime('%Y-%m-%d'),
                金额=lambda x: x["金额"].apply(lambda x: f"¥{x:,.2f}")
            )
            .fillna('')
            .sort_values('日期', ascending=False)
        )
        
        st.dataframe(display_records[["日期", "类型", "金额", "用途", "备注"]])
        
        # 绘制时间趋势图
        st.subheader(f"'{selected_tag}'标签的时间趋势")
        time_grouped = tag_records.groupby(pd.Grouper(key="日期", freq="M"))["金额"].sum()
        
        if len(time_grouped) > 1:
            fig2, ax2 = plt.subplots(figsize=(12, 6))
            time_grouped.plot(kind="line", marker="o", ax=ax2)
            ax2.set_title(f"'{selected_tag}'标签的月度趋势")
            ax2.set_ylabel("金额")
            ax2.grid(True)
            st.pyplot(fig2)
        else:
            st.info("数据点不足，无法显示趋势图")

        

    # # 在底部添加另一个退出按钮
    # st.markdown("---")
    # if st.button("安全退出程序", key="bottom_exit_button", help="保存数据并退出程序"):
    #     save_data(df)  # 确保数据保存
    #     safe_exit()

if __name__ == "__main__":
    main()
