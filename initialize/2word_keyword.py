import json
import re
from collections import Counter
import string
import nltk
import ssl
from typing import List, Dict

class MathVocabularyBuilder:
    def __init__(self, operator_file_path: str):
        """
        初始化，只处理一种算子文件
        
        Args:
            operator_file_path: 算子JSON文件的路径
        """
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
            # 添加额外的数学符号和数字作为停用词
            additional_stop_words = {'=', '+', '-', '*', '/', '(', ')', '[', ']', '{', '}', '<', '>',
                                     '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                                     ':', ',', '.', ';', "'", '"', '!', '?', '@', '#', '$', '%', '^', '&', '_', '~', '`'}
            self.stop_words.update(additional_stop_words)
            print("NLTK已成功加载")
        else:
            # 备选停用词列表，包含额外数学符号和数字
            self.stop_words = set([
                'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'it', 'its', 'they', 'them',
                'their', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'where', 'when',
                'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
                'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
                # 额外添加的数学符号和数字
                '=', '+', '-', '*', '/', '(', ')', '[', ']', '{', '}', '<', '>',
                '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                ':', ',', '.', ';', "'", '"', '!', '?', '@', '#', '$', '%', '^', '&', '_', '~', '`'
            ])
            print("使用备选分词方案")
        
        self.punctuation = set(string.punctuation)
        self.operator_file_path = operator_file_path
    
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
    
    def load_all_data(self):
        """加载数据，只加载算子文件和问题文件"""
        # 加载算子文件
        self.operators = self._load_json_file(self.operator_file_path)
        
        # 加载问题文件
        self.problems = self._load_json_file("/data/train/batch_1000per/chunk_0001.json")
        
        print(f"加载数据完成:")
        print(f"  - 算子: {len(self.operators)}")
        print(f"  - 问题: {len(self.problems)}")
    
    def _load_json_file(self, filename):
        """加载JSON文件"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: 文件 {filename} 未找到")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析错误 {filename}: {e}")
            return []
    
    def preprocess_text(self, text: str) -> List[str]:
        """预处理文本"""
        if not text:
            return []
        
        try:
            if self.nltk_available:
                tokens = nltk.word_tokenize(str(text).lower())
            else:
                tokens = self.simple_tokenize(str(text))
            
            # 过滤处理 - 现在会过滤掉数学符号和数字
            filtered_tokens = [
                token for token in tokens 
                if (token not in self.stop_words and 
                    token not in self.punctuation and
                    len(token) > 1 and
                    not token.replace('.', '').isdigit())
            ]
            
            return filtered_tokens
        except Exception as e:
            print(f"分词错误: {e}")
            return self.simple_tokenize(str(text))
    
    def simple_tokenize(self, text: str) -> List[str]:
        """备选分词函数"""
        text = str(text).lower()
        # 匹配单词、带下划线的单词、数字、特殊数学符号
        tokens = re.findall(r'[a-z]+(?:_[a-z]+)*|\d+\.?\d*|[^a-zA-Z0-9\s]', text)
        return [
            token for token in tokens 
            if len(token) > 0
        ]
    
    def extract_operators(self) -> List[Dict]:
        """从算子文件提取算子信息"""
        operators_list = []
        
        # 处理算子文件
        for item in self.operators:
            # 获取算子名称
            name = item.get("Assertional_Logic", "").strip()
            if not name:
                continue
                
            operators_list.append({
                "Assertional_Logic": name,
                "explanation": item.get("Explanation", ""),
                "lean_code": item.get("Lean4_Code", ""),
                "description": item.get("Description", ""),
                "formula": item.get("Formula", ""),
                "examples": item.get("Examples", "")
            })
        
        print(f"总共提取了 {len(operators_list)} 个算子")
        return operators_list
    
    def extract_keywords_for_operator(self, operator: Dict) -> List[Dict[str, int]]:
        """提取算子的关键词和权重，将权重限制在1~5之间，算子本身不作为关键词"""
        op_name = operator["Assertional_Logic"]
        
        # 收集所有相关的文本，下面的策略只是根据本人目前手边的数据进行的设定，使用者可以根据现有条件自行增添
        all_texts = []
        
        # 1. 算子自身的描述信息
        all_texts.append(operator.get("explanation", ""))
        all_texts.append(operator.get("description", ""))
        all_texts.append(operator.get("formula", ""))
        all_texts.append(operator.get("examples", ""))
        all_texts.append(operator.get("lean_code", ""))
        
        # 2. 收集所有相关问题的文本
        for problem in self.problems:
            problem_text = problem.get("Problem", "")
            query = problem.get("Query", "")
            declaration = problem.get("Declaration", "")
            facts = problem.get("Facts", "")
            
            all_text = f"{problem_text} {query} {declaration} {facts}".lower()
            
            # 检查算子名称是否出现在问题文本中
            if op_name.lower() in all_text:
                all_texts.append(all_text)
            else:
                # 检查算子解释中的关键词是否出现在问题中
                op_explanation = operator.get("explanation", "").lower()
                op_description = operator.get("description", "").lower()
                op_keywords = self.preprocess_text(op_explanation + " " + op_description)
                problem_keywords = self.preprocess_text(all_text)
                
                # 如果有重叠的关键词，则添加该问题文本
                keyword_overlap = set(op_keywords) & set(problem_keywords)
                if len(keyword_overlap) > 0:
                    all_texts.append(all_text)
        
        # 3. 合并所有文本并提取关键词
        combined_text = " ".join(all_texts)
        
        # 使用不同的分词策略提取更丰富的关键词
        keywords = []
        
        # 策略1: 提取普通单词
        word_tokens = self.preprocess_text(combined_text)
        keywords.extend(word_tokens)
        
        # 策略2: 提取特殊符号和数学表达式
        math_symbols = re.findall(r'[+\-*/=<>≤≥≠±∞∝√∛∫∑∏∂∇⋅×÷→⇒⇔∀∃∈∉⊂⊆∪∩∅∨∧¬⊕⊗⊖⊙°θαβγδϵζηθικλμνξοπρστυφχψω∆∇≡≈≅∼≃≪≫⊢⊨⊩⊢⊣⊤⊥⊢⊨⊩⊢⊣⊤⊥]', combined_text)
        keywords.extend(math_symbols)
        
        # 策略3: 提取数字和公式模式
        number_patterns = re.findall(r'\d+\.?\d*|\d+/\d+|[a-z]+\^?\d+', combined_text)
        keywords.extend(number_patterns)
        
        # 策略4: 提取带特殊字符的组合
        special_patterns = re.findall(r'[a-zA-Z]+[+\-*/^=<>]+[a-zA-Z\d]+|[a-zA-Z]+\^?\d+', combined_text)
        keywords.extend(special_patterns)
        
        # 注意：策略5已移除，算子名称本身不再作为关键词
        
        # 统计词频
        keyword_counter = Counter(keywords)
        
        # 转换为所需的格式，并将权重限制在1~5之间
        keyword_weights = []
        for keyword, weight in keyword_counter.most_common():
            # 过滤掉算子名称本身（算子不能算作关键词）
            if keyword.lower() == op_name.lower():
                continue
                
            # 过滤掉太短或太常见的词（包括数学符号和数字）
            if (len(keyword) > 0 and 
                keyword not in self.stop_words and
                keyword not in self.punctuation and
                not keyword.isdigit() and  # 排除纯数字
                weight >= 1):  # 只保留出现至少一次的
                
                # 限制权重在1~5之间
                limited_weight = min(weight, 5)
                
                keyword_weights.append({
                    "key_word": keyword,
                    "weight": limited_weight
                })
        
        return keyword_weights
    
    def build_keyword_library(self) -> List[Dict]:
        """建立关键词库，输出格式完全符合要求"""
        # 提取算子
        operators_list = self.extract_operators()
        
        # 构建关键词库
        keyword_library = []
        
        for operator in operators_list:
            op_name = operator["Assertional_Logic"]
            print(f"处理算子: {op_name}")
            
            # 提取关键词和权重
            keyword_weights = self.extract_keywords_for_operator(operator)
            
            # 构建严格符合格式的输出
            keyword_entry = {
                "Assertional_Logic": op_name,
                "key_words": keyword_weights
            }
            
            keyword_library.append(keyword_entry)
        
        return keyword_library
    
    def save_keyword_library(self, keyword_library: List[Dict], 
                           filename: str = "operator_keywords.json"):
        """保存关键词库到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(keyword_library, f, indent=2, ensure_ascii=False)
        
        print(f"关键词库已保存到: {filename}")
        print(f"格式验证: 输出文件包含 {len(keyword_library)} 个算子")
    
    def analyze_keyword_statistics(self, keyword_library: List[Dict]):
        """分析关键词统计信息"""
        print(f"\n=== 关键词统计 ===")
        print(f"总算子数: {len(keyword_library)}")
        
        total_keywords = 0
        keywords_per_operator = []
        weight_stats = []
        
        for operator in keyword_library:
            num_keywords = len(operator["key_words"])
            total_keywords += num_keywords
            keywords_per_operator.append(num_keywords)
            
            # 收集所有关键词的权重
            for kw in operator["key_words"]:
                weight_stats.append(kw["weight"])
        
        if keywords_per_operator:
            avg_keywords = total_keywords / len(keyword_library)
            max_keywords = max(keywords_per_operator)
            min_keywords = min(keywords_per_operator)
            
            print(f"总关键词数: {total_keywords}")
            print(f"平均每个算子关键词数: {avg_keywords:.1f}")
            print(f"最大关键词数: {max_keywords}")
            print(f"最小关键词数: {min_keywords}")
        
        if weight_stats:
            avg_weight = sum(weight_stats) / len(weight_stats)
            max_weight = max(weight_stats)
            min_weight = min(weight_stats)
            
            print(f"\n权重统计:")
            print(f"  平均权重: {avg_weight:.1f}")
            print(f"  最大权重: {max_weight}")
            print(f"  最小权重: {min_weight}")
            
            # 统计权重分布
            weight_dist = {}
            for weight in weight_stats:
                if weight not in weight_dist:
                    weight_dist[weight] = 0
                weight_dist[weight] += 1
            
            print(f"  权重分布:")
            for weight in sorted(weight_dist.keys()):
                print(f"    权重{weight}: {weight_dist[weight]}个")
        
        # 显示关键词最多的算子
        top_keyword_operators = sorted(
            [(op["Assertional_Logic"], len(op["key_words"])) 
             for op in keyword_library],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        print(f"\n关键词最多的前10个算子:")
        for op, count in top_keyword_operators:
            print(f"  {op}: {count}个关键词")
        
        # 统计没有关键词的算子
        operators_without_keywords = [op["Assertional_Logic"] for op in keyword_library if len(op["key_words"]) == 0]
        if operators_without_keywords:
            print(f"\n没有关键词的算子 ({len(operators_without_keywords)} 个):")
            for op in operators_without_keywords[:10]:
                print(f"  - {op}")
            if len(operators_without_keywords) > 10:
                print(f"  ... 还有 {len(operators_without_keywords)-10} 个")

def main():
    """主函数"""
    # 指定要处理的算子文件路径
    operator_file_path = "/data/train/initial/Assertional_Logic.json"
    
    builder = MathVocabularyBuilder(operator_file_path)
    
    # 1. 加载数据
    builder.load_all_data()
    
    # 2. 构建关键词库
    print("\n正在构建关键词库...")
    keyword_library = builder.build_keyword_library()
    
    # 3. 保存结果
    builder.save_keyword_library(keyword_library, "/data/train/initial/word_keywords.json")
    
    # 4. 分析统计信息
    builder.analyze_keyword_statistics(keyword_library)
    
    # 5. 显示样例输出
    print("\n=== 样例输出 (前2个算子) ===")
    sample_count = min(2, len(keyword_library))
    for i in range(sample_count):
        operator = keyword_library[i]
        print(f"\n{json.dumps({'Assertional_Logic': operator['Assertional_Logic'], 'key_words': operator['key_words'][:5]}, indent=2, ensure_ascii=False)}")
    
    return keyword_library

if __name__ == "__main__":
    keyword_library = main()