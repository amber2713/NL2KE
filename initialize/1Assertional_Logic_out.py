import json
import re
from typing import List, Dict, Set

def extract_target_strings_precise(input_file: str) -> Set[str]:
    """
    精确提取目标字符串：从大写字母开始，前一个字符必须是除了下划线和英文字母的其他字符
    """
    # 读取输入JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 用于存储所有提取的字符串（自动去重）
    extracted_strings = set()
    
    # 需要处理的字段
    target_fields = ['Declaration', 'Facts', 'Query']
    
    print("开始处理数据...")
    
    for i, item in enumerate(data):
        print(f"\n处理第 {i+1} 个数据块 (ID: {item.get('id', 'N/A')}):")
        
        for field in target_fields:
            if field in item and item[field]:
                text = item[field]
                print(f"  {field}: {text}")
                
                # 使用更精确的正则表达式
                # 匹配：前面是单词边界或非字母非下划线字符，然后是大写字母，后面跟着字母数字下划线
                pattern = r'(?<!\w)[A-Z][a-zA-Z0-9_]*'
                
                # 找到所有匹配项
                matches = re.findall(pattern, text)
                
                # 进一步验证：确保匹配的字符串长度>=3
                valid_matches = [match for match in matches if len(match) >= 3]
                
                for match in valid_matches:
                    extracted_strings.add(match)
                    print(f"    提取到: '{match}'")
    
    return extracted_strings

def extract_all_possible_strings(input_file: str) -> Set[str]:
    """
    穷尽所有可能的目标字符串，包括边界情况的处理
    """
    # 读取输入JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    extracted_strings = set()
    target_fields = ['Declaration', 'Facts', 'Query']
    
    print("开始穷尽提取数据...")
    
    for i, item in enumerate(data):
        print(f"\n处理第 {i+1} 个数据块 (ID: {item.get('id', 'N/A')}):")
        
        for field in target_fields:
            if field in item and item[field]:
                text = item[field]
                print(f"  {field}: {text}")
                
                # 方法1：使用正则表达式查找所有可能的匹配
                pattern1 = r'(?<!\w)[A-Z][a-zA-Z0-9_]*'
                matches1 = re.findall(pattern1, text)
                
                # 方法2：分割文本并检查每个单词
                words = re.split(r'[^\w]', text)  # 按非单词字符分割
                matches2 = [word for word in words if word and word[0].isupper() and len(word) >= 3]
                
                # 方法3：查找所有大写字母位置并验证前面的字符
                matches3 = []
                for match in re.finditer(r'[A-Z][a-zA-Z0-9_]*', text):
                    start_pos = match.start()
                    word = match.group()
                    
                    # 检查前面的字符是否符合条件
                    if start_pos == 0:  # 字符串开头
                        matches3.append(word)
                    else:
                        prev_char = text[start_pos - 1]
                        if not (prev_char.isalpha() or prev_char == '_'):
                            matches3.append(word)
                
                # 合并所有方法的结果
                all_matches = set(matches1 + matches2 + matches3)
                valid_matches = [match for match in all_matches if len(match) >= 3]
                
                for match in valid_matches:
                    extracted_strings.add(match)
                    print(f"    提取到: '{match}'")
    
    return extracted_strings

def create_structured_output(extracted_strings: Set[str]) -> List[Dict[str, str]]:
    """
    创建结构化的输出，只包含Assertional_Logic字段
    """
    result = []
    
    # 对提取的字符串进行排序
    sorted_strings = sorted(list(extracted_strings))
    
    for string in sorted_strings:
        entry = {
            "Assertional_Logic": string
        }
        result.append(entry)
    
    return result

def save_structured_output(output_data: List[Dict[str, str]], output_file: str):
    """保存结构化的输出到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n处理完成!")
    print(f"总共提取了 {len(output_data)} 个算子:")
    for entry in output_data[:10]:  # 只显示前10个
        print(f"  - {entry['Assertional_Logic']}")
    if len(output_data) > 10:
        print(f"  ... 还有 {len(output_data)-10} 个算子")

# 测试函数，验证提取规则
def test_extraction_rules():
    """测试提取规则是否正确"""
    test_cases = [
        # (输入文本, 期望提取的结果)
        ("Solve_equation(x: Real, Tan(x) + 1 / Cos(x) = 2) = ?", ["Solve_equation", "Real", "Tan", "Cos"]),
        ("a: IrrationalNumbers", ["IrrationalNumbers"]),
        ("Sin(a^2 - Real.pi / 2) = 0", ["Sin", "Real"]),
        ("Test_ABC and XYZ test", ["Test_ABC", "XYZ"]),  # "test"不以大写开头
        ("Multiple Words Here", ["Multiple", "Words", "Here"]),
        ("start With Capital", ["With", "Capital"]),  # "start"不以大写开头
        ("URL_Handler and XML_Parser", ["URL_Handler", "XML_Parser"]),
        ("123Number and Abc123", ["Abc123"]),  # "123Number"不以字母开头
        ("", []),  # 空字符串
        ("a b c", []),  # 没有大写字母
    ]
    
    pattern = r'(?<!\w)[A-Z][a-zA-Z0-9_]*'
    
    print("测试提取规则:")
    for i, (test_input, expected) in enumerate(test_cases):
        matches = re.findall(pattern, test_input)
        valid_matches = [match for match in matches if len(match) >= 3]
        
        status = "✓" if set(valid_matches) == set(expected) else "✗"
        print(f"{status} 测试 {i+1}: '{test_input}'")
        print(f"    期望: {expected}")
        print(f"    实际: {valid_matches}")
        if set(valid_matches) != set(expected):
            print(f"    不匹配!")
        print()

# 使用示例
if __name__ == "__main__":
    input_filename = "/data/train/train(PDFQ).json"  # 替换为您的输入文件路径
    output_filename = "/data/train/initial/Assertional_Logic.json"  # 替换为您的输出文件路径
    
    # 先运行测试
    test_extraction_rules()
    
    try:
        # 使用精确提取版本
        #extracted_strings = extract_target_strings_precise(input_filename)
        
        # 如果需要更彻底的提取，可以使用穷尽版本
        extracted_strings = extract_all_possible_strings(input_filename)
        
        # 创建结构化的输出
        structured_output = create_structured_output(extracted_strings)
        
        # 保存输出
        save_structured_output(structured_output, output_filename)
        
        # 显示部分输出样例
        print("\n=== 输出样例 (前10个算子) ===")
        for i, entry in enumerate(structured_output[:10]):
            print(f"{json.dumps(entry, ensure_ascii=False)},")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_filename}")
    except json.JSONDecodeError:
        print(f"错误: {input_filename} 不是有效的JSON文件")
    except Exception as e:
        print(f"处理过程中出现错误: {e}")