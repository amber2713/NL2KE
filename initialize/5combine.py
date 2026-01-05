import json
import sys
from collections import defaultdict

def integrate_keywords(file1_path, file2_path, output_path):
    """
    整合两个文件的key_words，基于Assertional_Logic字段
    
    Args:
        file1_path: 第一个文件路径（keywords+weight格式）
        file2_path: 第二个文件路径（keywords+weight格式）  
        output_path: 输出文件路径（keywords+weight格式）
    """
    
    try:
        # 读取第一个文件
        with open(file1_path, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        
        # 读取第二个文件
        with open(file2_path, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
        
        print(f"文件1包含 {len(data1)} 个算子")
        print(f"文件2包含 {len(data2)} 个算子")
        
        # 创建字典以便快速查找，key: Assertional_Logic, value: 关键词字典
        result_dict = defaultdict(lambda: {"key_words": {}})
        
        # 处理第一个文件的数据
        for item in data1:
            logic = item.get("Assertional_Logic", "")
            if not logic:
                continue
                
            keywords = item.get("key_words", [])
            # 使用字典存储关键词和权重，方便合并
            keyword_dict = {}
            
            for kw in keywords:
                if isinstance(kw, dict) and "key_word" in kw and "weight" in kw:
                    keyword = kw["key_word"]
                    weight = kw["weight"]
                    # 如果是keywords+weight格式
                    keyword_dict[keyword] = max(keyword_dict.get(keyword, 0), weight)
                elif isinstance(kw, str):
                    # 如果是纯字符串格式（旧格式），给默认权重5
                    keyword_dict[kw] = max(keyword_dict.get(kw, 0), 5)
            
            if keyword_dict:
                result_dict[logic]["Assertional_Logic"] = logic
                result_dict[logic]["key_words"].update(keyword_dict)
        
        # 处理第二个文件的数据，合并到字典中
        for item in data2:
            logic = item.get("Assertional_Logic", "")
            if not logic:
                continue
                
            keywords = item.get("key_words", [])
            keyword_dict = {}
            
            for kw in keywords:
                if isinstance(kw, dict) and "key_word" in kw and "weight" in kw:
                    keyword = kw["key_word"]
                    weight = kw["weight"]
                    # 如果是keywords+weight格式
                    keyword_dict[keyword] = max(keyword_dict.get(keyword, 0), weight)
                elif isinstance(kw, str):
                    # 如果是纯字符串格式（旧格式），给默认权重5
                    keyword_dict[kw] = max(keyword_dict.get(kw, 0), 5)
            
            if keyword_dict:
                result_dict[logic]["Assertional_Logic"] = logic
                result_dict[logic]["key_words"].update(keyword_dict)
        
        # 将结果转换为keywords+weight格式并排序
        result_list = []
        keyword_stats = {"total_keywords": 0, "max_keywords": 0, "min_keywords": float('inf')}
        
        for logic, data in result_dict.items():
            if not data.get("key_words"):
                continue
                
            # 获取关键词字典，按权重降序排序，如果权重相同则按字母顺序排序
            keyword_items = data["key_words"].items()
            sorted_keywords = sorted(
                keyword_items, 
                key=lambda x: (-x[1], x[0])  # 先按权重降序，再按字母顺序
            )
            
            # 转换为keywords+weight格式，并限制权重在1-5之间
            formatted_keywords = []
            for keyword, weight in sorted_keywords:
                # 确保权重在1-5范围内
                normalized_weight = max(1, min(5, weight))
                formatted_keywords.append({
                    "key_word": keyword,
                    "weight": normalized_weight
                })
            
            result_list.append({
                "Assertional_Logic": logic,
                "key_words": formatted_keywords
            })
            
            # 统计信息
            num_keywords = len(formatted_keywords)
            keyword_stats["total_keywords"] += num_keywords
            keyword_stats["max_keywords"] = max(keyword_stats["max_keywords"], num_keywords)
            keyword_stats["min_keywords"] = min(keyword_stats["min_keywords"], num_keywords)
        
        # 按Assertional_Logic排序
        result_list.sort(key=lambda x: x["Assertional_Logic"])
        
        # 写入输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_list, f, ensure_ascii=False, indent=2)
        
        print(f"\n整合完成！")
        print(f"共处理了 {len(result_list)} 个算子")
        print(f"总关键词数: {keyword_stats['total_keywords']}")
        print(f"每个算子平均关键词数: {keyword_stats['total_keywords'] / len(result_list):.1f}")
        print(f"最大关键词数: {keyword_stats['max_keywords']}")
        print(f"最小关键词数: {keyword_stats['min_keywords']}")
        print(f"结果已保存到: {output_path}")
        
        # 显示一些整合结果示例
        print("\n整合结果示例 (前5个算子):")
        for i, item in enumerate(result_list[:5]):
            print(f"\n{i+1}. {item['Assertional_Logic']}: {len(item['key_words'])} 个关键词")
            
            # 显示前3个关键词和权重
            for j, kw in enumerate(item['key_words'][:3]):
                print(f"   {kw['key_word']}: 权重 {kw['weight']}")
            
            if len(item['key_words']) > 3:
                print(f"   ... 还有 {len(item['key_words']) - 3} 个关键词")
        
        return result_list
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 - {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"错误: JSON格式不正确 - {e}")
        return None
    except Exception as e:
        print(f"发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数，处理命令行参数"""
    if len(sys.argv) != 4:
        print("使用方法: python integrate_keywords.py <文件1路径> <文件2路径> <输出文件路径>")
        print("示例: python integrate_keywords.py file1.json file2.json output.json")
        print("\n文件格式说明:")
        print("  输入文件必须是JSON格式，包含Assertional_Logic和key_words字段")
        print("  key_words字段应该是数组，每个元素包含key_word和weight")
        print("  示例格式:")
        print('  {"Assertional_Logic": "Real", "key_words": [{"key_word": "real", "weight": 5}, ...]}')
        
        # 如果没有提供命令行参数，可以使用默认路径
        file1 = input("请输入第一个文件路径: ").strip()
        file2 = input("请输入第二个文件路径: ").strip()
        output = input("请输入输出文件路径: ").strip()
        
        if not file1 or not file2 or not output:
            print("必须提供所有文件路径！")
            return
    else:
        file1, file2, output = sys.argv[1], sys.argv[2], sys.argv[3]
    
    integrate_keywords(file1, file2, output)

def create_sample_files():
    """创建示例文件用于测试"""
    # 示例文件1
    sample1 = [
        {
            "Assertional_Logic": "Real",
            "key_words": [
                {"key_word": "real", "weight": 5},
                {"key_word": "continuous", "weight": 10},
                {"key_word": "ℝ", "weight": 8}
            ]
        },
        {
            "Assertional_Logic": "Integral",
            "key_words": [
                {"key_word": "integral", "weight": 5},
                {"key_word": "∫", "weight": 12},
                {"key_word": "integration", "weight": 10}
            ]
        }
    ]
    
    # 示例文件2
    sample2 = [
        {
            "Assertional_Logic": "Real",
            "key_words": [
                {"key_word": "real number", "weight": 12},
                {"key_word": "ℝ", "weight": 10},
                {"key_word": "continuous", "weight": 5}
            ]
        },
        {
            "Assertional_Logic": "Derivative",
            "key_words": [
                {"key_word": "derivative", "weight": 5},
                {"key_word": "d/dx", "weight": 12},
                {"key_word": "differentiation", "weight": 10}
            ]
        }
    ]
    
    # 保存示例文件
    with open("sample1.json", "w", encoding="utf-8") as f:
        json.dump(sample1, f, indent=2, ensure_ascii=False)
    
    with open("sample2.json", "w", encoding="utf-8") as f:
        json.dump(sample2, f, indent=2, ensure_ascii=False)
    
    print("示例文件已创建: sample1.json, sample2.json")
    print("可以使用以下命令测试:")
    print("python integrate_keywords.py sample1.json sample2.json integrated.json")

if __name__ == "__main__":
    # 如果想创建示例文件进行测试，可以取消下面的注释
    # create_sample_files()
    
    # 运行主函数
    main()