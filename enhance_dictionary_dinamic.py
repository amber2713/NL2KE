import json
import re
import copy
"""这个程序用来对得到的算子对应keyword数据进行加强，使得在训练集中的表现更加好"""
"""本程序加强的原则是对于统计test_weight.py生成的文件中能够出现第一型错误和第二型错误的算子，对于第一型错误，提高在该problem里面出现能够匹配上的keyword在正确算子中的的weight，对于第二型错误则减少weight"""
"""本程序会按照统计的次数进行加强和减少"""
def load_json_file(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return None

def save_json_file(data, file_path):
    """保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"结果已保存到 {file_path}")
    except Exception as e:
        print(f"保存文件 {file_path} 时出错: {e}")

def preprocess_text(text):
    """
    预处理文本：移除公式标记、标点符号，转换为小写
    """
    if not text:
        return ""
    
    # 移除LaTeX公式标记
    text = re.sub(r'\$.*?\$', '', text)
    text = re.sub(r'\\\[.*?\\\]', '', text)
    
    # 移除标点符号
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 转换为小写并移除多余空格
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text

def find_matching_keywords_with_count(problem_text, keywords_list):
    """
    在问题文本中查找匹配的关键词，并统计每个关键词的匹配次数
    keywords_list: 字典列表，每个字典包含key_word和weight
    返回：{关键词: {count: 匹配次数, original_dict: 原始字典}}
    """
    processed_text = preprocess_text(problem_text)
    matched_keywords = {}
    
    for keyword_dict in keywords_list:
        keyword = keyword_dict.get("key_word", "")
        if not keyword:
            continue
            
        # 预处理关键词（去除反斜杠等）
        processed_keyword = keyword.replace('\\', '').lower().strip()
        
        if processed_keyword:
            # 计算关键词在文本中出现的次数
            count = processed_text.count(processed_keyword)
            if count > 0:
                matched_keywords[keyword] = {
                    "count": count,
                    "original_dict": keyword_dict
                }
    
    return matched_keywords

def find_keyword_index(keywords_list, target_keyword):
    """
    在关键词列表中查找特定关键词的索引
    """
    for i, keyword_dict in enumerate(keywords_list):
        if keyword_dict.get("key_word", "") == target_keyword:
            return i
    return -1

def update_operators_increase_weight_dynamic(problems, operator_data, condition_type, min_weight_increase=1):
    """
    增加权重：根据条件为匹配正确的算子增加关键词权重（根据匹配次数动态增加）
    condition_type: 'file2' 或 'file3'
    min_weight_increase: 每个匹配到的关键词最小增加的权重值
    """
    # 创建一个映射：算子名称 -> 索引位置
    operator_index_map = {}
    for idx, item in enumerate(operator_data):
        operator = item.get("Assertional_Logic", "")
        if operator:
            operator_index_map[operator] = idx
    
    # 统计信息
    stats = {
        "total_cases": 0,
        "operators_found": {},
        "keywords_matched": {},  # 记录每个关键词的总匹配次数
        "keywords_weight_increase": {},  # 记录每个关键词增加的权重
        "problems_processed": [],
        "min_weight_increase": min_weight_increase
    }
    
    # 找出符合条件的问題
    filtered_cases = []
    for problem in problems:
        # 根据条件类型选择比较对象
        if condition_type == 'file2':
            comparison = problem.get("Comparison_File2", {})
            f1_score = comparison.get("f1_score", 0)
            # 如果f1_score为0，表示没有匹配到任何实际算子
            condition_met = (f1_score == 0)
            actual_operators_key = "Actual_Operators_File2"
        else:  # file3
            comparison = problem.get("Comparison_File1", {})
            f1_score = comparison.get("f1_score", 0)
            # 如果f1_score不等于1，表示匹配不完美
            condition_met = (f1_score != 1.0)
            actual_operators_key = "Actual_Operators_File1"
        
        if condition_met:
            filtered_cases.append((problem, actual_operators_key))
    
    stats["total_cases"] = len(filtered_cases)
    
    if len(filtered_cases) == 0:
        print(f"  没有找到符合条件的问題，无需处理")
        return operator_data, stats
    
    print(f"  找到 {len(filtered_cases)} 个符合条件的问題")
    
    # 创建一个操作数据的深拷贝，以便修改
    updated_operator_data = copy.deepcopy(operator_data)
    
    # 处理每个符合条件的问題
    for i, (problem, actual_operators_key) in enumerate(filtered_cases, 1):
        problem_text = problem.get("Problem", "")
        actual_operators = problem.get(actual_operators_key, [])
        
        print(f"\n    处理问題 {i}/{len(filtered_cases)}:")
        print(f"      问題: {problem_text[:80]}...")
        print(f"      实际算子: {actual_operators}")
        
        # 记录处理的问題
        problem_record = {
            "problem_index": i,
            "problem_preview": problem_text[:80],
            "actual_operators": actual_operators,
            "matched_keywords_by_operator": {}
        }
        
        # 对每个实际算子进行处理
        for operator in actual_operators:
            # 在算子数据中查找该算子
            if operator in operator_index_map:
                idx = operator_index_map[operator]
                operator_item = updated_operator_data[idx]
                keywords_list = operator_item.get("key_words", [])
                
                # 在问題文本中查找匹配的关键词及匹配次数
                matched_keywords = find_matching_keywords_with_count(problem_text, keywords_list)
                
                if matched_keywords:
                    print(f"      算子 '{operator}' 匹配到 {len(matched_keywords)} 个关键词:")
                    
                    # 更新统计信息
                    if operator not in stats["operators_found"]:
                        stats["operators_found"][operator] = 0
                    stats["operators_found"][operator] += 1
                    
                    # 记录关键词匹配情况
                    for keyword, info in matched_keywords.items():
                        if keyword not in stats["keywords_matched"]:
                            stats["keywords_matched"][keyword] = 0
                        stats["keywords_matched"][keyword] += info["count"]
                    
                    # 记录到问題记录中
                    problem_record["matched_keywords_by_operator"][operator] = matched_keywords
                    
                    # 增加匹配关键词的权重（根据匹配次数动态增加）
                    for keyword, info in matched_keywords.items():
                        match_count = info["count"]
                        # 根据匹配次数计算权重增加值
                        weight_increase = max(match_count, min_weight_increase)
                        
                        keyword_idx = find_keyword_index(keywords_list, keyword)
                        if keyword_idx >= 0:
                            # 关键词已存在，增加权重
                            old_weight = keywords_list[keyword_idx].get("weight", 1)
                            new_weight = old_weight + weight_increase
                            keywords_list[keyword_idx]["weight"] = new_weight
                            
                            # 记录权重增加情况
                            if keyword not in stats["keywords_weight_increase"]:
                                stats["keywords_weight_increase"][keyword] = 0
                            stats["keywords_weight_increase"][keyword] = max(
                                stats["keywords_weight_increase"][keyword], weight_increase
                            )
                            
                            print(f"        关键词 '{keyword}': 匹配{match_count}次，权重从 {old_weight} 增加到 {new_weight}")
                        else:
                            # 关键词不存在，添加新关键词
                            new_keyword_dict = {
                                "key_word": keyword,
                                "weight": weight_increase
                            }
                            keywords_list.append(new_keyword_dict)
                            
                            # 记录权重增加情况
                            if keyword not in stats["keywords_weight_increase"]:
                                stats["keywords_weight_increase"][keyword] = 0
                            stats["keywords_weight_increase"][keyword] = max(
                                stats["keywords_weight_increase"][keyword], weight_increase
                            )
                            
                            print(f"        关键词 '{keyword}': 匹配{match_count}次，添加新关键词，权重为 {weight_increase}")
                    
                    # 更新关键词列表
                    operator_item["key_words"] = keywords_list
                else:
                    print(f"      算子 '{operator}' 没有匹配到任何关键词")
            else:
                print(f"      警告：算子 '{operator}' 在算子文件中未找到")
        
        stats["problems_processed"].append(problem_record)
    
    return updated_operator_data, stats

def update_operators_decrease_weight_dynamic(problems, operator_data, condition_type, base_weight_decrease=1):
    """
    减少权重：对于错误匹配的算子，减少其关键词的权重（根据匹配次数动态减少）
    condition_type: 'file2' 或 'file3'
    base_weight_decrease: 基础权重减少值
    """
    # 创建一个映射：算子名称 -> 索引位置
    operator_index_map = {}
    for idx, item in enumerate(operator_data):
        operator = item.get("Assertional_Logic", "")
        if operator:
            operator_index_map[operator] = idx
    
    # 统计信息
    stats = {
        "total_cases": 0,
        "incorrect_operators_found": {},
        "keywords_decreased": {},
        "keywords_removed": {},
        "keywords_kept": {},
        "problems_processed": []
    }
    
    # 找出符合条件的问題
    filtered_cases = []
    for problem in problems:
        # 根据条件类型选择比较对象
        if condition_type == 'file2':
            expected_operators_key = "Expected_Operators_File2"
            actual_operators_key = "Actual_Operators_File2"
        else:  # file3
            expected_operators_key = "Expected_Operators_File1"
            actual_operators_key = "Actual_Operators_File1"
        
        expected_operators = [item["operator"] for item in problem.get(expected_operators_key, [])]
        actual_operators = problem.get(actual_operators_key, [])
        
        # 找出错误匹配的算子（在Expected中但不在Actual中）
        incorrect_operators = [op for op in expected_operators if op not in actual_operators]
        
        if incorrect_operators:
            filtered_cases.append((problem, incorrect_operators, expected_operators_key))
    
    stats["total_cases"] = len(filtered_cases)
    
    if len(filtered_cases) == 0:
        print(f"  没有找到错误匹配的问題，无需处理")
        return operator_data, stats
    
    print(f"  找到 {len(filtered_cases)} 个有错误匹配的问題")
    
    # 创建一个操作数据的深拷贝，以便修改
    updated_operator_data = copy.deepcopy(operator_data)
    
    # 处理每个有错误匹配的问題
    for i, (problem, incorrect_operators, expected_operators_key) in enumerate(filtered_cases, 1):
        problem_text = problem.get("Problem", "")
        
        print(f"\n    处理问題 {i}/{len(filtered_cases)}:")
        print(f"      问題: {problem_text[:80]}...")
        print(f"      错误匹配的算子: {incorrect_operators}")
        
        # 记录处理的问題
        problem_record = {
            "problem_index": i,
            "problem_preview": problem_text[:80],
            "incorrect_operators": incorrect_operators,
            "keywords_adjusted_by_operator": {}
        }
        
        # 对每个错误匹配的算子进行处理
        for operator in incorrect_operators:
            # 在算子数据中查找该算子
            if operator in operator_index_map:
                idx = operator_index_map[operator]
                operator_item = updated_operator_data[idx]
                keywords_list = operator_item.get("key_words", [])
                
                # 在问題文本中查找匹配的关键词及匹配次数
                matched_keywords = find_matching_keywords_with_count(problem_text, keywords_list)
                
                if matched_keywords:
                    print(f"      错误算子 '{operator}' 匹配到 {len(matched_keywords)} 个关键词:")
                    
                    # 更新统计信息
                    if operator not in stats["incorrect_operators_found"]:
                        stats["incorrect_operators_found"][operator] = 0
                    stats["incorrect_operators_found"][operator] += 1
                    
                    # 记录调整的关键词
                    adjusted_keywords = []
                    
                    # 对每个匹配到的关键词进行处理
                    for keyword, info in matched_keywords.items():
                        keyword_idx = find_keyword_index(keywords_list, keyword)
                        
                        if keyword_idx >= 0:
                            old_weight = keywords_list[keyword_idx].get("weight", 1)
                            match_count = info["count"]
                            
                            print(f"        关键词 '{keyword}': 权重 {old_weight}，在问題中匹配 {match_count} 次")
                            
                            # 根据匹配次数动态计算权重减少值
                            # 匹配次数越多，减少的权重越多（但不超过原始权重）
                            weight_decrease = min(match_count, old_weight)
                            
                            # 判断是否需要调整
                            if old_weight > weight_decrease:
                                # 如果权重大于要减少的值，减少权重
                                new_weight = old_weight - weight_decrease
                                keywords_list[keyword_idx]["weight"] = new_weight
                                
                                adjusted_keywords.append({
                                    "keyword": keyword,
                                    "action": "decreased",
                                    "old_weight": old_weight,
                                    "new_weight": new_weight,
                                    "weight_decrease": weight_decrease
                                })
                                
                                # 更新统计信息
                                if keyword not in stats["keywords_decreased"]:
                                    stats["keywords_decreased"][keyword] = 0
                                stats["keywords_decreased"][keyword] += 1
                                
                            elif old_weight == 1 and match_count > 3:
                                # 如果权重为1且在问題中出现很多次（>3），删除该关键词
                                del keywords_list[keyword_idx]
                                
                                adjusted_keywords.append({
                                    "keyword": keyword,
                                    "action": "removed",
                                    "reason": f"权重为1且出现次数过多（{match_count}次）"
                                })
                                
                                # 更新统计信息
                                if keyword not in stats["keywords_removed"]:
                                    stats["keywords_removed"][keyword] = 0
                                stats["keywords_removed"][keyword] += 1
                            else:
                                # 保留权重为1的关键词
                                adjusted_keywords.append({
                                    "keyword": keyword,
                                    "action": "kept",
                                    "reason": f"保留权重为1（问題中匹配{match_count}次）"
                                })
                                
                                # 更新统计信息
                                if keyword not in stats["keywords_kept"]:
                                    stats["keywords_kept"][keyword] = 0
                                stats["keywords_kept"][keyword] += 1
                        else:
                            print(f"        警告：关键词 '{keyword}' 在算子中未找到")
                    
                    # 记录到问題记录中
                    problem_record["keywords_adjusted_by_operator"][operator] = adjusted_keywords
                    
                    # 更新关键词列表
                    operator_item["key_words"] = keywords_list
                    
                    print(f"      算子 '{operator}' 关键词调整完成")
                else:
                    print(f"      错误算子 '{operator}' 没有匹配到任何关键词，无需调整")
            else:
                print(f"      警告：算子 '{operator}' 在算子文件中未找到")
        
        stats["problems_processed"].append(problem_record)
    
    return updated_operator_data, stats

def process_dynamic_weight_all_files():
    """
    处理所有文件：动态权重增加/减少版本
    """
    # 文件路径设置
    FILE1_PATH = "/output/outcome.json"  # 结果文件，文件格式和test_weight.py的输出文件相同
    FILE2_PATH = "/operator1/fixed_Declaration.json"  # 算子关键词文件2加强前的定义类型算子keywords对应文件
    FILE3_PATH = "/operator1/fixed_others.json"  # 算子关键词文件3 加强前的其他类型算子keywords对应文件
    OUTPUT_PATH2 = "/operator2/fixed_Declaration.json"  # 输出文件2 加强后的文件2
    OUTPUT_PATH3 = "/operator2/fixed_others.json"  # 输出文件3 加强后的文件3
    
    MIN_WEIGHT_INCREASE = 1  # 每个匹配到的关键词最小增加的权重值
    BASE_WEIGHT_DECREASE = 1  # 基础权重减少值
    
    print("="*80)
    print("动态权重增加/减少版本 - 处理所有文件")
    print("="*80)
    
    # 加载文件1（结果文件）
    print(f"加载文件1: {FILE1_PATH}")
    file1_data = load_json_file(FILE1_PATH)
    if not file1_data:
        return
    
    # 提取问題列表
    if "problems" in file1_data:
        problems = file1_data["problems"]
    else:
        problems = file1_data  # 假设直接是问題列表
    
    print(f"文件1中总问題数: {len(problems)}")
    
    # 加载文件2（算子关键词文件2）
    print(f"\n加载文件2: {FILE2_PATH}")
    file2_data = load_json_file(FILE2_PATH)
    if not file2_data:
        return
    
    print(f"文件2中算子数量: {len(file2_data)}")
    
    # 加载文件3（算子关键词文件3）
    print(f"\n加载文件3: {FILE3_PATH}")
    file3_data = load_json_file(FILE3_PATH)
    if not file3_data:
        return
    
    print(f"文件3中算子数量: {len(file3_data)}")
    
    # 处理文件2：先减少权重（错误匹配），再增加权重（正确匹配）
    print("\n" + "="*60)
    print("处理文件2（Comparison_File2为0的问題）")
    print("="*60)
    
    # 1. 减少权重：对于错误匹配的算子
    print("\n1. 减少权重（错误匹配的算子，动态减少）:")
    file2_data_after_decrease, stats_file2_decrease = update_operators_decrease_weight_dynamic(
        problems, file2_data, 'file2', BASE_WEIGHT_DECREASE
    )
    
    # 2. 增加权重：对于正确匹配的算子
    print("\n2. 增加权重（正确匹配的算子，动态增加）:")
    updated_file2_data, stats_file2_increase = update_operators_increase_weight_dynamic(
        problems, file2_data_after_decrease, 'file2', MIN_WEIGHT_INCREASE
    )
    
    # 保存更新后的文件2
    save_json_file(updated_file2_data, OUTPUT_PATH2)
    
    # 处理文件3：先减少权重（错误匹配），再增加权重（正确匹配）
    print("\n" + "="*60)
    print("处理文件3（Comparison_File1不等于1的问題）")
    print("="*60)
    
    # 1. 减少权重：对于错误匹配的算子
    print("\n1. 减少权重（错误匹配的算子，动态减少）:")
    file3_data_after_decrease, stats_file3_decrease = update_operators_decrease_weight_dynamic(
        problems, file3_data, 'file3', BASE_WEIGHT_DECREASE
    )
    
    # 2. 增加权重：对于正确匹配的算子
    print("\n2. 增加权重（正确匹配的算子，动态增加）:")
    updated_file3_data, stats_file3_increase = update_operators_increase_weight_dynamic(
        problems, file3_data_after_decrease, 'file3', MIN_WEIGHT_INCREASE
    )
    
    # 保存更新后的文件3
    save_json_file(updated_file3_data, OUTPUT_PATH3)
    
    # 打印总体统计信息
    print("\n" + "="*80)
    print("处理完成！总体统计信息:")
    print("="*80)
    
    print(f"\n文件1中总问題数: {len(problems)}")
    
    # 文件2统计
    print(f"\n文件2处理统计:")
    print(f"  减少权重 - 有错误匹配的问題数: {stats_file2_decrease['total_cases']}")
    print(f"  减少权重 - 错误匹配算子数: {len(stats_file2_decrease['incorrect_operators_found'])}")
    print(f"  减少权重 - 减少权重的关键词数: {len(stats_file2_decrease['keywords_decreased'])}")
    print(f"  减少权重 - 完全删除的关键词数: {len(stats_file2_decrease['keywords_removed'])}")
    print(f"  减少权重 - 保留的关键词数: {len(stats_file2_decrease['keywords_kept'])}")
    
    print(f"\n  增加权重 - Comparison_File2为0的问題数: {stats_file2_increase['total_cases']}")
    print(f"  增加权重 - 正确匹配算子数: {len(stats_file2_increase['operators_found'])}")
    print(f"  增加权重 - 最小权重增加值: {MIN_WEIGHT_INCREASE}")
    
    # 文件3统计
    print(f"\n文件3处理统计:")
    print(f"  减少权重 - 有错误匹配的问題数: {stats_file3_decrease['total_cases']}")
    print(f"  减少权重 - 错误匹配算子数: {len(stats_file3_decrease['incorrect_operators_found'])}")
    print(f"  减少权重 - 减少权重的关键词数: {len(stats_file3_decrease['keywords_decreased'])}")
    print(f"  减少权重 - 完全删除的关键词数: {len(stats_file3_decrease['keywords_removed'])}")
    print(f"  减少权重 - 保留的关键词数: {len(stats_file3_decrease['keywords_kept'])}")
    
    print(f"\n  增加权重 - Comparison_File1不等于1的问題数: {stats_file3_increase['total_cases']}")
    print(f"  增加权重 - 正确匹配算子数: {len(stats_file3_increase['operators_found'])}")
    print(f"  增加权重 - 最小权重增加值: {MIN_WEIGHT_INCREASE}")
    
    # 创建完整结果
    full_result = {
        "updated_operators_file2": updated_file2_data,
        "updated_operators_file3": updated_file3_data,
        "statistics": {
            "file2_decrease": stats_file2_decrease,
            "file2_increase": stats_file2_increase,
            "file3_decrease": stats_file3_decrease,
            "file3_increase": stats_file3_increase
        },
        "config": {
            "file1_path": FILE1_PATH,
            "file2_path": FILE2_PATH,
            "file3_path": FILE3_PATH,
            "output_path2": OUTPUT_PATH2,
            "output_path3": OUTPUT_PATH3,
            "min_weight_increase": MIN_WEIGHT_INCREASE,
            "base_weight_decrease": BASE_WEIGHT_DECREASE
        }
    }
    
    # 保存完整结果
    full_output_path = "operator2/full_result_dynamic_weight.json"
    save_json_file(full_result, full_output_path)
    
    print(f"\n更新后的文件2已保存到: {OUTPUT_PATH2}")
    print(f"更新后的文件3已保存到: {OUTPUT_PATH3}")
    print(f"完整结果已保存到: {full_output_path}")
    
    return updated_file2_data, updated_file3_data

if __name__ == "__main__":
    process_dynamic_weight_all_files()