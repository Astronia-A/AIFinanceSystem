# database.py
"""
数据访问层 (DAL) 模块
功能：
1. SQLite 数据库的初始化与连接管理
2. 财务记录的 CRUD (增删改查) 操作
3. 用户认证数据管理
4. 数据清洗与格式化 (用于 Excel 导入)
5. 核心功能：基于 Pandas 进行数据统计，为 AI 提供结构化的财务摘要文本
"""

import sqlite3
import pandas as pd
import hashlib

# 数据库文件路径
DB_FILE = 'finance_system.db'

def make_hash(password):
    """
    对密码进行 SHA-256 加密
    用于存储用户凭证时的安全性处理
    """
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """
    初始化数据库
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 财务流水表
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            record_date TEXT NOT NULL,
            amount REAL NOT NULL,
            record_type TEXT NOT NULL,
            operator TEXT DEFAULT 'admin'
        )
    ''')
    # 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    # 初始化默认管理员账户
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES (?, ?)", ("admin", make_hash("123456")))
    conn.commit()
    conn.close()

def get_all_records():
    """
    获取所有财务记录
    Returns:
        list[dict]: 返回字典列表，格式如 [{'id': 1, 'item_name': '...', ...}, ...]
        用于前端直接渲染表格或图表
    """
    conn = sqlite3.connect(DB_FILE)
    # 设置 row_factory 让查询结果可以通过列名索引，类似字典
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # 按日期倒序排列
    cursor.execute("SELECT * FROM records ORDER BY record_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_record(item, date, amount, operator="admin"):
    """
    插入单条财务记录
    Args:
        item (str): 项目名称
        date (str): 日期字符串
        amount (float): 金额
        operator (str): 操作人，默认为 admin
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 判断收支类型
    type_str = "收入" if float(amount) >= 0 else "支出"
    c.execute("INSERT INTO records (item_name, record_date, amount, record_type, operator) VALUES (?, ?, ?, ?, ?)",
              (item, str(date), float(amount), type_str, operator))
    conn.commit()
    conn.close()

def get_financial_summary_text():
    """
    生成全量财务数据的文本摘要
    用途:
    当用户未指定时间范围时，AI 需要对整体财务状况进行分析。
    该函数计算总收入、总支出和净利润，并格式化为自然语言文本。
    """
    try:
        data = get_all_records()
        if not data:
            return "当前系统中没有任何财务收支记录。请告知用户先去录入数据。"
        df = pd.DataFrame(data)
        # 数据清洗：确保 amount 列为数值类型，处理潜在的非数字字符
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        # 统计核心指标
        total_in = df[df['amount'] > 0]['amount'].sum()
        total_out = df[df['amount'] < 0]['amount'].sum()
        profit = total_in + total_out
        # 构造发给 LLM 的 Prompt 片段
        summary = (
            f"财务数据统计如下：\n"
            f"总收入: {total_in:.2f} 元\n"
            f"总支出: {total_out:.2f} 元\n"
            f"净利润: {profit:.2f} 元\n"
        )
        return summary
    except Exception as e:
        print(f"❌ 生成数据摘要失败: {e}")
        return "读取财务数据时发生错误，请检查数据库。"

def delete_record(record_id):
    """
    根据 ID 删除记录
    Returns:
        bool: 删除是否成功 (受影响行数 > 0)
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM records WHERE id = ?", (record_id,))
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
    except Exception as e:
        print(f"删除失败: {e}")
        return False

def insert_batch_from_excel(df):
    """
    从 Pandas DataFrame 批量插入数据
    流程:
    1. 遍历 DataFrame 行
    2. 数据清洗 (日期格式化、类型转换)
    3. 逐行插入数据库
    4. 容错处理：单行报错不影响整体流程
    Returns:
        int: 成功插入的记录数量
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    count = 0
    for _, row in df.iterrows():
        try:
            # 数据类型转换与清洗，自动判断类型
            item = str(row['项目'])
            date_val = pd.to_datetime(row['日期']).strftime('%Y-%m-%d')
            amount = float(row['金额'])
            type_str = "收入" if amount >= 0 else "支出"
            operator = "admin"
            c.execute(
                "INSERT INTO records (item_name, record_date, amount, record_type, operator) VALUES (?, ?, ?, ?, ?)",
                (item, date_val, amount, type_str, operator))
            count += 1
        except Exception as e:
            # 记录日志但不中断循环
            print(f"跳过错误行: {row} - {e}")
            continue
    conn.commit()
    conn.close()
    return count

def get_filtered_financial_summary(start_date: str, end_date: str):
    """
    根据特定时间范围生成深度财务摘要 (Agent 核心功能)
    功能:
    1. 按日期范围筛选数据
    2. 计算 KPI (总收支、净利润、净利率)
    3. 提取 Top 3 大额支出项 (用于 AI 进行风险提示)
    4. 格式化为结构化文本供 AI 理解
    Args:
        start_date (str): 开始日期 'YYYY-MM-DD'
        end_date (str): 结束日期 'YYYY-MM-DD'
    """
    df = pd.DataFrame(get_all_records())
    if df.empty:
        return "数据库为空，无法进行分析。"
    # 1. 日期格式标准化与筛选
    df['record_date'] = pd.to_datetime(df['record_date'])
    # 创建布尔掩码进行切片
    mask = (df['record_date'] >= pd.to_datetime(start_date)) & (df['record_date'] <= pd.to_datetime(end_date))
    filtered_df = df.loc[mask]
    if filtered_df.empty:        return f"在 {start_date} 到 {end_date} 期间没有找到任何财务记录。"
    # 2. 数据清洗
    filtered_df.loc[:, 'amount'] = pd.to_numeric(filtered_df['amount'], errors='coerce').fillna(0)
    # 3. 统计核心财务指标
    total_in = filtered_df[filtered_df['amount'] > 0]['amount'].sum()
    total_out = filtered_df[filtered_df['amount'] < 0]['amount'].sum()
    profit = total_in + total_out
    # 计算净利率 (仅在有收入时计算)
    margin_text = ""
    if total_in > 0:
        margin = (profit / total_in) * 100
        margin_text = f"（净利率: {margin:.1f}%）"
    # 4. 提取关键洞察：该时间段内 Top 3 大额支出
    # 逻辑：筛选负数 -> 排序 -> 取前三
    top_expense = filtered_df[filtered_df['amount'] < 0].sort_values('amount').head(3)
    top_str = ""
    for _, row in top_expense.iterrows():
        date_str = row['record_date'].strftime('%Y-%m-%d')
        top_str += f"- {date_str} [{row['item_name']}]: {row['amount']}\n"
    # 5. 生成最终传给 LLM 的摘要文本
    summary = (
        f"【分析时间段】: {start_date} 至 {end_date}\n"
        f"【经营数据】:\n"
        f"   - 总收入: {total_in:.2f}\n"
        f"   - 总支出: {total_out:.2f}\n"
        f"   - 净利润: {profit:.2f} {margin_text}\n"
        f"【重点支出项(Top3)】:\n{top_str}"
    )
    return summary