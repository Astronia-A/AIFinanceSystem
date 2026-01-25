import random
from datetime import date, timedelta
from openpyxl import Workbook

def generate_account_excel(filename="account.xlsx"):
    # 创建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "流水"

    # 表头（无编号）
    ws.append(["项目", "日期", "金额"])

    # 日期范围
    start_date = date(2020, 1, 1)
    end_date = date(2025, 12, 31)

    # 收入 / 支出项目
    income_projects = [
        "软件产品销售收入","软件订阅收入","技术服务收入","维护与技术支持服务费","云服务或平台使用费","系统集成项目收入",
        "企业级解决方案收入","数据服务或数据接口收费","API调用或平台接口收入","广告收入","增值服务收入","授权许可收入",
        "咨询服务收入","培训服务收入","合作分成收入","政府补贴或科研项目经费","定制化产品交付收入","运维托管服务收入",
        "国际市场销售收入","技术成果转化或专利收益"
        ]
    expense_projects = [
        "员工薪酬","社保及员工福利支出","研发投入","云服务与服务器费用","软件及技术授权费用","办公场地租金",
        "市场推广费用","销售渠道与推广佣金","设备采购","网络与通信费用","数据安全与合规支出","差旅费用","培训与人才发展费用",
        "运维成本","法律与咨询费用","税费支出","第三方服务外包费用","产品售后与客户支持成本","折旧与摊销","办公日常费用"]

    current_date = start_date

    while current_date <= end_date:
        # 每天随机生成 0~3 条流水
        for _ in range(random.randint(0, 3)):
            if random.choice([True, False]):
                # 收入
                project = random.choice(income_projects)
                amount = round(random.uniform(10, 200), 2) * 100
            else:
                # 支出
                project = random.choice(expense_projects)
                amount = -round(random.uniform(5, 150), 2) * 100

            ws.append([
                project,
                f"{current_date.year}.{current_date.month}.{current_date.day}",
                amount
            ])

        current_date += timedelta(days=1)

    # 保存 Excel 文件
    wb.save(filename)
    print(f"流水文件已生成：{filename}")

if __name__ == "__main__":
    generate_account_excel()
