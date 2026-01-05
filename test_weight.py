import json
import jieba
from collections import Counter
import os
import re

# 直接在代码中指定3个文件路径
ALL_OPERATORS_FILE1 = "/operator/fixed_others.json"  # 第一个算子文件
ALL_OPERATORS_FILE2 = "/operator/fixed_Declaration.json"  # 第二个算子文件（与第一个格式相同）
PROBLEM_FILE = "/data/train/batch_1000per/chunk_0019.json"
OUTPUT_FILE = "/output/0019.json"

# 配置参数
SCORE_THRESHOLD = 10  # 得分阈值，超过此值的算子都算有效训练时可以调整
REAL_OPERATOR_THRESHOLD = 26  # 文件2中其他算子的阈值，超过此值才考虑训练时可以调整

def analyze_operators(operators_file, is_file2=False):
    """
    从算子文件中分析算子-关键词映射
    新格式：每个关键词是字典，包含key_word和weight
    is_file2: 如果是第二个文件，记录关键词权重
    """
    operator_keywords = {}  # 算子 -> 关键词列表（字典格式）
    operator_keyword_weights = {}  # 算子 -> 关键词到权重的映射（仅用于文件2）
    
    try:
        with open(operators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            operator = item.get("Assertional_Logic")
            keywords = item.get("key_words", [])
            
            if operator:
                operator_keywords[operator] = keywords
                
                # 如果是文件2，建立关键词到权重的映射
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

def load_all_operators(operators_file):
    """
    从文件中加载所有算子名称
    """
    try:
        with open(operators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_operators = [item.get("Assertional_Logic") for item in data if item.get("Assertional_Logic")]
        print(f"从 {operators_file} 加载了 {len(all_operators)} 个算子")
        return all_operators
    except Exception as e:
        print(f"读取算子文件 {operators_file} 时出错: {e}")
        return []

def preprocess_text(text):
    """
    预处理文本：移除公式标记但保留内容，保留绝对值符号|，移除其他标点符号，转换为小写
    """
    if not text:
        return ""
    
    # 1. 移除公式标记但保留内容
    # 移除内联公式标记 $...$，保留内容
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    # 移除行间公式标记 \[...\]，保留内容
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    
    # 2. 处理LaTeX中的绝对值符号（\left|、\right|、| 等）
    # 将 \left| 和 \right| 替换为普通的 |
    text = re.sub(r'\\left\||\\right\|', '|', text)
    
    # 3. 处理\mid（集合中的分隔符），通常也表示为|
    text = re.sub(r'\\mid\b', '|', text)
    
    # 4. 移除标点符号，但保留|、数字、字母和空格
    # 保留的字符：字母、数字、空格、|、=、+、-、*、/、^、_、<、>、(、)、[、]、{、}等数学符号
    # 主要移除：.,!?;:'"等自然语言标点
    text = re.sub(r'[^\w\s\|=+\-*/^_<>()\[\]{}]', ' ', text)
    
    # 5. 转换为小写并移除多余空格
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text

def match_operators_to_problem(problem_text, operator_keywords):
    """
    将算子匹配到问题文本，返回得分超过阈值的所有算子（通用版本，用于文件1）
    新格式：关键词是字典，使用weight作为匹配得分
    """
    # 预处理问题文本
    processed_text = preprocess_text(problem_text)
    
    # 分词
    words = list(jieba.cut(processed_text))
    
    # 计算每个算子的匹配得分
    operator_scores = {}
    
    for operator, keywords in operator_keywords.items():
        score = 0
        
        # 直接关键词匹配 - 使用权重
        for kw_dict in keywords:
            keyword = kw_dict.get("key_word", "")
            weight = kw_dict.get("weight", 0)
            if keyword and keyword in processed_text:
                score += weight  # 使用权重而不是固定加1
        
        # 基于分词的匹配 - 使用权重
        for word in words:
            for kw_dict in keywords:
                keyword = kw_dict.get("key_word", "")
                weight = kw_dict.get("weight", 0)
                if keyword and word in keyword and len(word) > 2:  # 只考虑长度大于2的词
                    score += 0.5 * weight  # 部分匹配使用权重的一半
        
        # 考虑算子关键词数量（关键词越多，匹配可能性越大）
        keyword_count = len(keywords)
        total_weight = sum(kw_dict.get("weight", 0) for kw_dict in keywords)
        diversity_bonus = min(total_weight / 200, 1.0)  # 基于总权重计算奖励，最多1分
        
        # 最终得分
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
    """
    将算子匹配到问题文本，返回得分超过阈值的所有算子（用于文件2，有Real算子特殊规则）
    规则：
    1. 先不计算Real算子的得分
    2. 计算其他19个算子的得分
    3. 如果其他算子中有得分超过REAL_OPERATOR_THRESHOLD的，就取这些算子中得分最高的前5个
    4. 如果其他算子中没有任何一个得分超过阈值，就只选取Real算子
    
    新格式：关键词是字典，使用weight作为匹配得分
    """
    # 预处理问题文本
    processed_text = preprocess_text(problem_text)
    
    # 分词
    words = list(jieba.cut(processed_text))
    
    # 计算每个算子的匹配得分（不包括Real）
    operator_scores = {}
    real_operator_score = 0
    
    for operator, keywords in operator_keywords.items():
        score = 0
        
        # 如果是文件2且有关键词权重信息
        if operator in operator_keyword_weights:
            keyword_weight_map = operator_keyword_weights[operator]
            
            # 直接关键词匹配 - 使用权重
            for keyword, weight in keyword_weight_map.items():
                if keyword in processed_text:
                    score += weight  # 使用权重
            
            # 基于分词的匹配 - 使用权重
            for word in words:
                for keyword, weight in keyword_weight_map.items():
                    if word in keyword and len(word) > 2:  # 只考虑长度大于2的词
                        score += 0.5 * weight  # 部分匹配使用权重的一半
        else:
            # 如果没有权重信息，使用原始方法（从字典列表获取）
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
        
        # 考虑算子关键词数量（关键词越多，匹配可能性越大）
        keyword_count = len(keywords)
        total_weight = sum(kw_dict.get("weight", 0) for kw_dict in keywords)
        diversity_bonus = min(total_weight / 200, 1.0)  # 基于总权重计算奖励，最多1分
        
        # 最终得分
        final_score = score + diversity_bonus
        
        # 如果是Real算子，记录其得分但不加入operator_scores
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
    # 检查是否有其他算子得分超过REAL_OPERATOR_THRESHOLD
    has_high_scoring_operator = False
    for operator, score_info in operator_scores.items():
        if score_info["score"] >= REAL_OPERATOR_THRESHOLD:
            has_high_scoring_operator = True
            break
    
    # 如果没有其他算子得分超过阈值，就只添加Real算子
    if not has_high_scoring_operator:
        operator_scores = {}
        if real_operator_score > 0:
            # 获取Real算子的信息
            real_keywords = operator_keywords.get("Real", [])
            real_keyword_count = len(real_keywords)
            real_total_weight = sum(kw_dict.get("weight", 0) for kw_dict in real_keywords)
            
            operator_scores["Real"] = {
                "score": real_operator_score,
                "base_score": real_operator_score,
                "diversity_bonus": 0,
                "keyword_count": real_keyword_count,
                "total_weight": real_total_weight,
                "added_by_rule": True  # 标记是通过规则添加的
            }
    
    return operator_scores

def get_top_5_operators(matched_operators, is_file2=False):
    """
    从匹配的算子中选取得分前5名的算子
    """
    # 按得分排序
    sorted_operators = sorted(matched_operators.items(), 
                             key=lambda x: x[1]["score"], 
                             reverse=True)
    
    # 如果是文件2，检查是否有通过规则添加的Real算子
    if is_file2:
        real_included = any(op == "Real" and info.get("added_by_rule", False) 
                           for op, info in matched_operators.items())
        
        # 如果Real是通过规则添加的，确保它在top5中
        if real_included:
            # 分离Real和其他算子
            real_operator = None
            other_operators = []
            
            for operator, score_info in sorted_operators:
                if operator == "Real" and score_info.get("added_by_rule", False):
                    real_operator = (operator, score_info)
                else:
                    other_operators.append((operator, score_info))
            
            # 如果只有Real，直接返回Real
            if real_operator and len(other_operators) == 0:
                top_5 = [real_operator]
            elif real_operator:
                # 取前4个其他算子
                top_others = other_operators[:4]
                # 将Real加入
                top_5 = [real_operator] + top_others
            else:
                # 如果没找到Real（虽然不太可能），直接取前5
                top_5 = sorted_operators[:5]
        else:
            # 如果没有通过规则添加Real，直接取前5
            top_5 = sorted_operators[:5]
    else:
        # 文件1的算子直接取前5
        top_5 = sorted_operators[:5]
    
    # 转换为期望的格式
    expected_operators = []
    for operator, score_info in top_5:
        expected_operators.append({
            "operator": operator,
            "score": score_info["score"],
            "base_score": score_info.get("base_score", 0),
            "diversity_bonus": score_info.get("diversity_bonus", 0),
            "keyword_count": score_info.get("keyword_count", 0),
            "total_weight": score_info.get("total_weight", 0),
            "added_by_rule": score_info.get("added_by_rule", False) if is_file2 else False
        })
    
    return expected_operators

def extract_actual_operators(declaration, facts, query, all_operators1, all_operators2):
    """
    从Declaration、Facts、Query中提取实际使用的算子
    返回两个列表：file1中的实际算子和file2中的实际算子
    """
    actual_operators_all = set()
    actual_operators_file1 = set()
    actual_operators_file2 = set()
    
    # 合并所有文本
    all_text = f"{declaration} {facts} {query}"
    
    # 在文本中查找所有算子（文件1）
    for operator in all_operators1:
        # 使用正则表达式确保匹配完整的算子名称
        pattern = r'\b' + re.escape(operator) + r'\b'
        if re.search(pattern, all_text, re.IGNORECASE):
            actual_operators_all.add(operator)
            actual_operators_file1.add(operator)
    
    # 在文本中查找所有算子（文件2）
    for operator in all_operators2:
        # 使用正则表达式确保匹配完整的算子名称
        pattern = r'\b' + re.escape(operator) + r'\b'
        if re.search(pattern, all_text, re.IGNORECASE):
            actual_operators_all.add(operator)
            actual_operators_file2.add(operator)
    
    return {
        "all": list(actual_operators_all),
        "file1": list(actual_operators_file1),
        "file2": list(actual_operators_file2)
    }

def process_problems_with_comparison():
    """
    处理问题文件，为每个问题匹配算子，并与实际转换结果比较
    """
    # 分析两个算子文件
    print("分析第一个算子文件...")
    operator_keywords1 = analyze_operators(ALL_OPERATORS_FILE1, is_file2=False)
    print(f"第一个文件加载了 {len(operator_keywords1)} 个算子")
    
    print("分析第二个算子文件...")
    operator_keywords2, operator_keyword_weights2 = analyze_operators(ALL_OPERATORS_FILE2, is_file2=True)
    print(f"第二个文件加载了 {len(operator_keywords2)} 个算子")
    
    # 加载所有算子名称
    all_operators1 = load_all_operators(ALL_OPERATORS_FILE1)
    all_operators2 = load_all_operators(ALL_OPERATORS_FILE2)
    
    if not all_operators1 or not all_operators2:
        print("错误：无法加载算子列表")
        return
    
    # 读取问题文件
    try:
        with open(PROBLEM_FILE, 'r', encoding='utf-8') as f:
            problems = json.load(f)
    except Exception as e:
        print(f"读取问题文件 {PROBLEM_FILE} 时出错: {e}")
        return
    
    results = []
    comparison_stats = {
        "total_problems": len(problems),
        # 文件1的统计
        "correct_matches_file1": 0,
        "partial_matches_file1": 0,
        "no_matches_file1": 0,
        "precision_file1": 0,
        "recall_file1": 0,
        "f1_score_file1": 0,
        # 文件2的统计
        "correct_matches_file2": 0,
        "partial_matches_file2": 0,
        "no_matches_file2": 0,
        "precision_file2": 0,
        "recall_file2": 0,
        "f1_score_file2": 0,
        "real_operator_added_count": 0,  # 统计通过规则添加Real算子的次数
        # 合并统计
        "combined_precision": 0,
        "combined_recall": 0,
        "combined_f1_score": 0
    }
    
    for problem in problems:
        problem_text = problem.get("Problem", "")
        declaration = problem.get("Declaration", "")
        facts = problem.get("Facts", "")
        query = problem.get("Query", "")
        
        # 分别匹配两个文件的算子
        matched_operators1 = match_operators_to_problem(problem_text, operator_keywords1)
        matched_operators2 = match_operators_to_problem_file2(problem_text, operator_keywords2, operator_keyword_weights2)
        
        # 选取得分前5名的算子作为expected_operators
        expected_operators1 = get_top_5_operators(matched_operators1, is_file2=False)
        expected_operators2 = get_top_5_operators(matched_operators2, is_file2=True)
        
        # 统计通过规则添加Real算子的情况
        for op_info in expected_operators2:
            if op_info.get("added_by_rule", False) and op_info["operator"] == "Real":
                comparison_stats["real_operator_added_count"] += 1
                break
        
        # 提取实际使用的算子
        actual_operators_result = extract_actual_operators(declaration, facts, query, all_operators1, all_operators2)
        actual_operators_all = actual_operators_result["all"]
        actual_operators_file1 = actual_operators_result["file1"]
        actual_operators_file2 = actual_operators_result["file2"]
        
        # 分别比较两个文件的匹配结果
        expected_ops_list1 = [item["operator"] for item in expected_operators1]
        expected_ops_list2 = [item["operator"] for item in expected_operators2]
        
        # 文件1的匹配：只比较文件1的算子
        correct_matches1 = set(expected_ops_list1) & set(actual_operators_file1)
        
        # 文件2的匹配：只比较文件2的算子
        correct_matches2 = set(expected_ops_list2) & set(actual_operators_file2)
        
        # 计算匹配精度（文件1）
        precision1 = len(correct_matches1) / len(expected_ops_list1) if expected_ops_list1 else 0
        recall1 = len(correct_matches1) / len(actual_operators_file1) if actual_operators_file1 else 0
        f1_score1 = 2 * precision1 * recall1 / (precision1 + recall1) if (precision1 + recall1) > 0 else 0
        
        # 计算匹配精度（文件2）
        precision2 = len(correct_matches2) / len(expected_ops_list2) if expected_ops_list2 else 0
        recall2 = len(correct_matches2) / len(actual_operators_file2) if actual_operators_file2 else 0
        f1_score2 = 2 * precision2 * recall2 / (precision2 + recall2) if (precision2 + recall2) > 0 else 0
        
        # 计算合并的匹配精度
        combined_expected_ops = expected_ops_list1 + expected_ops_list2
        combined_correct_matches = list(correct_matches1) + list(correct_matches2)
        combined_precision = len(combined_correct_matches) / len(combined_expected_ops) if combined_expected_ops else 0
        combined_recall = len(combined_correct_matches) / len(actual_operators_all) if actual_operators_all else 0
        combined_f1_score = 2 * combined_precision * combined_recall / (combined_precision + combined_recall) if (combined_precision + combined_recall) > 0 else 0
        
        # 更新统计信息（文件1）
        if len(correct_matches1) > 0:
            if len(correct_matches1) == len(actual_operators_file1) and len(correct_matches1) == len(expected_ops_list1):
                comparison_stats["correct_matches_file1"] += 1
            else:
                comparison_stats["partial_matches_file1"] += 1
        else:
            comparison_stats["no_matches_file1"] += 1
        
        # 更新统计信息（文件2）
        if len(correct_matches2) > 0:
            if len(correct_matches2) == len(actual_operators_file2) and len(correct_matches2) == len(expected_ops_list2):
                comparison_stats["correct_matches_file2"] += 1
            else:
                comparison_stats["partial_matches_file2"] += 1
        else:
            comparison_stats["no_matches_file2"] += 1
        
        # 添加到结果中
        result_problem = problem.copy()
        result_problem["Matched_Operators_File1"] = matched_operators1
        result_problem["Expected_Operators_File1"] = expected_operators1
        result_problem["Matched_Operators_File2"] = matched_operators2
        result_problem["Expected_Operators_File2"] = expected_operators2
        result_problem["Actual_Operators_File1"] = actual_operators_file1
        result_problem["Actual_Operators_File2"] = actual_operators_file2
        result_problem["Actual_Operators_All"] = actual_operators_all
        result_problem["Comparison_File1"] = {
            "correct_matches": list(correct_matches1),
            "precision": precision1,
            "recall": recall1,
            "f1_score": f1_score1
        }
        result_problem["Comparison_File2"] = {
            "correct_matches": list(correct_matches2),
            "precision": precision2,
            "recall": recall2,
            "f1_score": f1_score2
        }
        result_problem["Comparison_Combined"] = {
            "correct_matches": combined_correct_matches,
            "precision": combined_precision,
            "recall": combined_recall,
            "f1_score": combined_f1_score
        }
        results.append(result_problem)
    
    # 计算总体统计
    comparison_stats["precision_file1"] = sum(p["Comparison_File1"]["precision"] for p in results) / len(results)
    comparison_stats["recall_file1"] = sum(p["Comparison_File1"]["recall"] for p in results) / len(results)
    comparison_stats["f1_score_file1"] = sum(p["Comparison_File1"]["f1_score"] for p in results) / len(results)
    
    comparison_stats["precision_file2"] = sum(p["Comparison_File2"]["precision"] for p in results) / len(results)
    comparison_stats["recall_file2"] = sum(p["Comparison_File2"]["recall"] for p in results) / len(results)
    comparison_stats["f1_score_file2"] = sum(p["Comparison_File2"]["f1_score"] for p in results) / len(results)
    
    comparison_stats["combined_precision"] = sum(p["Comparison_Combined"]["precision"] for p in results) / len(results)
    comparison_stats["combined_recall"] = sum(p["Comparison_Combined"]["recall"] for p in results) / len(results)
    comparison_stats["combined_f1_score"] = sum(p["Comparison_Combined"]["f1_score"] for p in results) / len(results)
    
    # 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "problems": results,
            "comparison_stats": comparison_stats,
            "config": {
                "score_threshold": SCORE_THRESHOLD,
                "real_operator_threshold": REAL_OPERATOR_THRESHOLD,
                "all_operators_file1": ALL_OPERATORS_FILE1,
                "all_operators_file2": ALL_OPERATORS_FILE2,
                "problem_file": PROBLEM_FILE
            }
        }, f, indent=2, ensure_ascii=False)
    
    # 打印总体统计
    print("\n总体匹配统计:")
    print("=" * 80)
    print(f"总问题数: {comparison_stats['total_problems']}")
    
    print(f"\n第一个算子文件 (每个问题top5算子):")
    print("-" * 50)
    print(f"  完全匹配: {comparison_stats['correct_matches_file1']}")
    print(f"  部分匹配: {comparison_stats['partial_matches_file1']}")
    print(f"  无匹配: {comparison_stats['no_matches_file1']}")
    print(f"  平均精确率: {comparison_stats['precision_file1']:.4f}")
    print(f"  平均召回率: {comparison_stats['recall_file1']:.4f}")
    print(f"  平均F1分数: {comparison_stats['f1_score_file1']:.4f}")
    
    print(f"\n第二个算子文件 (每个问题top5算子):")
    print("-" * 50)
    print(f"  完全匹配: {comparison_stats['correct_matches_file2']}")
    print(f"  部分匹配: {comparison_stats['partial_matches_file2']}")
    print(f"  无匹配: {comparison_stats['no_matches_file2']}")
    print(f"  平均精确率: {comparison_stats['precision_file2']:.4f}")
    print(f"  平均召回率: {comparison_stats['recall_file2']:.4f}")
    print(f"  平均F1分数: {comparison_stats['f1_score_file2']:.4f}")
    print(f"  通过规则添加Real算子的次数: {comparison_stats['real_operator_added_count']}")
    
    print(f"\n合并两个文件 (每个问题top10算子):")
    print("-" * 50)
    print(f"  平均精确率: {comparison_stats['combined_precision']:.4f}")
    print(f"  平均召回率: {comparison_stats['combined_recall']:.4f}")
    print(f"  平均F1分数: {comparison_stats['combined_f1_score']:.4f}")
    
    print(f"\n使用阈值:")
    print("-" * 50)
    print(f"  通用得分阈值: {SCORE_THRESHOLD}")
    print(f"  文件2其他算子阈值: {REAL_OPERATOR_THRESHOLD}")
    
    print(f"\n文件2特殊规则说明:")
    print("-" * 50)
    print("  1. 先不计算Real算子的得分")
    print("  2. 计算其他19个算子的得分")
    print("  3. 如果有其他算子得分超过阈值，就取这些算子中得分最高的前5个")
    print("  4. 如果没有其他算子得分超过阈值，就只选取Real算子")
    
    print(f"\n关键词权重计分规则:")
    print("-" * 50)
    print("  1. 关键词匹配时，直接使用权重值作为得分")
    print("  2. 部分匹配（分词匹配）使用权重值的一半作为得分")
    print("  3. 多样性奖励基于关键词总权重计算")
    
    print(f"\n处理完成！结果已保存到 {OUTPUT_FILE}")
    
    return results, comparison_stats

if __name__ == "__main__":
    # 检查文件是否存在
    missing_files = []
    
    if not os.path.exists(ALL_OPERATORS_FILE1):
        missing_files.append(ALL_OPERATORS_FILE1)
        
    if not os.path.exists(ALL_OPERATORS_FILE2):
        missing_files.append(ALL_OPERATORS_FILE2)
        
    if not os.path.exists(PROBLEM_FILE):
        missing_files.append(PROBLEM_FILE)
    
    if missing_files:
        print("以下文件不存在:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("请修改代码中的文件路径")
    else:
        process_problems_with_comparison()