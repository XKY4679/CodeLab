import pandas as pd
import random
import os
import time
from tkinter import filedialog, Tk

# 配置项
MAX_QUESTIONS = 20  # 每次最大题数
SCORE_PER_Q = 5  # 每题分值 (也可以选择动态计算)


def select_file():
    """ 弹窗选择文件，解决路径硬编码问题 """
    print("正在打开文件选择窗口...")
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="请选择题库Excel文件",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    return file_path


def load_questions(file_path):
    try:
        if not file_path:
            return None

        df = pd.read_excel(file_path, engine='openpyxl')

        # 清理列名空格，防止' 答案'这种由于空格导致的错误
        df.columns = df.columns.str.strip()

        required_columns = ['题目', '选项A', '选项B', '选项C', '选项D', '答案', '解析内容']
        if not all(col in df.columns for col in required_columns):
            print(f"错误：Excel文件缺少必要的列。需要：{required_columns}")
            return None

        # 填充空值为 "暂无解析"，防止显示 nan
        df['解析内容'] = df['解析内容'].fillna("暂无解析")

        # 确保答案列都是字符串并转大写
        df['答案'] = df['答案'].astype(str).str.strip().str.upper()

        return df.to_dict('records')
    except Exception as e:
        print(f"读取文件出错: {str(e)}")
        return None


def run_quiz():
    file_path = select_file()
    if not file_path:
        print("未选择文件，程序退出。")
        return

    questions_pool = load_questions(file_path)
    if not questions_pool:
        return

    while True:  # 循环答题结构
        random.shuffle(questions_pool)
        # 动态决定题目数量：如果题库少于20题，就全选
        num_questions = min(MAX_QUESTIONS, len(questions_pool))
        current_quiz = questions_pool[:num_questions]

        score = 0
        wrong_questions = []  # 错题本

        # 动态计算满分 (防止题不够导致无法满分)
        total_possible_score = num_questions * SCORE_PER_Q

        print("\n" + "=" * 40)
        print(f"★ 智能答题系统启动 (本轮共 {num_questions} 题) ★")
        print("=" * 40)

        for i, q in enumerate(current_quiz):
            print(f"\n[第 {i + 1}/{num_questions} 题]")
            print(f"题目：{q['题目']}")
            print("-" * 20)
            for opt in ['A', 'B', 'C', 'D']:
                # 处理选项可能为空的情况
                opt_content = q.get(f'选项{opt}', '')
                print(f"{opt}. {opt_content}")

            while True:
                user_answer = input("\n请输入答案 (A/B/C/D)：").strip().upper()
                if user_answer in ['A', 'B', 'C', 'D']:
                    break
                print(">> 输入无效，请输入 A, B, C 或 D")

            correct_answer = q['答案']

            if user_answer == correct_answer:
                print(f"√ 回答正确！ (+{SCORE_PER_Q}分)")
                score += SCORE_PER_Q
            else:
                print(f"× 回答错误！")
                print(f"   您的选择：{user_answer}")
                print(f"   正确答案：{correct_answer}")
                # 加入错题本
                q['用户错选'] = user_answer
                wrong_questions.append(q)

            # 解析展示
            print(f"💡 解析：{q['解析内容']}")
            print("━" * 30)
            time.sleep(0.5)  # 稍微停顿，优化体验

        # 结算
        print("\n" + "#" * 30)
        print(f" 最终得分：{score} / {total_possible_score}")
        print("#" * 30)

        # 错题回顾
        if wrong_questions:
            print(f"\n您本轮做错了 {len(wrong_questions)} 道题，是否查看错题详情？(y/n)")
            if input().lower() == 'y':
                print("\n--- 错题回顾 ---")
                for wq in wrong_questions:
                    print(f"题目：{wq['题目']}")
                    print(f"正确答案：{wq['答案']} | 您的选择：{wq['用户错选']}")
                    print(f"解析：{wq['解析内容']}\n")

        # 是否重来
        if input("\n是否再来一轮？(y/n): ").lower() != 'y':
            print("感谢使用，再见！")
            break


if __name__ == "__main__":
    run_quiz()