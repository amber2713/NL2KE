import json
import re
import os
from collections import Counter
import string
import nltk
import ssl
from typing import Dict, List, Set, Any, Tuple

class BatchOperatorAnalyzer:
    def __init__(self):
        # SSL设置
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        
        # NLTK设置
        self.nltk_available = self._setup_nltk()
        
        if self.nltk_available:
            from nltk.corpus import stopwords
            self.stop_words = set(stopwords.words('english'))
            print("NLTK已成功加载")
        else:
            # 备选停用词列表
            self.stop_words = set([
                'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'it', 'its', 'them',
                'their', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'where', 'when',
                'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
                'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'
            ])
            print("使用备选分词方案")
        
        self.punctuation = set(string.punctuation)
        
        # 数学动词模式 - 用于识别谓宾结构
        self.math_verbs = {
            'find', 'calculate', 'compute', 'determine', 'solve', 'evaluate', 'measure',
            'construct', 'draw', 'plot', 'locate', 'identify', 'verify', 'check',
            'prove', 'show', 'demonstrate', 'establish', 'define', 'describe'
        }
        
        # 数学宾语模式 - 常见的数学对象
        self.math_objects = {
            'area', 'volume', 'distance', 'length', 'angle', 'slope', 'equation',
            'point', 'line', 'circle', 'triangle', 'square', 'rectangle', 'polygon',
            'intersection', 'midpoint', 'center', 'radius', 'diameter', 'tangent',
            'perpendicular', 'parallel', 'bisector', 'median', 'altitude', 'centroid',
            'circumcenter', 'incenter', 'orthocenter', 'vector', 'matrix', 'coordinate'
        }
    
    def _setup_nltk(self):
        """设置NLTK"""
        try:
            nltk.data.find('tokenizers/punkt')
            return True
        except LookupError:
            try:
                print("正在下载NLTK数据包...")
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                return True
            except Exception as e:
                print(f"NLTK下载失败: {e}")
                return False
    
    def load_operators_list(self, operators_list_file: str) -> List[str]:
        """加载算子列表，支持新格式：包含Assertional_Logic字段的对象数组"""
        try:
            with open(operators_list_file, 'r', encoding='utf-8') as f:
                operators_data = json.load(f)
            
            operators = []
            
            # 检查数据格式
            if isinstance(operators_data, list):
                for item in operators_data:
                    if isinstance(item, dict) and "Assertional_Logic" in item:
                        operator_name = item.get("Assertional_Logic", "").strip()
                        if operator_name:
                            operators.append(operator_name)
                    elif isinstance(item, str):
                        # 也支持旧的字符串数组格式
                        if item.strip():
                            operators.append(item.strip())
            
            print(f"加载算子列表完成: {len(operators)} 个算子")
            return operators
        except Exception as e:
            print(f"加载算子列表失败: {e}")
            return []
    
    def load_problems(self, input_path: str, operator_name: str = None) -> List[Dict]:
        """
        加载问题数据，支持两种输入形式：
        1. 单个问题文件：直接返回文件中的所有问题
        2. 文件夹：根据算子名称查找对应的文件
        
        Args:
            input_path: 输入路径，可以是文件或文件夹
            operator_name: 算子名称（仅在输入为文件夹时需要）
            
        Returns:
            问题数据列表
        """
        if os.path.isfile(input_path):
            # 输入是单个文件
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    problems_data = json.load(f)
                
                if isinstance(problems_data, list):
                    print(f"从文件加载了 {len(problems_data)} 个问题")
                    return problems_data
                else:
                    print("文件格式错误：应该是一个问题数组")
                    return []
            except Exception as e:
                print(f"加载问题文件失败: {e}")
                return []
        elif os.path.isdir(input_path):
            # 输入是文件夹，需要算子名称来查找文件
            if not operator_name:
                print("错误：当输入为文件夹时，必须提供算子名称")
                return []
            
            try:
                # 构建可能的文件名模式
                possible_filenames = [
                    f"{operator_name}.json",
                    f"{operator_name.lower()}.json",
                    f"{operator_name.upper()}.json",
                ]
                
                problems = []
                
                # 尝试每个可能的文件名
                for filename in possible_filenames:
                    file_path = os.path.join(input_path, filename)
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                        
                        if isinstance(file_data, list):
                            problems.extend(file_data)
                            print(f"  从 {filename} 加载了 {len(file_data)} 个问题")
                        break  # 找到文件后跳出循环
                
                return problems
            except Exception as e:
                print(f"  加载算子 {operator_name} 的问题数据失败: {e}")
                return []
        else:
            print(f"错误：输入路径不存在: {input_path}")
            return []
    
    def extract_verb_object_phrases(self, text: str) -> List[str]:
        """
        提取谓宾结构短语
        基于规则的方法识别数学问题中的动词-宾语模式
        """
        if not text:
            return []
        
        phrases = []
        
        try:
            # 使用NLTK进行基础分词和词性标注
            if self.nltk_available:
                tokens = nltk.word_tokenize(str(text).lower())
                # 这里简化处理，实际应该使用完整的句法分析
                # 使用基于规则的模式匹配
                phrases = self._rule_based_phrase_extraction(tokens)
            else:
                # 备选方案：基于正则表达式的简单短语提取
                phrases = self._regex_based_phrase_extraction(str(text).lower())
            
            return phrases
            
        except Exception as e:
            print(f"短语提取错误: {e}")
            return self._regex_based_phrase_extraction(str(text).lower())
    
    def _rule_based_phrase_extraction(self, tokens: List[str]) -> List[str]:
        """基于规则的短语提取"""
        phrases = []
        
        # 简单的滑动窗口方法识别动词-宾语模式
        for i in range(len(tokens)):
            # 检查当前词是否是数学动词
            if tokens[i] in self.math_verbs:
                # 构建可能的短语
                phrase_tokens = [tokens[i]]
                
                # 添加后续的宾语词
                j = i + 1
                while j < len(tokens) and j < i + 5:  # 限制短语长度
                    if (tokens[j] in self.stop_words or 
                        tokens[j] in self.punctuation):
                        j += 1
                        continue
                    
                    # 如果遇到另一个动词，停止扩展
                    if tokens[j] in self.math_verbs and j > i + 1:
                        break
                    
                    phrase_tokens.append(tokens[j])
                    j += 1
                
                if len(phrase_tokens) > 1:  # 至少包含动词和一个宾语
                    phrase = ' '.join(phrase_tokens)
                    phrases.append(phrase)
        
        return phrases
    
    def _regex_based_phrase_extraction(self, text: str) -> List[str]:
        """基于正则表达式的短语提取（备选方案）"""
        phrases = []
        
        # 定义数学动词模式
        verb_pattern = r'\b(find|calculate|compute|determine|solve|construct|draw|prove|show)\b'
        
        # 匹配动词及其后面的内容（最多5个词）
        pattern = rf'{verb_pattern}(\s+\w+){{1,4}}'
        
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                # re.findall返回元组，需要拼接
                full_match = ' '.join([m for m in match if m])
                phrases.append(full_match.strip())
            else:
                phrases.append(match.strip())
        
        return phrases
    
    def preprocess_text(self, text: str) -> List[str]:
        """预处理文本 - 现在提取谓宾短语而不是单个词语"""
        if not text:
            return []
        
        # 提取谓宾短语
        phrases = self.extract_verb_object_phrases(text)
        
        # 过滤处理：移除太短的短语和纯数字短语
        filtered_phrases = [
            phrase for phrase in phrases 
            if (len(phrase) > 3 and  # 短语至少3个字符
                not phrase.replace(' ', '').isdigit() and
                not all(word in self.stop_words for word in phrase.split()))
        ]
        
        return filtered_phrases
    
    def extract_text_from_problems(self, problems: List[Dict]) -> List[str]:
        """从问题数据中提取文本内容"""
        all_texts = []
        
        for problem in problems:
            problem_text = problem.get("Problem", "")
            query = problem.get("Query", "")
            declaration = problem.get("Declaration", "")
            facts = problem.get("Facts", "")
            
            # 合并所有文本内容
            combined_text = f"{problem_text} {query} {declaration} {facts}"
            all_texts.append(combined_text)
        
        return all_texts
    
    def analyze_operator_context(self, operator_name: str, problems: List[Dict]) -> Dict:
        """分析单个算子上下文，返回keywords+weight格式的数据"""
        # 从问题数据中提取文本
        all_texts = self.extract_text_from_problems(problems)
        
        # 收集所有谓宾短语
        all_phrases = []
        for text in all_texts:
            phrases = self.preprocess_text(text)
            all_phrases.extend(phrases)
        
        print(f"算子 '{operator_name}' 的问题数: {len(problems)}")
        print(f"提取了 {len(all_phrases)} 个谓宾短语")
        
        # 如果没有任何短语，返回空结果
        if not all_phrases:
            return {
                "Assertional_Logic": operator_name,
                "key_words": [],
                "total_problems": len(problems),
                "total_phrases": 0,
                "unique_phrases": 0,
                "message": "没有找到谓宾短语"
            }
        
        # 统计短语频率
        phrase_freq = Counter(all_phrases)
        
        # 转换为keywords+weight格式
        key_words = []
        
        # 对每个短语进行权重计算（限制在1-15之间）
        for phrase, freq in phrase_freq.most_common(50):  # 只取前50个最高频短语
            # 计算权重（基于频率，限制在1-15之间）
            if len(phrase_freq) > 1:
                # 标准化频率到1-15范围
                max_freq = max(phrase_freq.values())
                min_freq = min(phrase_freq.values())
                
                if max_freq == min_freq:
                    weight = 8  # 如果所有频率相同，设为中间值
                else:
                    # 将频率映射到1-15范围
                    normalized = (freq - min_freq) / (max_freq - min_freq)
                    weight = int(1 + normalized * 14)  # 映射到1-15
            else:
                weight = 8  # 只有一个短语的情况
            
            # 确保权重在1-15之间
            weight = max(1, min(15, weight))
            
            key_words.append({
                "key_word": phrase,
                "weight": weight
            })
        
        # 构建结果（keywords+weight格式）
        result = {
            "Assertional_Logic": operator_name,
            "key_words": key_words,
            "total_problems": len(problems),
            "total_phrases": len(all_phrases),
            "unique_phrases": len(phrase_freq),
            "message": f"成功提取{len(key_words)}个关键词"
        }
        
        return result
    
    def display_operator_results(self, results: Dict):
        """显示单个算子的分析结果（keywords+weight格式）"""
        operator_name = results["Assertional_Logic"]
        key_words = results.get("key_words", [])
        
        print(f"\n=== 算子 '{operator_name}' 相关文本中的关键词和权重 ===")
        print(f"问题数: {results.get('total_problems', 0)}")
        print(f"总短语数: {results.get('total_phrases', 0)}")
        print(f"唯一短语数: {results.get('unique_phrases', 0)}")
        
        if not key_words:
            print("没有找到关键词")
            return
        
        print(f"\n排名 | 关键词 | 权重")
        print("-" * 60)
        
        for i, item in enumerate(key_words[:15], 1):  # 显示前15个
            keyword = item["key_word"]
            weight = item["weight"]
            print(f"{i:2d}.  {keyword:40} {weight:5d}")
        
        if len(key_words) > 15:
            print(f"... 还有 {len(key_words) - 15} 个关键词")
        
        # 统计信息
        total_weight = sum(item["weight"] for item in key_words)
        avg_weight = total_weight / len(key_words) if len(key_words) > 0 else 0
        print(f"\n关键词总数: {len(key_words)}")
        print(f"平均权重: {avg_weight:.2f}")
        print(f"最小权重: {min(item['weight'] for item in key_words)}")
        print(f"最大权重: {max(item['weight'] for item in key_words)}")
    
    def save_all_results_to_single_file(self, results_list: List[Dict], output_dir: str, filename: str = "all_operators_keywords.json") -> str:
        """将所有算子的结果保存到一个文件中"""
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建合并后的数据
        all_operators_data = []
        
        for result in results_list:
            # 提取keywords+weight格式的数据
            item_data = {
                "Assertional_Logic": result["Assertional_Logic"],
                "key_words": result.get("key_words", [])
            }
            all_operators_data.append(item_data)
        
        # 保存到单个文件
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_operators_data, f, indent=2, ensure_ascii=False)
        
        print(f"所有算子的keywords+weight格式结果已保存到: {filepath}")
        return filepath
    
    def process_all_operators(self, operators_list_file: str, 
                            problems_input_path: str,
                            output_dir: str = "operator_keywords_results",
                            input_type: str = "auto",
                            output_filename: str = "all_operators_keywords.json"):
        """
        处理所有算子，将所有结果整合到一个文件中
        
        Args:
            operators_list_file: 算子列表文件，JSON格式，包含Assertional_Logic字段
            problems_input_path: 问题数据输入路径，可以是文件或文件夹
            output_dir: 输出目录
            input_type: 输入类型，可选值：
                - "auto": 自动检测（默认）
                - "file": 单个问题文件
                - "directory": 包含多个算子问题文件的文件夹
            output_filename: 输出文件名，默认为"all_operators_keywords.json"
        """
        # 1. 加载算子列表
        operators_list = self.load_operators_list(operators_list_file)
        if not operators_list:
            print("算子列表加载失败，程序退出")
            return
        
        # 2. 确定输入类型
        if input_type == "auto":
            if os.path.isfile(problems_input_path):
                input_type = "file"
            elif os.path.isdir(problems_input_path):
                input_type = "directory"
            else:
                print(f"错误：无法确定输入类型，路径不存在: {problems_input_path}")
                return
        
        # 3. 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n开始处理 {len(operators_list)} 个算子...")
        print("输出格式: keywords+weight")
        print(f"输入类型: {input_type}")
        print(f"问题数据路径: {problems_input_path}")
        print(f"输出文件: {os.path.join(output_dir, output_filename)}")
        
        results_summary = {
            "total_operators": len(operators_list),
            "processed_operators": 0,
            "operators_with_data": 0,
            "operators_with_keywords": 0,
            "total_keywords": 0,
            "output_directory": output_dir,
            "output_file": output_filename,
            "input_type": input_type,
            "input_path": problems_input_path,
            "operator_results": []
        }
        
        all_results_list = []  # 用于存储所有算子的结果
        
        # 4. 如果是文件输入类型，预加载所有问题
        all_problems_data = None
        if input_type == "file":
            print("正在预加载所有问题数据...")
            all_problems_data = self.load_problems(problems_input_path)
            if not all_problems_data:
                print("错误：无法加载问题文件")
                return
        
        # 5. 为每个算子分析上下文
        for i, operator in enumerate(operators_list, 1):
            print(f"\n[{i}/{len(operators_list)}] 正在处理算子: {operator}")
            
            # 获取该算子的所有问题数据
            if input_type == "file":
                # 文件输入类型：使用所有问题数据
                problems_data = all_problems_data
            else:
                # 文件夹输入类型：根据算子名称加载对应文件
                problems_data = self.load_problems(problems_input_path, operator)
            
            if not problems_data:
                print(f"警告: 算子 '{operator}' 的问题数据为空或无法读取")
                results_summary["processed_operators"] += 1
                continue
            
            # 分析算子上下文
            results = self.analyze_operator_context(operator, problems_data)
            
            # 添加到所有结果列表
            all_results_list.append(results)
            
            # 显示结果摘要
            self.display_operator_results(results)
            
            # 更新摘要
            results_summary["processed_operators"] += 1
            if results.get("total_phrases", 0) > 0:
                results_summary["operators_with_data"] += 1
            if len(results.get("key_words", [])) > 0:
                results_summary["operators_with_keywords"] += 1
                results_summary["total_keywords"] += len(results["key_words"])
            
            results_summary["operator_results"].append({
                "operator": operator,
                "keywords_count": len(results.get("key_words", [])),
                "problems_count": results.get("total_problems", 0),
                "total_phrases": results.get("total_phrases", 0),
                "unique_phrases": results.get("unique_phrases", 0),
            })
        
        # 6. 将所有算子的结果保存到一个文件中
        if all_results_list:
            output_filepath = self.save_all_results_to_single_file(all_results_list, output_dir, output_filename)
            results_summary["output_file_path"] = output_filepath
            
            # 显示总结果
            print(f"\n" + "=" * 60)
            print("所有算子处理完成!")
            print("=" * 60)
            print(f"总共处理了 {results_summary['processed_operators']} 个算子")
            print(f"其中有数据的算子: {results_summary['operators_with_data']} 个")
            print(f"有关键词的算子: {results_summary['operators_with_keywords']} 个")
            print(f"总关键词数: {results_summary['total_keywords']} 个")
            print(f"结果已保存到: {output_filepath}")
        else:
            print("没有生成任何结果文件")
        
        # 7. 保存摘要文件
        summary_path = os.path.join(output_dir, "processing_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results_summary, f, indent=2, ensure_ascii=False)
        
        print(f"处理摘要保存在: {summary_path}")
        
        return results_summary

def get_user_input(prompt: str, default: str = "") -> str:
    """
    获取用户输入，支持默认值
    """
    if default:
        user_input = input(f"{prompt} (默认: {default}): ").strip()
        if not user_input:
            return default
        return user_input
    else:
        while True:
            user_input = input(f"{prompt}: ").strip()
            if user_input:
                return user_input
            print("输入不能为空，请重新输入。")

def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """
    获取是/否输入
    """
    default_str = "Y" if default else "N"
    while True:
        user_input = input(f"{prompt} (Y/N, 默认: {default_str}): ").strip().upper()
        if not user_input:
            return default
        if user_input in ["Y", "YES"]:
            return True
        elif user_input in ["N", "NO"]:
            return False
        print("请输入 Y 或 N。")

def main():
    """主函数 - 交互式输入"""
    print("=" * 60)
    print("算子动宾短语关键词提取工具")
    print("版本: 整合输出版 - 所有结果输出到单个文件")
    print("=" * 60)
    print()
    
    # 创建分析器
    analyzer = BatchOperatorAnalyzer()
    
    # 获取算子列表文件路径
    print("【步骤1】算子列表文件输入")
    print("算子列表文件格式示例：")
    print('''[
  {
    "Assertional_Logic": "AND"
  },
  {
    "Assertional_Logic": "Abs"
  },
  {
    "Assertional_Logic": "Real"
  }
]''')
    operators_file = get_user_input("请输入算子列表文件路径", "/data/train/initial/Assertional_Logic.json")
    
    # 检查文件是否存在
    while not os.path.exists(operators_file):
        print(f"错误：文件不存在: {operators_file}")
        operators_file = get_user_input("请重新输入算子列表文件路径", "/data/train/initial/Assertional_Logic.json")
    
    # 获取问题数据输入类型
    print("\n【步骤2】问题数据输入类型选择")
    print("请选择问题数据输入类型：")
    print("1. 单个问题文件（包含所有算子的问题）")
    print("2. 问题文件夹（每个算子有独立的文件）")
    
    input_type_choice = get_user_input("请选择输入类型 (1 或 2)", "1")
    
    if input_type_choice == "1":
        input_type = "file"
        print("\n【步骤3】问题文件输入")
        print("问题文件格式示例：")
        print('''[
  {
    "Problem": "Find the value of x when x AND y = True",
    "Query": "What is x?",
    "Declaration": "x: Boolean, y: Boolean",
    "Facts": "y = True"
  }
]''')
        problems_path = get_user_input("请输入问题文件路径", "/data/train/batch_1000per/chunk_0001.json")
    else:
        input_type = "directory"
        print("\n【步骤3】问题文件夹输入")
        print("文件夹结构示例：")
        print('''问题文件夹/
├── AND.json
├── Abs.json
├── Real.json
└── ...（其他算子）''')
        problems_path = get_user_input("请输入问题文件夹路径", "/data/batch")
    
    # 检查问题输入路径是否存在
    while not os.path.exists(problems_path):
        print(f"错误：路径不存在: {problems_path}")
        if input_type == "file":
            problems_path = get_user_input("请重新输入问题文件路径", "/data/train/batch_1000per/chunk_0001.json")
        else:
            problems_path = get_user_input("请重新输入问题文件夹路径", "/data/batch")
    
    # 获取输出目录
    print("\n【步骤4】输出目录设置")
    output_dir = get_user_input("请输入输出目录路径", "data/train/initial")
    
    # 获取输出文件名
    print("\n【步骤5】输出文件设置")
    print("注意：所有算子的结果将整合到一个文件中")
    output_filename = get_user_input("请输入输出文件名", "all_operators_keywords.json")
    
    # 显示配置摘要
    print("\n" + "=" * 60)
    print("配置摘要")
    print("=" * 60)
    print(f"算子列表文件: {operators_file}")
    print(f"问题数据路径: {problems_path}")
    print(f"输入类型: {'单个文件' if input_type == 'file' else '文件夹'}")
    print(f"输出目录: {output_dir}")
    print(f"输出文件: {output_filename}")
    print(f"所有结果将整合到: {os.path.join(output_dir, output_filename)}")
    print()
    
    # 确认配置
    if not get_yes_no_input("是否开始处理？"):
        print("用户取消处理。")
        return
    
    print("\n" + "=" * 60)
    print("开始处理...")
    print("=" * 60)
    
    # 处理所有算子
    try:
        summary = analyzer.process_all_operators(
            operators_file, 
            problems_path,
            output_dir,
            input_type,
            output_filename
        )
        
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        
        return summary
    except Exception as e:
        print(f"\n处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_example_files():
    """创建示例文件，用于测试两种输入形式"""
    
    # 创建示例目录
    os.makedirs("example_inputs", exist_ok=True)
    
    # 创建算子列表文件
    operators_list = [
        {"Assertional_Logic": "AND"},
        {"Assertional_Logic": "Abs"},
        {"Assertional_Logic": "Real"}
    ]
    
    # 1. 创建文件夹形式的示例
    os.makedirs("example_inputs/problems_directory", exist_ok=True)
    
    # 创建AND.json问题文件
    and_problems = [
        {
            "Problem": "Find the value of x when x AND y = True",
            "Query": "What is x?",
            "Declaration": "x: Boolean, y: Boolean",
            "Facts": "y = True"
        },
        {
            "Problem": "Calculate the logical AND of A and B",
            "Query": "What is the result?",
            "Declaration": "A: Boolean, B: Boolean",
            "Facts": "A = True, B = False"
        }
    ]
    
    with open("example_inputs/problems_directory/AND.json", "w", encoding="utf-8") as f:
        json.dump(and_problems, f, indent=2, ensure_ascii=False)
    
    # 创建Abs.json问题文件
    abs_problems = [
        {
            "Problem": "Find the absolute value of -5",
            "Query": "What is | -5 |?",
            "Declaration": "x: Integer",
            "Facts": "x = -5"
        }
    ]
    
    with open("example_inputs/problems_directory/Abs.json", "w", encoding="utf-8") as f:
        json.dump(abs_problems, f, indent=2, ensure_ascii=False)
    
    # 创建Real.json问题文件
    real_problems = [
        {
            "Problem": "Determine if 3.14 is a real number",
            "Query": "Is it real?",
            "Declaration": "x: Number",
            "Facts": "x = 3.14"
        }
    ]
    
    with open("example_inputs/problems_directory/Real.json", "w", encoding="utf-8") as f:
        json.dump(real_problems, f, indent=2, ensure_ascii=False)
    
    # 2. 创建文件形式的示例（包含所有问题的单个文件）
    all_problems = [
        {
            "Problem": "Find the value of x when x AND y = True",
            "Query": "What is x?",
            "Declaration": "x: Boolean, y: Boolean",
            "Facts": "y = True"
        },
        {
            "Problem": "Calculate the logical AND of A and B",
            "Query": "What is the result?",
            "Declaration": "A: Boolean, B: Boolean",
            "Facts": "A = True, B = False"
        },
        {
            "Problem": "Find the absolute value of -5",
            "Query": "What is | -5 |?",
            "Declaration": "x: Integer",
            "Facts": "x = -5"
        },
        {
            "Problem": "Determine if 3.14 is a real number",
            "Query": "Is it real?",
            "Declaration": "x: Number",
            "Facts": "x = 3.14"
        }
    ]
    
    with open("example_inputs/all_problems.json", "w", encoding="utf-8") as f:
        json.dump(all_problems, f, indent=2, ensure_ascii=False)
    
    # 保存算子列表文件
    with open("example_inputs/operators.json", "w", encoding="utf-8") as f:
        json.dump(operators_list, f, indent=2, ensure_ascii=False)
    
    print("示例文件已创建在 'example_inputs/' 目录中:")
    print("├── operators.json                 (算子列表)")
    print("├── all_problems.json              (单个问题文件)")
    print("└── problems_directory/            (问题文件夹)")
    print("    ├── AND.json")
    print("    ├── Abs.json")
    print("    └── Real.json")
    print("\n使用说明:")
    print("1. 运行程序: python script.py")
    print("2. 根据提示输入相应文件路径")
    print("3. 选择输入类型（文件或文件夹）")
    print("4. 设置输出文件名")
    print("5. 等待处理完成")
    print("6. 所有结果将整合到一个文件中")

if __name__ == "__main__":
    # 如果需要创建示例文件进行测试，可以取消下面的注释
    # create_example_files()
    
    # 运行交互式主函数
    main()