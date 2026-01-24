# database.py
import sqlite3
import pandas as pd
import hashlib

DB_FILE = 'finance_system.db'


def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 流水表
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
    # 默认管理员
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES (?, ?)", ("admin", make_hash("123456")))
    conn.commit()
    conn.close()


def get_all_records():
    """获取所有记录，返回字典列表供前端使用"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 让结果可以通过列名访问
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records ORDER BY record_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_record(item, date, amount, operator="admin"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    type_str = "收入" if float(amount) >= 0 else "支出"
    c.execute("INSERT INTO records (item_name, record_date, amount, record_type, operator) VALUES (?, ?, ?, ?, ?)",
              (item, str(date), float(amount), type_str, operator))
    conn.commit()
    conn.close()


# database.py 局部确认

def get_financial_summary_text():
    """生成财务数据的文本摘要，供 AI 使用"""
    try:
        data = get_all_records()
        if not data:
            return "当前系统中没有任何财务收支记录。请告知用户先去录入数据。"

        df = pd.DataFrame(data)

        # 确保 amount 是数字类型
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

        total_in = df[df['amount'] > 0]['amount'].sum()
        total_out = df[df['amount'] < 0]['amount'].sum()
        profit = total_in + total_out

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
    """根据 ID 删除记录"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM records WHERE id = ?", (record_id,))
        # 检查是否有行被删除
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
    except Exception as e:
        print(f"删除失败: {e}")
        return False


def insert_batch_from_excel(df):
    """批量插入 DataFrame 数据"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    count = 0
    for _, row in df.iterrows():
        try:
            # 简单清洗数据
            item = str(row['项目'])
            # 处理日期：尝试转为 YYYY-MM-DD 字符串
            date_val = pd.to_datetime(row['日期']).strftime('%Y-%m-%d')
            amount = float(row['金额'])
            type_str = "收入" if amount >= 0 else "支出"
            operator = "admin"  # 默认操作人

            c.execute(
                "INSERT INTO records (item_name, record_date, amount, record_type, operator) VALUES (?, ?, ?, ?, ?)",
                (item, date_val, amount, type_str, operator))
            count += 1
        except Exception as e:
            print(f"跳过错误行: {row} - {e}")
            continue

    conn.commit()
    conn.close()
    return count


def get_filtered_financial_summary(start_date: str, end_date: str):
    """
    根据时间范围生成财务摘要
    :param start_date: 'YYYY-MM-DD'
    :param end_date: 'YYYY-MM-DD'
    """
    df = pd.DataFrame(get_all_records())

    if df.empty:
        return "数据库为空，无法进行分析。"

    # 1. 转换日期格式进行筛选
    df['record_date'] = pd.to_datetime(df['record_date'])
    mask = (df['record_date'] >= pd.to_datetime(start_date)) & (df['record_date'] <= pd.to_datetime(end_date))
    filtered_df = df.loc[mask]

    if filtered_df.empty:
        return f"在 {start_date} 到 {end_date} 期间没有找到任何财务记录。"

    # 2. 确保金额是数字
    filtered_df.loc[:, 'amount'] = pd.to_numeric(filtered_df['amount'], errors='coerce').fillna(0)

    # 3. 统计核心指标
    total_in = filtered_df[filtered_df['amount'] > 0]['amount'].sum()
    total_out = filtered_df[filtered_df['amount'] < 0]['amount'].sum()
    profit = total_in + total_out

    # 计算收支比或利润率
    margin_text = ""
    if total_in > 0:
        margin = (profit / total_in) * 100
        margin_text = f"（净利率: {margin:.1f}%）"

    # 4. 获取该时间段内 Top 3 大额支出 (减少干扰，只取前3)
    top_expense = filtered_df[filtered_df['amount'] < 0].sort_values('amount').head(3)
    top_str = ""
    for _, row in top_expense.iterrows():
        date_str = row['record_date'].strftime('%Y-%m-%d')
        top_str += f"- {date_str} [{row['item_name']}]: {row['amount']}\n"

    # 5. 生成摘要文本
    summary = (
        f"【分析时间段】: {start_date} 至 {end_date}\n"
        f"【经营数据】:\n"
        f"   - 总收入: {total_in:.2f}\n"
        f"   - 总支出: {total_out:.2f}\n"
        f"   - 净利润: {profit:.2f} {margin_text}\n"
        f"【重点支出项(Top3)】:\n{top_str}"
    )

    return summary
