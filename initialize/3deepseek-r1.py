import json
import os
from openai import OpenAI

def safe_json_load(file_path):
    """安全加载JSON文件，处理各种编码和格式问题"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise ValueError(f"文件为空: {file_path}")
    
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read().strip()
                
            if not content:
                continue
                
            # 尝试解析JSON
            data = json.loads(content)
            print(f"✅ 使用 {encoding} 编码成功加载 {file_path}")
            return data
            
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError as e:
            print(f"❌ {encoding} 编码下JSON解析失败: {e}")
            continue
    
    raise ValueError(f"无法解析文件: {file_path}")

def main():
    # 检查 API 密钥
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("❌ 未设置 ARK_API_KEY 环境变量")
        return
    
    # 初始化客户端
    try:
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
    except Exception as e:
        print(f"❌ API 客户端初始化失败: {e}")
        return
    
    # 文件路径 - 请替换为你的实际路径
    file_path = "/data/train/initial/word_keywords.json"  # 只需要一个文件
    output_dir = "/data/train/initial"     # 替换为实际路径
    
    # 安全加载文件
    try:
        file_data = safe_json_load(file_path)
        print(f"📊 文件包含 {len(file_data)} 条数据")
        
    except Exception as e:
        print(f"❌ 文件加载失败: {e}")
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 更新后的系统提示语，让大模型自己理解算子含义
    instruction = '''You are an expert mathematician and computer scientist specializing in formal mathematical notation and automated theorem proving. 

Your task is to process mathematical operators in Assertional_Logic format and generate appropriate keywords.

For each Assertional_Logic entry:
1. First, analyze the mathematical meaning of the Assertional_Logic name
2. Based on your mathematical knowledge, understand what this operator represents
3. Generate keywords that would naturally appear in mathematical problems using this operator

CRITICAL GUIDELINES FOR KEYWORD GENERATION:

1. UNDERSTAND THE MATHEMATICAL MEANING:
   - Analyze the Assertional_Logic name to infer its mathematical purpose
   - Consider common mathematical contexts where this operator would be used
   - Think about related mathematical concepts and terminology

2. ABSTRACT NUMERICAL VALUES:
   - Replace specific numbers with variable symbols (e.g., √2 → √a, 3x → kx, 5² → n²)
   - Use single letters (a, b, c, x, y, z, n, m, k, etc.) as placeholders for numerical values
   - Focus on the mathematical structure rather than specific values

3. ELIMINATE STRUCTURAL REDUNDANCIES:
   - Group similar expressions under a single abstract representation
   - Remove repetitive patterns by creating generalized versions
   - Keep only the essential mathematical structure

4. GENERATE RELEVANT KEYWORDS:
   - Include the operator name itself in various forms (camelCase, snake_case, lowercase)
   - Include related mathematical terms and concepts
   - Include common mathematical symbols and notations
   - Include terms from different mathematical fields that might use this operator

5. EXAMPLES OF KEYWORD GENERATION:
   - For "Real": ["real", "ℝ", "continuous", "real number", "real line", "R"]
   - For "Integral": ["integral", "∫", "integration", "antiderivative", "area"]
   - For "Matrix": ["matrix", "matrices", "determinant", "eigenvalue", "linear algebra"]

The keywords should be abstract, concise, and directly relevant to the mathematical meaning of the Assertional_Logic operator.

For each keyword, assign a weight between 1 and 15 based on:
- Relevance to the operator (most relevant: higher weight)
- Frequency in mathematical literature
- Importance in understanding the operator

Output only in JSON format with the same structure as the input, but with updated key_words fields.'''
    
    # 处理文件的数据
    output_data = []
    
    for index, item in enumerate(file_data):
        assertional_logic = item.get("Assertional_Logic", "")
        current_keywords = item.get("key_words", [])
        
        # 构建用户提示
        user_prompt = f"""## Current Assertional_Logic Entry to Process:
Assertional_Logic: {assertional_logic}
Current key_words: {current_keywords}

Please analyze this mathematical operator and generate appropriate keywords:

1. Based on your mathematical expertise, what does the operator "{assertional_logic}" represent?
2. What are the core mathematical concepts and terminology related to this operator?
3. What keywords would naturally appear in mathematical problems or discussions about this operator?

IMPORTANT: Apply abstraction to all keywords:
- Replace specific numbers with variable symbols
- Eliminate structural redundancies by creating generalized versions
- Focus on mathematical structure rather than specific values

Output only the updated JSON object for this entry in the format:
{{"Assertional_Logic": "...", "key_words": [{{"key_word": "...", "weight": ...}}, ...]}}"""

        try:
            # 调用API
            response = client.chat.completions.create(
                model="deepseek-r1-250120",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                top_p=0.8
            )
            
            result = response.choices[0].message.content
            print(f"✅ 处理第 {index + 1} 条数据: {assertional_logic}")
            
            # 解析结果
            try:
                # 清理响应，提取JSON部分
                cleaned_result = result.strip()
                if "```json" in cleaned_result:
                    json_part = cleaned_result.split("```json")[1].split("```")[0].strip()
                    updated_item = json.loads(json_part)
                elif cleaned_result.startswith("{") and cleaned_result.endswith("}"):
                    updated_item = json.loads(cleaned_result)
                else:
                    # 尝试找到JSON对象
                    start_idx = cleaned_result.find('{')
                    end_idx = cleaned_result.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        json_str = cleaned_result[start_idx:end_idx]
                        updated_item = json.loads(json_str)
                    else:
                        raise ValueError("No JSON object found")
                
                # 验证必要字段
                if "Assertional_Logic" not in updated_item:
                    updated_item["Assertional_Logic"] = assertional_logic
                
                # 验证权重在1-15范围内
                if "key_words" in updated_item:
                    for kw in updated_item["key_words"]:
                        if "weight" in kw:
                            kw["weight"] = min(max(int(kw["weight"]), 1), 15)
                
                output_data.append(updated_item)
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ JSON解析错误，使用原始数据: {e}")
                print(f"原始响应: {result[:200]}...")
                output_data.append(item)
            
        except Exception as e:
            print(f"❌ API调用失败: {e}")
            output_data.append(item)
            continue
    
    # 保存结果
    output_path = os.path.join(output_dir, "deepseek_keywords_auto.json")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        print(f"✅ 处理完成，结果保存到: {output_path}")
        print(f"📊 成功处理 {len(output_data)}/{len(file_data)} 条数据")
        
        # 显示一些处理前后的对比示例
        print("\n🔍 处理前后对比示例:")
        for i in range(min(3, len(file_data))):
            original = file_data[i].get("key_words", [])
            processed = output_data[i].get("key_words", [])
            print(f"\n  {file_data[i].get('Assertional_Logic', '')}:")
            print(f"    前: {[kw.get('key_word', '') for kw in original[:3]]}")
            print(f"    后: {[kw.get('key_word', '') for kw in processed[:3]]}")
            
    except Exception as e:
        print(f"❌ 结果保存失败: {e}")

if __name__ == "__main__":
    main()