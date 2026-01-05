import json
import os
import math

def split_json_file(input_file, output_dir, chunk_size=1000):
    """
    将大型JSON文件分割成多个小文件
    
    参数:
        input_file: 输入JSON文件路径
        output_dir: 输出文件夹路径
        chunk_size: 每个文件包含的数据块数量，默认为1000
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出文件夹: {output_dir}")
    
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"成功读取文件: {input_file}")
        print(f"总数据量: {len(data)} 条记录")
        
        # 计算需要分割成多少个文件
        num_chunks = math.ceil(len(data) / chunk_size)
        print(f"将分割为 {num_chunks} 个文件，每个文件最多 {chunk_size} 条记录")
        
        # 分割数据并保存
        for i in range(num_chunks):
            # 计算当前块的起始和结束索引
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(data))
            
            # 提取当前块的数据
            chunk_data = data[start_idx:end_idx]
            
            # 生成输出文件名
            output_file = os.path.join(output_dir, f"chunk_{i+1:04d}.json")
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)
            
            print(f"  已保存: {output_file} (包含 {len(chunk_data)} 条记录)")
        
        print(f"\n分割完成! 所有文件已保存到: {output_dir}")
        
        # 生成汇总信息文件
        summary_file = os.path.join(output_dir, "分割信息.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"JSON文件分割汇总信息\n")
            f.write("=" * 40 + "\n")
            f.write(f"原始文件: {input_file}\n")
            f.write(f"总记录数: {len(data)} 条\n")
            f.write(f"分割大小: {chunk_size} 条/文件\n")
            f.write(f"生成文件数: {num_chunks} 个\n")
            f.write(f"输出目录: {output_dir}\n")
            f.write("\n文件列表:\n")
            
            for i in range(num_chunks):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(data))
                f.write(f"  chunk_{i+1:04d}.json: 记录 {start_idx+1}-{end_idx} (共 {end_idx-start_idx} 条)\n")
        
        print(f"汇总信息已保存到: {summary_file}")
        
        return num_chunks
        
    except FileNotFoundError:
        print(f"错误: 文件 {input_file} 不存在")
        return 0
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
        return 0
    except Exception as e:
        print(f"错误: {e}")
        return 0


def verify_split_files(output_dir, original_count):
    """
    验证分割后的文件是否完整
    
    参数:
        output_dir: 输出文件夹路径
        original_count: 原始数据总条数
    """
    print("\n" + "="*50)
    print("验证分割文件...")
    
    # 获取所有分割文件
    chunk_files = [f for f in os.listdir(output_dir) if f.startswith('chunk_') and f.endswith('.json')]
    chunk_files.sort()  # 按文件名排序
    
    if not chunk_files:
        print("未找到分割文件")
        return False
    
    total_records = 0
    valid_files = 0
    
    for filename in chunk_files:
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            record_count = len(chunk_data)
            total_records += record_count
            valid_files += 1
            
            print(f"  {filename}: {record_count} 条记录")
            
        except Exception as e:
            print(f"  {filename}: 读取失败 - {e}")
    
    print(f"\n验证结果:")
    print(f"  有效文件数: {valid_files}/{len(chunk_files)}")
    print(f"  总记录数: {total_records}")
    print(f"  原始记录数: {original_count}")
    print(f"  完整性: {'✓ 完整' if total_records == original_count else '✗ 不完整'}")
    
    return total_records == original_count


def main():
    # 配置参数
    INPUT_FILE = "/Users/xuhui/Desktop/NO code/PDFQ.json"  # 输入文件路径
    OUTPUT_DIR = "/Users/xuhui/Desktop/NO code/batch"  # 输出文件夹名称
    CHUNK_SIZE = 1000  # 每个文件的数据块数量
    
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件 {INPUT_FILE} 不存在")
        return
    
    print("="*50)
    print("JSON文件分割工具")
    print("="*50)
    
    # 分割文件
    num_chunks = split_json_file(INPUT_FILE, OUTPUT_DIR, CHUNK_SIZE)
    
    if num_chunks > 0:
        # 读取原始数据总数用于验证
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        # 验证分割结果
        verify_split_files(OUTPUT_DIR, len(original_data))
        
        # 提供使用示例
        print("\n" + "="*50)
        print("使用示例:")
        print("  要读取第1个分割文件:")
        print(f"    with open('{OUTPUT_DIR}/chunk_0001.json', 'r', encoding='utf-8') as f:")
        print("        data = json.load(f)")
        print("\n  要合并所有分割文件:")
        print(f"    all_data = []")
        print(f"    for i in range(1, {num_chunks+1}):")
        print(f"        file_path = f'{OUTPUT_DIR}/chunk_{{i:04d}}.json'")
        print(f"        with open(file_path, 'r', encoding='utf-8') as f:")
        print(f"            chunk = json.load(f)")
        print(f"            all_data.extend(chunk)")


if __name__ == "__main__":
    main()