import pandas as pd
import numpy as np
from scipy.optimize import minimize

# 读取CSV文件
df = pd.read_csv('./salary_model/sales_Nov.csv', dtype={'工号': str})

# 去除工号列的前后空格
df['工号'] = df['工号'].str.strip()
# 处理销售额列：去掉逗号并转换为浮点数
df['销售额'] = df['销售额'].str.replace(',', '').astype(float)
df['销售提成'] = df['销售提成'].str.replace(',', '').astype(float)

# names_to_remove 是需要移除的姓名列表
names_to_remove = ['杨小冬', '杨春凤', '梁红香', '王晓敏', '高景芝']
df_filtered = df[~df['姓名'].isin(names_to_remove)]

# 汇总每个员工的销售提成
total_commissions_by_employee = df_filtered.groupby('姓名')['销售提成'].sum()
total_commissions_by_employee += df_filtered.groupby('姓名')['营业员提成'].sum()

# 进行数据转换
summary_df = df_filtered.pivot_table(
    index=['工号', '姓名'],
    values=['销售额', '销售提成'],
    columns='分类',
    aggfunc='sum',
    fill_value=0
).reset_index()

# 将MultiIndex的列名压平，并创建一个新的列名列表
summary_df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in summary_df.columns.values]

# 计算每个员工的营业员提成总和
summary_df['总营业员提成'] = df_filtered.groupby(['工号', '姓名'])['营业员提成'].sum().values


# 定义目标函数，它将基于提成比例计算预测的总提成
def objective(commission_rates, total_commissions_by_employee, sales_data):
    # 根据新的提成比例计算预测提成
    predicted_commissions = (
        sales_data['销售额_A'] * commission_rates[0] +
        sales_data['销售额_B'] * commission_rates[1] +
        sales_data['销售额_C1'] * commission_rates[2] +
        sales_data['销售额_C2'] * commission_rates[3] +
        sales_data['销售额_E'] * commission_rates[4]
    )
    
    # 计算预测提成与当前提成之间的差异
    commission_diff = predicted_commissions - total_commissions_by_employee

    # 计算方差
    variance = commission_diff.var()
    
    # 我们的目标是最小化差异和方差
    return commission_diff.pow(2).sum() + variance

# 初始提成比例
initial_commission_rates = [0.08, 0.07, 0.04, 0.01, 0.005]

# 销售数据
sales_data = summary_df

# 当前总提成
current_total_commissions = summary_df['销售提成_A'] + summary_df['销售提成_B'] + \
                            summary_df['销售提成_C1'] + summary_df['销售提成_C2'] + \
                            summary_df['销售提成_E'] + summary_df['总营业员提成']

# 约束条件调整
constraints = (
    # 每个提成比例必须是非负的
    {'type': 'ineq', 'fun': lambda x: min(x)},
    {'type': 'eq', 'fun': lambda x: x[2] - 0.03},
    {'type': 'eq', 'fun': lambda x: x[3] - 0.02},
    {'type': 'eq', 'fun': lambda x: x[4] - 0.005},
    # A类提成比例不小于B类
    {'type': 'ineq', 'fun': lambda x: x[0] - x[1] - 0.02},
    # B类提成比例不小于C1类
    {'type': 'ineq', 'fun': lambda x: x[1] - x[2]},
    # C1类提成比例不小于C2类
    {'type': 'ineq', 'fun': lambda x: x[2] - x[3]},
    # C2类提成比例不小于E类
    {'type': 'ineq', 'fun': lambda x: x[3] - x[4]},
)

# 执行优化
result = minimize(
    objective,
    initial_commission_rates,
    args=(current_total_commissions, sales_data),
    constraints=constraints,
    method='trust-constr'
)

# 输出最优解
if result.success:
    optimized_commission_rates = result.x
    print("Optimized Commission Rates:", optimized_commission_rates)
else:
    print("Optimization failed:", result.message)


