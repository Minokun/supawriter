# -*- coding: utf-8 -*-
"""
写作风格分析服务（F5 功能）

分析用户上传的范文，提取6维度风格特征：
1. 语气风格 - 正式/口语化/情感化/专业
2. 句式偏好 - 长句/短句/复合句/简单句
3. 用词特征 - 专业术语/通俗/形容词丰富度
4. 段落结构 - 长段/短段/列表使用
5. 开头风格 - 总结式/引用式/故事式/提问式
6. 结尾风格 - 总结式/开放式/呼吁式/留白式
"""

import re
from typing import Dict, List, Any
from datetime import datetime


class StyleAnalyzerService:
    """写作风格分析服务"""

    @classmethod
    def analyze_tone(cls, content: str) -> Dict[str, Any]:
        """
        分析语气风格

        评分维度：
        - 正式度：专业术语、完整句子、较少口语
        - 口语化程度：语气词、省略句、口语表达
        - 情感化程度：感叹词、形容词密度
        - 专业度：行业术语、数据引用、逻辑严密性
        """
        if not content:
            return {'style': 'neutral', 'confidence': 0}

        # 1. 检测正式度（专业术语、完整句子）
        formal_indicators = [
            '认为', '指出', '表示', '综上所述', '此外', '因此',
            '数据分析', '研究显示', '根据', '鉴于'
        ]
        formal_count = sum(1 for ind in formal_indicators if ind in content)

        # 2. 检测口语化（语气词、省略句）
        colloquial_indicators = [
            '嘛', '哈', '哎', '嗯', '哦', '嘿', '嘛',
            '咱们', '那个', '这个', '就是', '的话'
        ]
        colloquial_count = sum(1 for ind in colloquial_indicators if ind in content)

        # 3. 检测情感化（感叹词、形容词）
        emotional_indicators = [
            '!', '！', '太', '超', '非常', '特别', '真心',
            '哇', '哈', '嘿', '啊', '嘛'
        ]
        emotional_count = sum(1 for ind in emotional_indicators if ind in content)

        # 判断风格
        if formal_count > colloquial_count * 2 and emotional_count < formal_count / 3:
            return {
                'style': 'formal',
                'label': '正式风格',
                'description': '表达规范、逻辑严密，适合专业内容',
                'confidence': min(85, 50 + formal_count * 5)
            }
        elif colloquial_count > formal_count * 2:
            return {
                'style': 'colloquial',
                'label': '口语化风格',
                'description': '表达生动、接近日常交流，适合生活分享',
                'confidence': min(85, 50 + colloquial_count * 5)
            }
        elif emotional_count > formal_count * 1.5:
            return {
                'style': 'emotional',
                'label': '情感化风格',
                'description': '情感丰富、感染力强，适合故事讲述',
                'confidence': min(85, 50 + emotional_count * 5)
            }
        else:
            return {
                'style': 'neutral',
                'label': '中性风格',
                'description': '表达平衡、简洁清晰',
                'confidence': 70
            }

    @classmethod
    def analyze_sentence_structure(cls, content: str) -> Dict[str, Any]:
        """
        分析句式偏好

        评分维度：
        - 平均句长
        - 长句占比（>30字）
        - 短句占比（<15字）
        - 复合句使用
        """
        if not content:
            return {'type': 'balanced', 'label': '平衡'}

        # 分割句子
        sentences = re.split(r'[。！？；；]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {'type': 'balanced', 'label': '平衡'}

        # 计算句长分布
        sentence_lengths = [len(s) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)

        long_sentences = len([s for s in sentence_lengths if s > 30])
        short_sentences = len([s for s in sentence_lengths if s < 15])

        long_ratio = long_sentences / len(sentences)
        short_ratio = short_sentences / len(sentences)

        if long_ratio > 0.4:
            return {
                'type': 'long_sentence',
                'label': '长句为主',
                'description': '习惯使用长句，表达细腻但可能影响阅读速度',
                'avg_length': round(avg_length)
            }
        elif short_ratio > 0.5:
            return {
                'type': 'short_sentence',
                'label': '短句为主',
                'description': '善用短句，节奏明快，适合快速阅读',
                'avg_length': round(avg_length)
            }
        else:
            return {
                'type': 'balanced',
                'label': '句式平衡',
                'description': '长短句搭配合理，阅读节奏舒适',
                'avg_length': round(avg_length)
            }

    @classmethod
    def analyze_vocabulary(cls, content: str) -> Dict[str, Any]:
        """
        分析用词特征

        评分维度：
        - 专业术语密度
        - 形容词密度
        - 词汇丰富度（去重词数/总词数）
        """
        if not content:
            return {'type': 'standard', 'label': '标准'}

        # 提取中文词
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
        total_words = len(chinese_words)

        if total_words == 0:
            return {'type': 'standard', 'label': '标准'}

        # 计算词汇丰富度
        unique_words = len(set(chinese_words))
        richness = unique_words / total_words if total_words > 0 else 0

        # 专业术语检测（常见行业词）
        professional_terms = [
            '算法', '架构', '优化', '性能', '部署', '策略',
            '营销', '转化', '流量', '用户画像', '增长',
            '运营', '转化率', '留存', '活跃', '获客'
        ]
        pro_count = sum(1 for term in professional_terms if term in content)
        pro_density = pro_count / total_words if total_words > 0 else 0

        # 形容词检测
        # 简单检测：包含"的"、"很"、"非常"等词
        adj_indicators = content.count('的') + content.count('很') + content.count('非常')
        adj_density = adj_indicators / total_words if total_words > 0 else 0

        if pro_density > 0.05:
            return {
                'type': 'professional',
                'label': '专业术语丰富',
                'description': '使用大量行业术语，适合专业内容创作',
                'richness': round(richness * 100, 1)
            }
        elif adj_density > 0.3:
            return {
                'type': 'descriptive',
                'label': '描述性强',
                'description': '形容词使用频繁，内容生动形象',
                'richness': round(richness * 100, 1)
            }
        elif richness > 0.8:
            return {
                'type': 'rich',
                'label': '词汇丰富',
                'description': '用词多样，表达能力强',
                'richness': round(richness * 100, 1)
            }
        else:
            return {
                'type': 'standard',
                'label': '标准',
                'description': '用词规范，表达清晰',
                'richness': round(richness * 100, 1)
            }

    @classmethod
    def analyze_paragraph_structure(cls, content: str) -> Dict[str, Any]:
        """
        分析段落结构

        评分维度：
        - 平均段长
        - 短段占比（<100字）
        - 长段占比（>300字）
        - 列表使用频率
        """
        if not content:
            return {'type': 'standard', 'label': '标准'}

        # 分割段落
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if not paragraphs:
            return {'type': 'standard', 'label': '标准'}

        # 计算段长
        paragraph_lengths = [len(p) for p in paragraphs]
        avg_length = sum(paragraph_lengths) / len(paragraph_lengths)

        short_para = len([l for l in paragraph_lengths if l < 100])
        long_para = len([l for l in paragraph_lengths if l > 300])

        short_ratio = short_para / len(paragraphs)
        long_ratio = long_para / len(paragraphs)

        # 检测列表使用
        bullet_count = len(re.findall(r'^[\-\*]\s', content, re.MULTILINE))
        numbered_count = len(re.findall(r'^\d+\.\s', content, re.MULTILINE))
        total_lists = bullet_count + numbered_count

        if total_lists > len(paragraphs) * 0.5:
            return {
                'type': 'list_based',
                'label': '列表为主',
                'description': '善用列表形式组织内容，条理清晰',
                'avg_length': round(avg_length)
            }
        elif long_ratio > 0.4:
            return {
                'type': 'long_paragraph',
                'label': '长段落为主',
                'description': '段落较长，内容连贯，但可能影响阅读',
                'avg_length': round(avg_length)
            }
        elif short_ratio > 0.6:
            return {
                'type': 'short_paragraph',
                'label': '短段落为主',
                'description': '段落短小，节奏明快',
                'avg_length': round(avg_length)
            }
        else:
            return {
                'type': 'balanced',
                'label': '段落平衡',
                'description': '段落长度适中，结构清晰',
                'avg_length': round(avg_length)
            }

    @classmethod
    def analyze_opening_style(cls, content: str) -> Dict[str, Any]:
        """
        分析开头风格

        评分维度：
        - 总结式：文章开始就给出结论
        - 引用式：以引用/名言开头
        - 故事式：以场景描述/故事开头
        - 提问式：以问题开头
        """
        if not content:
            return {'type': 'direct', 'label': '直叙'}

        # 取前200字分析
        opening = content[:200]

        # 检测各种开头模式
        summary_patterns = [
            '总的来说', '综上', '简而言之', '一句话', '直接说',
            '结论是', '结果是'
        ]

        quote_patterns = [
            '说得好', '古人云', '俗话说', '正如', '引用',
            '"', '"', "'", "'"
        ]

        story_patterns = [
            '记得', '那天', '小时候', '在', '经过',
            '场景', '画面'
        ]

        question_patterns = [
            '？', '?', '吗', '怎么', '如何', '为什么',
            '你是否', '大家是否', '你是否想'
        ]

        summary_count = sum(1 for p in summary_patterns if p in opening)
        quote_count = sum(1 for p in quote_patterns if p in opening)
        story_count = sum(1 for p in story_patterns if p in opening)
        question_count = sum(1 for p in question_patterns if p in opening)

        # 判断主要风格
        max_count = max(summary_count, quote_count, story_count, question_count)

        if max_count == 0:
            return {
                'type': 'direct',
                'label': '直叙式',
                'description': '直接进入主题，开门见山'
            }
        elif max_count == summary_count and summary_count > 0:
            return {
                'type': 'summary',
                'label': '总结式',
                'description': '先给出结论，再展开论述'
            }
        elif max_count == quote_count and quote_count > 0:
            return {
                'type': 'quote',
                'label': '引用式',
                'description': '以引用或名言开头，增加权威感'
            }
        elif max_count == story_count and story_count > 0:
            return {
                'type': 'story',
                'label': '故事式',
                'description': '以场景或故事开头，吸引读者'
            }
        else:
            return {
                'type': 'question',
                'label': '提问式',
                'description': '以问题开头，引发思考'
            }

    @classmethod
    def analyze_closing_style(cls, content: str) -> Dict[str, Any]:
        """
        分析结尾风格

        评分维度：
        - 总结式：结尾总结全文
        - 开放式：结尾留有思考空间
        - 呼吁式：结尾呼吁行动
        - 留白式：结尾简洁有力
        """
        if not content:
            return {'type': 'simple', 'label': '简洁'}

        # 取最后200字分析
        closing = content[-200:] if len(content) > 200 else content

        # 检测各种结尾模式
        summary_patterns = [
            '综上所述', '总而言之', '总的来说', '以上',
            '总结', '回顾', '归纳', '概括'
        ]

        call_to_action_patterns = [
            '请', '欢迎', '期待', '希望', '建议',
            '行动', '参与', '关注', '点赞'
        ]

        open_ended_patterns = [
            '思考', '期待', '未来', '继续', '探索',
            '...', '……'
        ]

        summary_count = sum(1 for p in summary_patterns if p in closing)
        call_to_action_count = sum(1 for p in call_to_action_patterns if p in closing)
        open_ended_count = sum(1 for p in open_ended_patterns if p in closing)

        # 判断主要风格
        max_count = max(summary_count, call_to_action_count, open_ended_count)

        if max_count == 0:
            return {
                'type': 'simple',
                'label': '简洁收尾',
                'description': '结尾简洁有力，不拖泥带水'
            }
        elif max_count == summary_count and summary_count > 0:
            return {
                'type': 'summary',
                'label': '总结式',
                'description': '结尾总结全文，强化核心观点'
            }
        elif max_count == call_to_action_count and call_to_action_count > 0:
            return {
                'type': 'call_to_action',
                'label': '呼吁式',
                'description': '结尾呼吁行动，促进用户参与'
            }
        else:
            return {
                'type': 'open_ended',
                'label': '开放式',
                'description': '结尾留有余韵，引发读者思考'
            }

    @classmethod
    def analyze_sample(cls, content: str) -> Dict[str, Any]:
        """
        分析范文样本，提取完整风格画像

        Returns:
            包含6维度分析的字典
        """
        if not content or len(content) < 500:
            return {
                'error': '范文内容太短，至少需要500字',
                'tone': None,
                'sentence_style': None,
                'vocabulary': None,
                'paragraph_structure': None,
                'opening_style': None,
                'closing_style': None
            }

        return {
            'tone': cls.analyze_tone(content),
            'sentence_style': cls.analyze_sentence_structure(content),
            'vocabulary': cls.analyze_vocabulary(content),
            'paragraph_structure': cls.analyze_paragraph_structure(content),
            'opening_style': cls.analyze_opening_style(content),
            'closing_style': cls.analyze_closing_style(content)
        }


# 风格分析结果数据模型
class StyleAnalysisResult:
    """风格分析结果"""

    def __init__(
        self,
        user_id: int,
        style_profile: Dict[str, Any],
        sample_filenames: List[str],
        is_active: bool = True
    ):
        self.user_id = user_id
        self.style_profile = style_profile
        self.sample_filenames = sample_filenames
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'style_profile': self.style_profile,
            'sample_filenames': self.sample_filenames,
            'sample_count': len(self.sample_filenames),
            'is_active': self.is_active
        }
