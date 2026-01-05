import json
import sys
import os
from typing import List, Dict, Any

def extract_data_blocks(json_file_path: str) -> List[Dict[str, Any]]:
    """
    从JSON文件中提取每个数据块的Problem, Declaration, Facts, Query, lean_theorem字段
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(json_file_path):
            print(f"错误: 文件 '{json_file_path}' 不存在")
            return []
            
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        extracted_blocks = []
        
        # 处理不同的JSON结构
        if isinstance(data, list):
            data_blocks = data
        elif isinstance(data, dict):
            # 尝试找到包含数据块的键
            possible_keys = ['data', 'blocks', 'items', 'results', 'entries']
            data_blocks = None
            for key in possible_keys:
                if key in data and isinstance(data[key], list):
                    data_blocks = data[key]
                    break
            
            # 如果没有找到合适的键，将整个对象视为一个数据块
            if data_blocks is None:
                data_blocks = [data]
        else:
            print("错误: JSON文件格式不支持")
            return []
        
        # 提取每个数据块的指定字段
        for i, block in enumerate(data_blocks):
            # 检查block是否为字典类型
            if not isinstance(block, dict):
                print(f"警告: 数据块 #{i} 不是字典类型，跳过")
                continue
                
            extracted_block = {
                'index': i + 1,  # 从1开始计数
                'Problem': block.get('Problem', '未找到Problem字段'),
                'Declaration': block.get('Declaration', '未找到Declaration字段'),
                'Facts': block.get('Facts', '未找到Facts字段'),
                'Query': block.get('Query', '未找到Query字段'),
                'lean_theorem': block.get('lean_theorem', '未找到lean_theorem字段')
            }
            extracted_blocks.append(extracted_block)
        
        print(f"成功处理 {len(extracted_blocks)} 个数据块")
        return extracted_blocks
        
    except FileNotFoundError:
        print(f"错误: 文件 '{json_file_path}' 未找到")
        return []
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {str(e)}")
        return []
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")
        return []

def save_extracted_data(extracted_blocks: List[Dict[str, Any]], output_file: str):
    """
    保存提取的数据到文件
    """
    if not extracted_blocks:
        print("没有数据可保存")
        return False
    
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存到JSON文件
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(extracted_blocks, file, ensure_ascii=False, indent=2)
        
        print(f"✓ 数据已成功保存到: {output_file}")
        print(f"✓ 文件大小: {os.path.getsize(output_file)} 字节")
        return True
        
    except Exception as e:
        print(f"✗ 保存文件时发生错误: {str(e)}")
        return False

def print_extracted_data(extracted_blocks: List[Dict[str, Any]]):
    """
    打印提取的数据到控制台
    """
    if not extracted_blocks:
        print("没有数据可显示")
        return
    
    print("\n" + "="*60)
    print("提取的数据预览 (前3个数据块):")
    print("="*60)
    
    for i, block in enumerate(extracted_blocks[:3]):  # 只显示前3个
        print(f"\n数据块 #{block['index']}:")
        print(f"  Problem: {block['Problem'][:100]}{'...' if len(block['Problem']) > 100 else ''}")
        print(f"  Declaration: {block['Declaration'][:100]}{'...' if len(block['Declaration']) > 100 else ''}")
        print(f"  Facts: {block['Facts'][:100]}{'...' if len(block['Facts']) > 100 else ''}")
        print(f"  Query: {block['Query'][:100]}{'...' if len(block['Query']) > 100 else ''}")
        print(f"  lean_theorem: {block['lean_theorem'][:100]}{'...' if len(block['lean_theorem']) > 100 else ''}")
        print("-" * 40)
    
    if len(extracted_blocks) > 3:
        print(f"... 还有 {len(extracted_blocks) - 3} 个数据块未显示")

def main():
    """
    主函数 - 修复版本
    """
    print("JSON数据提取工具")
    print("=" * 30)
    
    # 获取输入文件路径
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        json_file_path = input("请输入JSON文件路径: ").strip()
    
    # 检查输入文件
    if not json_file_path:
        print("错误: 未提供文件路径")
        return
    
    if not json_file_path.endswith('.json'):
        print("警告: 文件扩展名不是.json")
    
    # 设置输出文件路径
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # 基于输入文件名生成输出文件名
        base_name = os.path.splitext(os.path.basename(json_file_path))[0]
        default_output = f"{base_name}_extracted.json"
        output_file = input(f"请输入输出文件路径 (默认: {default_output}): ").strip()
        if not output_file:
            output_file = default_output
    
    # 确保输出文件有.json扩展名
    if not output_file.endswith('.json'):
        output_file += '.json'
    
    print(f"\n开始处理文件: {json_file_path}")
    print(f"输出文件: {output_file}")
    
    # 提取数据
    extracted_blocks = extract_data_blocks(json_file_path)
    
    if extracted_blocks:
        # 显示预览
        print_extracted_data(extracted_blocks)
        
        # 保存数据
        if save_extracted_data(extracted_blocks, output_file):
            print(f"\n🎉 处理完成! 共提取 {len(extracted_blocks)} 个数据块")
        else:
            print("\n❌ 保存失败")
    else:
        print("\n❌ 未能提取任何数据")

# 简单使用示例
def quick_extract(input_file, output_file=None):
    """
    快速提取函数 - 直接调用这个函数
    """
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_extracted.json"
    
    print(f"正在处理: {input_file}")
    extracted_blocks = extract_data_blocks(input_file)
    
    if extracted_blocks:
        success = save_extracted_data(extracted_blocks, output_file)
        if success:
            return extracted_blocks
    return None

if __name__ == "__main__":
    main()