import json
import re
from typing import List, Dict, Any
from collections import defaultdict
'''将短语打断成词'''
def get_stopwords() -> set:
    """
    获取停用词列表
    """
    # 英文停用词
    english_stopwords = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
        'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'hers'
    }
    
    # 数字
    numbers = {str(i) for i in range(10)}
    
    # 无意义的符号
    symbols = {'/', '\\', '|', '-', '_', '+', '=', '(', ')', '[', ']', '{', '}',
               '<', '>', ':', ';', ',', '.', '!', '?', '"', "'", '`', '~', '@',
               '#', '$', '%', '^', '&', '*', ' ', 'no'}
    
    # 数学符号（保留数学表达式中的符号）
    math_symbols = {'+', '-', '=', '×', '÷', '±', '≠', '≤', '≥', '≈', '≡', '∞'}
    
    # 合并停用词（排除数学符号）
    all_stopwords = english_stopwords | numbers | (symbols - math_symbols)
    
    return all_stopwords

def split_keywords_with_weights(keywords_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将带权重的关键词列表拆分成单个单词和表达式，并重新分配权重
    
    Args:
        keywords_data: 带权重的关键词列表，格式为 [{"key_word": "短语", "weight": 权重}, ...]
    
    Returns:
        拆分后带权重的关键词列表
    """
    split_keywords_dict = defaultdict(int)  # 用于存储关键词和累计权重
    stopwords = get_stopwords()
    
    for kw_data in keywords_data:
        keyword = kw_data.get("key_word", "")
        original_weight = kw_data.get("weight", 1)
        
        if not keyword:
            continue
        
        # 处理同时包含文本和数学表达式的情况
        math_pattern = r'(?:[A-Za-zα-ωΑ-Ω₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎]+\s*[=≠≤≥≈≡]\s*[^=]+?|\b[A-Za-z]+\d*\b\s*=\s*[^=]+?)'
        math_matches = list(re.finditer(math_pattern, keyword))
        
        if math_matches:
            # 分离文本和数学部分
            last_end = 0
            math_expressions = []
            text_parts = []
            
            for match in math_matches:
                # 提取数学表达式前的文本部分
                text_part = keyword[last_end:match.start()].strip()
                if text_part:
                    text_parts.extend(re.split(r'[\s,;.]+', text_part))
                
                # 提取数学表达式
                math_expr = match.group().strip()
                if math_expr:
                    math_expressions.append(math_expr)
                
                last_end = match.end()
            
            # 处理最后一个数学表达式后的文本
            text_part = keyword[last_end:].strip()
            if text_part:
                text_parts.extend(re.split(r'[\s,;.]+', text_part))
            
            # 合并所有部分
            all_parts = text_parts + math_expressions
        else:
            # 没有数学表达式，按普通文本处理
            all_parts = re.split(r'[\s,;.]+', keyword)
        
        # 过滤停用词，统计每个部分的权重
        valid_parts = []
        for part in all_parts:
            clean_part = part.strip()
            if (clean_part and 
                clean_part.lower() not in stopwords and 
                len(clean_part) > 1):
                valid_parts.append(clean_part.lower())  # 统一转为小写
        
        # 如果没有有效的部分，跳过
        if not valid_parts:
            continue
        
        # 将原权重平均分配给各个有效部分
        weight_per_part = original_weight / len(valid_parts)
        
        # 累加权重到字典中
        for part in valid_parts:
            split_keywords_dict[part] += weight_per_part
    
    # 将权重字典转换为keywords+weight格式，并限制权重在1-15之间
    result_keywords = []
    for keyword, total_weight in split_keywords_dict.items():
        # 限制权重在1-15范围内
        normalized_weight = int(round(max(1, min(15, total_weight))))
        result_keywords.append({
            "key_word": keyword,
            "weight": normalized_weight
        })
    
    # 按权重降序排序，权重相同按字母顺序排序
    result_keywords.sort(key=lambda x: (-x["weight"], x["key_word"]))
    
    return result_keywords

def normalize_keywords_weight(keywords_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    标准化关键词权重，确保所有权重在1-15之间，并按权重降序排序
    
    Args:
        keywords_data: 带权重的关键词列表
    
    Returns:
        标准化后的关键词列表
    """
    # 确保所有权重在1-15之间
    for kw in keywords_data:
        if "weight" in kw:
            kw["weight"] = int(max(1, min(15, kw["weight"])))
    
    # 按权重降序排序，权重相同按字母顺序排序
    keywords_data.sort(key=lambda x: (-x["weight"], x["key_word"]))
    
    return keywords_data

def process_json_file():
    """
    处理JSON文件，拆分key_words并去重，保持keywords+weight格式
    """
    # 直接在代码中指定输入和输出文件名
    input_file = 'data_phrases.json'#需要被打断的短语
    output_file = 'data_out.json'#打断成词后的结果
    
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理每个条目
        processed_data = []
        total_original_keywords = 0
        total_processed_keywords = 0
        
        for i, item in enumerate(data):
            assertional_logic = item.get("Assertional_Logic", "")
            original_keywords = item.get("key_words", [])
            
            # 确保输入是keywords+weight格式
            if original_keywords and isinstance(original_keywords[0], str):
                # 如果输入是纯字符串列表，转换为keywords+weight格式
                original_keywords_weighted = [
                    {"key_word": kw, "weight": 5}  # 默认权重为5
                    for kw in original_keywords if kw.strip()
                ]
            else:
                # 已经是keywords+weight格式
                original_keywords_weighted = original_keywords
            
            # 拆分关键词并重新分配权重
            split_keywords = split_keywords_with_weights(original_keywords_weighted)
            
            # 去重：相同关键词取最大权重
            keyword_dict = {}
            for kw in split_keywords:
                key = kw["key_word"]
                weight = kw["weight"]
                if key not in keyword_dict or weight > keyword_dict[key]:
                    keyword_dict[key] = weight
            
            # 转换回keywords+weight格式
            unique_keywords = [
                {"key_word": key, "weight": weight}
                for key, weight in keyword_dict.items()
            ]
            
            # 标准化权重并排序
            unique_keywords = normalize_keywords_weight(unique_keywords)
            
            processed_item = {
                "Assertional_Logic": assertional_logic,
                "key_words": unique_keywords
            }
            processed_data.append(processed_item)
            
            # 更新统计
            total_original_keywords += len(original_keywords)
            total_processed_keywords += len(unique_keywords)
            
            # 打印处理详情（前5个条目）
            if i < 5:
                print(f"处理条目 {i+1}: {assertional_logic}")
                print(f"  原始关键词数: {len(original_keywords)}")
                print(f"  处理后关键词数: {len(unique_keywords)}")
                
                # 显示前3个处理后的关键词
                if unique_keywords:
                    print(f"  处理后关键词示例:")
                    for j, kw in enumerate(unique_keywords[:3]):
                        print(f"    {kw['key_word']}: 权重 {kw['weight']}")
                    if len(unique_keywords) > 3:
                        print(f"    ... 还有 {len(unique_keywords) - 3} 个关键词")
                print("-" * 50)
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n处理完成！结果已保存到 {output_file}")
        
        # 打印处理结果摘要
        print("\n处理结果摘要：")
        print(f"总条目数: {len(processed_data)}")
        print(f"总原始关键词数: {total_original_keywords}")
        print(f"总处理后关键词数: {total_processed_keywords}")
        
        if total_original_keywords > 0:
            reduction_percent = ((total_original_keywords - total_processed_keywords) / total_original_keywords * 100)
            print(f"关键词减少比例: {reduction_percent:.1f}%")
        
        # 显示权重分布
        print("\n权重分布统计:")
        weight_distribution = defaultdict(int)
        for item in processed_data:
            for kw in item["key_words"]:
                weight = kw["weight"]
                weight_distribution[weight] += 1
        
        # 按权重排序显示分布
        for weight in sorted(weight_distribution.keys()):
            count = weight_distribution[weight]
            print(f"  权重 {weight}: {count} 个关键词")
        
        # 显示部分处理后的结果
        print("\n处理后结果示例 (前3个条目):")
        for i, item in enumerate(processed_data[:3]):
            print(f"\n{i+1}. {item['Assertional_Logic']}: {len(item['key_words'])} 个关键词")
            for j, kw in enumerate(item['key_words'][:3]):
                print(f"   {kw['key_word']}: 权重 {kw['weight']}")
            if len(item['key_words']) > 3:
                print(f"   ... 还有 {len(item['key_words']) - 3} 个关键词")
            
    except FileNotFoundError:
        print(f"错误：找不到输入文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：{input_file} 不是有效的JSON文件")
    except KeyError as e:
        print(f"错误：JSON文件中缺少必要的键 {e}")
    except Exception as e:
        print(f"处理过程中发生错误：{e}")
        import traceback
        traceback.print_exc()

def create_sample_input():
    """
    创建示例输入文件，用于测试
    """
    sample_data = [
        {
            "Assertional_Logic": "Real",
            "key_words": [
                {"key_word": "real number calculation", "weight": 15},
                {"key_word": "solve real equations", "weight": 12},
                {"key_word": "ℝ = real", "weight": 10}
            ]
        },
        {
            "Assertional_Logic": "Integral",
            "key_words": [
                {"key_word": "calculate integral values", "weight": 15},
                {"key_word": "∫ f(x) dx", "weight": 14},
                {"key_word": "integration process", "weight": 8}
            ]
        }
    ]
    
    input_file = 'sample_input.json'
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=4)
    
    print(f"示例输入文件已创建: {input_file}")

# 直接执行文件处理
if __name__ == "__main__":
    # 如果需要创建示例文件进行测试，可以取消下面的注释
    # create_sample_input()
    
    process_json_file()