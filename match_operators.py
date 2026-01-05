import json
import jieba
import re
import os

# 配置参数
ALL_OPERATORS_FILE1 = "/data/operator/fixed_others.json"
ALL_OPERATORS_FILE2 = "/data/operator/fixed_Declaration.json"
SCORE_THRESHOLD = 10
REAL_OPERATOR_THRESHOLD = 26

def analyze_operators(operators_file, is_file2=False):
    """从算子文件中分析算子-关键词映射"""
    operator_keywords = {}
    operator_keyword_weights = {}
    
    try:
        with open(operators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            operator = item.get("Assertional_Logic")
            keywords = item.get("key_words", [])
            
            if operator:
                operator_keywords[operator] = keywords
                
                if is_file2:
                    keyword_weight_map = {}
                    for kw_dict in keywords:
                        key_word = kw_dict.get("key_word", "")
                        weight = kw_dict.get("weight", 0)
                        if key_word:
                            keyword_weight_map[key_word] = weight
                    operator_keyword_weights[operator] = keyword_weight_map
                    
    except Exception as e:
        print(f"读取算子文件 {operators_file} 时出错: {e}")
    
    if is_file2:
        return operator_keywords, operator_keyword_weights
    else:
        return operator_keywords

def preprocess_text(text):
    """预处理文本"""
    if not text:
        return ""
    
    # 移除公式标记但保留内容
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    
    # 处理LaTeX中的绝对值符号
    text = re.sub(r'\\left\||\\right\|', '|', text)
    text = re.sub(r'\\mid\b', '|', text)
    
    # 移除标点符号，但保留数学符号
    text = re.sub(r'[^\w\s\|=+\-*/^_<>()\[\]{}]', ' ', text)
    
    # 转换为小写并移除多余空格
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text

def match_operators_to_problem(problem_text, operator_keywords):
    """将算子匹配到问题文本（用于文件1）"""
    processed_text = preprocess_text(problem_text)
    words = list(jieba.cut(processed_text))
    
    operator_scores = {}
    
    for operator, keywords in operator_keywords.items():
        score = 0
        
        for kw_dict in keywords:
            keyword = kw_dict.get("key_word", "")
            weight = kw_dict.get("weight", 0)
            if keyword and keyword in processed_text:
                score += weight
        
        for word in words:
            for kw_dict in keywords:
                keyword = kw_dict.get("key_word", "")
                weight = kw_dict.get("weight", 0)
                if keyword and word in keyword and len(word) > 2:
                    score += 0.5 * weight
        
        keyword_count = len(keywords)
        total_weight = sum(kw_dict.get("weight", 0) for kw_dict in keywords)
        diversity_bonus = min(total_weight / 200, 1.0)
        
        final_score = score + diversity_bonus
        
        if final_score >= SCORE_THRESHOLD:
            operator_scores[operator] = {
                "score": final_score,
                "base_score": score,
                "diversity_bonus": diversity_bonus,
                "keyword_count": keyword_count,
                "total_weight": total_weight
            }
    
    return operator_scores

def match_operators_to_problem_file2(problem_text, operator_keywords, operator_keyword_weights):
    """将算子匹配到问题文本（用于文件2，有Real算子特殊规则）"""
    processed_text = preprocess_text(problem_text)
    words = list(jieba.cut(processed_text))
    
    operator_scores = {}
    real_operator_score = 0
    
    for operator, keywords in operator_keywords.items():
        score = 0
        
        if operator in operator_keyword_weights:
            keyword_weight_map = operator_keyword_weights[operator]
            
            for keyword, weight in keyword_weight_map.items():
                if keyword in processed_text:
                    score += weight
            
            for word in words:
                for keyword, weight in keyword_weight_map.items():
                    if word in keyword and len(word) > 2:
                        score += 0.5 * weight
        else:
            for kw_dict in keywords:
                keyword = kw_dict.get("key_word", "")
                weight = kw_dict.get("weight", 0)
                if keyword and keyword in processed_text:
                    score += weight
            
            for word in words:
                for kw_dict in keywords:
                    keyword = kw_dict.get("key_word", "")
                    weight = kw_dict.get("weight", 0)
                    if keyword and word in keyword and len(word) > 2:
                        score += 0.5 * weight
        
        keyword_count = len(keywords)
        total_weight = sum(kw_dict.get("weight", 0) for kw_dict in keywords)
        diversity_bonus = min(total_weight / 200, 1.0)
        
        final_score = score + diversity_bonus
        
        if operator == "Real":
            real_operator_score = final_score
        elif final_score >= SCORE_THRESHOLD:
            operator_scores[operator] = {
                "score": final_score,
                "base_score": score,
                "diversity_bonus": diversity_bonus,
                "keyword_count": keyword_count,
                "total_weight": total_weight
            }
    
    # 应用特殊规则
    has_high_scoring_operator = False
    for operator, score_info in operator_scores.items():
        if score_info["score"] >= REAL_OPERATOR_THRESHOLD:
            has_high_scoring_operator = True
            break
    
    if not has_high_scoring_operator:
        operator_scores = {}
        if real_operator_score > 0:
            real_keywords = operator_keywords.get("Real", [])
            real_keyword_count = len(real_keywords)
            real_total_weight = sum(kw_dict.get("weight", 0) for kw_dict in real_keywords)
            
            operator_scores["Real"] = {
                "score": real_operator_score,
                "base_score": real_operator_score,
                "diversity_bonus": 0,
                "keyword_count": real_keyword_count,
                "total_weight": real_total_weight,
                "added_by_rule": True
            }
    
    return operator_scores

def get_top_operators(matched_operators1, matched_operators2):
    """
    合并两个文件的匹配结果，返回得分前10名的算子
    规则：每个文件取前5，然后合并去重，按得分排序取前10
    """
    # 分别获取每个文件的前5个算子
    sorted_operators1 = sorted(matched_operators1.items(), 
                              key=lambda x: x[1]["score"], 
                              reverse=True)[:5]
    
    sorted_operators2 = sorted(matched_operators2.items(), 
                              key=lambda x: x[1]["score"], 
                              reverse=True)[:5]
    
    # 合并结果
    all_operators = {}
    
    for operator, score_info in sorted_operators1:
        all_operators[operator] = {
            "score": score_info["score"],
            "source": "file1"
        }
    
    for operator, score_info in sorted_operators2:
        # 如果算子已存在，取较高得分
        if operator in all_operators:
            if score_info["score"] > all_operators[operator]["score"]:
                all_operators[operator] = {
                    "score": score_info["score"],
                    "source": "file2"
                }
        else:
            all_operators[operator] = {
                "score": score_info["score"],
                "source": "file2"
            }
    
    # 按得分排序并返回前10个算子名称
    sorted_all = sorted(all_operators.items(), 
                       key=lambda x: x[1]["score"], 
                       reverse=True)[:10]
    
    return [operator for operator, _ in sorted_all]

def match_operators(input_file, output_file):
    """
    主函数：读取问题文件，为每个问题匹配算子，输出结果
    输入文件格式：仅包含Problem字段的JSON列表
    """
    # 分析算子文件
    print("分析第一个算子文件...")
    operator_keywords1 = analyze_operators(ALL_OPERATORS_FILE1, is_file2=False)
    print(f"第一个文件加载了 {len(operator_keywords1)} 个算子")
    
    print("分析第二个算子文件...")
    operator_keywords2, operator_keyword_weights2 = analyze_operators(ALL_OPERATORS_FILE2, is_file2=True)
    print(f"第二个文件加载了 {len(operator_keywords2)} 个算子")
    
    # 读取问题文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            problems = json.load(f)
    except Exception as e:
        print(f"读取问题文件 {input_file} 时出错: {e}")
        return
    
    # 处理每个问题
    results = []
    for i, problem in enumerate(problems):
        problem_text = problem.get("Problem", "")
        
        if not problem_text:
            print(f"警告：第 {i+1} 个问题没有Problem字段")
            result_problem = problem.copy()
            result_problem["operator"] = []
            results.append(result_problem)
            continue
        
        # 匹配算子
        matched_operators1 = match_operators_to_problem(problem_text, operator_keywords1)
        matched_operators2 = match_operators_to_problem_file2(
            problem_text, operator_keywords2, operator_keyword_weights2
        )
        
        # 获取前10个算子
        top_operators = get_top_operators(matched_operators1, matched_operators2)
        
        # 添加到结果中
        result_problem = problem.copy()
        result_problem["operator"] = top_operators
        results.append(result_problem)
        
        # 打印进度
        if (i + 1) % 100 == 0:
            print(f"已处理 {i+1}/{len(problems)} 个问题")
    
    # 保存结果
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"处理完成！结果已保存到 {output_file}")
    print(f"共处理了 {len(results)} 个问题")
    print(f"匹配算子数量统计：平均每个问题匹配到 {sum(len(p['operator']) for p in results)/len(results):.2f} 个算子")

if __name__ == "__main__":
    # 配置输入输出文件路径
    INPUT_FILE = "/data/train(only P).json"  # 输入文件路径，只包含Problem字段
    OUTPUT_FILE = "/data/train(only P)_pluso.json"  # 输出文件路径
    
    # 检查文件是否存在
    missing_files = []
    
    if not os.path.exists(ALL_OPERATORS_FILE1):
        missing_files.append(ALL_OPERATORS_FILE1)
        
    if not os.path.exists(ALL_OPERATORS_FILE2):
        missing_files.append(ALL_OPERATORS_FILE2)
        
    if not os.path.exists(INPUT_FILE):
        missing_files.append(INPUT_FILE)
    
    if missing_files:
        print("以下文件不存在:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("请修改代码中的文件路径")
    else:
        match_operators(INPUT_FILE, OUTPUT_FILE)