import pandas as pd
import random

def load_questions():
    try:
        # 路径确认（保持与之前一致）
        df = pd.read_excel(r"C:\Users\XKY\Desktop\答题程序\题库.xlsx", engine='openpyxl')

        # 新增解析内容列验证
        required_columns = ['题目', '选项A', '选项B', '选项C', '选项D', '答案', '解析内容']
        if not all(col in df.columns for col in required_columns):
            print("错误：Excel文件必须包含以下列：", required_columns)
            exit()

        return df.to_dict('records')
    except Exception as e:
        print("读取题库失败：", str(e))
        exit()


def run_quiz():
    questions = load_questions()
    random.shuffle(questions)  # 打乱题目顺序
    score = 0

    print("\n★ 智能答题系统 ★")
    input("按回车键开始答题...")

    # 随机选择20题
    for i, q in enumerate(questions[:20]):  # 修改为选取前20题
        print(f"\n第 {i + 1} 题：{q['题目']}")
        [print(f"{opt}. {q[f'选项{opt}']}") for opt in ['A', 'B', 'C', 'D']]

        # 输入验证保持不变
        while True:
            user_answer = input("请输入答案（A/B/C/D）：").upper()
            if user_answer in ['A', 'B', 'C', 'D']:
                break
            print("＞＞ 输入错误，请重新选择")

        # 新增解析展示（无论对错都显示）
        correct_answer = q['答案'].strip().upper()
        if user_answer == correct_answer:
            print(f" √ 正确！ +5分")  # 修改为每题5分，20题满分100分
            score += 5
        else:
            print(f"× 错误（您选：{user_answer} | 正确：{correct_answer}）")

        # 新增解析内容展示
        print(f"解析：{q['解析内容']}\n{'━' * 30}")

    print(f"\n ★★★ 最终得分：{score}/100")
    input("按回车退出系统...")


if __name__ == "__main__":
    run_quiz()
