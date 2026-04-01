"""
雅思备考智能教练 - 主题周学习计划版
根据Leon的需求定制：主题周 + 任务型学习 + 游戏化元素
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IELTSCoachDBV3:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv("IELTS_DB_PATH", "ielts_coach_v3.db")
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_score REAL NOT NULL,
                    current_level TEXT NOT NULL,
                    daily_hours INTEGER NOT NULL,
                    vocab_tool TEXT,
                    interests TEXT,  -- 用户兴趣JSON数组
                    start_date TEXT NOT NULL,
                    exam_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 主题周配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_number INTEGER NOT NULL,
                    theme_name TEXT NOT NULL,      -- 主题名称
                    theme_description TEXT,        -- 主题描述
                    focus_skills TEXT,             -- 重点技能
                    vocabulary_count INTEGER,      -- 本周词汇目标
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(week_number)
                )
            ''')
            
            # 学习任务表（按主题和任务类型）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_date TEXT NOT NULL,
                    task_type TEXT NOT NULL,        -- 任务类型：词汇/听力/综合等
                    task_title TEXT NOT NULL,       -- 任务标题
                    task_description TEXT NOT NULL, -- 详细描述
                    task_icon TEXT,                 -- 任务图标
                    resource_url TEXT,              -- 资源链接
                    difficulty_level INTEGER,       -- 难度等级
                    estimated_minutes INTEGER,      -- 预计时间
                    week_number INTEGER,            -- 第几周
                    theme_name TEXT,                -- 所属主题
                    points INTEGER DEFAULT 10,      -- 完成任务获得积分
                    streak_days INTEGER DEFAULT 0,  -- 连续打卡天数
                    completed BOOLEAN DEFAULT 0,    -- 是否完成
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 用户进度表（游戏化元素）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    total_points INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    badges TEXT,                    -- 获得的徽章JSON
                    level INTEGER DEFAULT 1,
                    vocabulary_mastered INTEGER DEFAULT 0,
                    last_active_date TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("主题周学习计划数据库初始化完成")
    
    # 用户配置相关
    def set_user_config(self, target_score: float, current_level: str, 
                       daily_hours: int, vocab_tool: str = "墨墨背单词",
                       interests: List[str] = None, exam_date: str = None) -> int:
        """设置用户配置"""
        start_date = datetime.now().strftime('%Y-%m-%d')
        interests_json = json.dumps(interests) if interests else '[]'
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_config")
            
            cursor.execute('''
                INSERT INTO user_config 
                (target_score, current_level, daily_hours, vocab_tool, interests, start_date, exam_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (target_score, current_level, daily_hours, vocab_tool, interests_json, start_date, exam_date))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_config(self) -> Optional[Dict]:
        """获取用户配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                config = dict(row)
                config['interests'] = json.loads(config['interests']) if config['interests'] else []
                return config
            return None
    
    # 主题周配置
    def setup_weekly_themes(self, user_interests: List[str]):
        """设置12周主题周计划"""
        # 基础主题（雅思常考）
        base_themes = [
            "教育学习", "科技发展", "环境保护", "文化艺术",
            "健康生活", "社会发展", "经济发展", "全球化"
        ]
        
        # 结合用户兴趣的主题
        interest_themes = []
        interest_map = {
            '科技': ['人工智能', '数字生活', '科技创新', '未来科技'],
            '美食': ['饮食文化', '健康饮食', '美食旅游', '烹饪艺术'],
            '旅行': ['旅游体验', '文化遗产', '冒险旅行', '城市探索'],
            '艺术': ['视觉艺术', '设计思维', '创意表达', '艺术史']
        }
        
        for interest in user_interests:
            if interest in interest_map:
                interest_themes.extend(interest_map[interest][:2])  # 每个兴趣选2个主题
        
        # 合并主题，确保12周
        all_themes = interest_themes + base_themes
        if len(all_themes) < 12:
            all_themes = all_themes + base_themes * 2  # 重复基础主题补足
        
        themes = all_themes[:12]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM weekly_themes")
            
            for week in range(12):
                theme = themes[week]
                theme_desc = self._get_theme_description(theme, week+1)
                focus_skills = self._get_focus_skills_for_week(week+1)
                vocab_count = 50 + (week * 10)  # 每周增加10个词汇
                
                cursor.execute('''
                    INSERT INTO weekly_themes 
                    (week_number, theme_name, theme_description, focus_skills, vocabulary_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (week+1, theme, theme_desc, focus_skills, vocab_count))
            
            conn.commit()
    
    def _get_theme_description(self, theme: str, week: int) -> str:
        """获取主题描述"""
        descriptions = {
            "教育学习": f"第{week}周：探索教育体系、学习方法、校园生活，掌握教育类话题的高频词汇和表达。",
            "科技发展": f"第{week}周：讨论人工智能、数字技术、科技创新，学习科技类学术词汇和论述技巧。",
            "环境保护": f"第{week}周：关注气候变化、可持续发展、生态保护，掌握环境话题的论证方法。",
            "文化艺术": f"第{week}周：深入艺术、设计、文化传统，学习如何描述和分析文化艺术现象。",
            "人工智能": f"第{week}周：聚焦AI技术、机器学习、智能应用，掌握前沿科技话题的英语表达。",
            "美食旅游": f"第{week}周：结合美食文化和旅行体验，学习描述感受和体验的生动表达。",
            "健康生活": f"第{week}周：探讨健康习惯、运动健身、心理健康，掌握健康话题的实用词汇。",
            "设计思维": f"第{week}周：学习设计理念、创意过程、问题解决，提升描述抽象概念的能力。"
        }
        return descriptions.get(theme, f"第{week}周主题：{theme}，围绕该主题进行全方位英语学习。")
    
    def _get_focus_skills_for_week(self, week: int) -> str:
        """根据周数确定重点技能"""
        if week <= 4:
            return "词汇积累 + 听力基础"
        elif week <= 8:
            return "听力提升 + 阅读技巧"
        else:
            return "综合应用 + 模考训练"
    
    # 智能任务生成
    def generate_theme_based_tasks(self, weeks: int = 12):
        """生成主题周学习任务"""
        user_config = self.get_user_config()
        if not user_config:
            raise ValueError("请先设置用户配置")
        
        # 先设置主题周
        self.setup_weekly_themes(user_config['interests'])
        
        start_date = datetime.strptime(user_config['start_date'], '%Y-%m-%d')
        
        # 获取主题周配置
        weekly_themes = self.get_weekly_themes()
        
        # 任务类型库（短时高频）
        task_templates = {
            'vocabulary': [
                {
                    'title': '主题词汇速记',
                    'desc_template': '学习{theme}相关的{count}个高频词汇',
                    'icon': '📚',
                    'minutes': 15
                },
                {
                    'title': '词汇应用练习',
                    'desc_template': '用本周词汇完成句子填空练习',
                    'icon': '✍️',
                    'minutes': 10
                },
                {
                    'title': '同义替换训练',
                    'desc_template': '掌握{theme}话题的常见同义表达',
                    'icon': '🔄',
                    'minutes': 12
                }
            ],
            'listening': [
                {
                    'title': '主题听力精听',
                    'desc_template': '精听一段关于{theme}的对话/讲座',
                    'icon': '👂',
                    'minutes': 20
                },
                {
                    'title': '听力场景训练',
                    'desc_template': '{theme}相关场景的听力理解练习',
                    'icon': '🎧',
                    'minutes': 15
                },
                {
                    'title': '笔记技巧练习',
                    'desc_template': '练习快速记录{theme}话题的关键信息',
                    'icon': '📝',
                    'minutes': 18
                }
            ],
            'integrated': [
                {
                    'title': '主题任务挑战',
                    'desc_template': '完成一个{theme}相关的综合学习任务',
                    'icon': '🎯',
                    'minutes': 25
                },
                {
                    'title': '快速反应训练',
                    'desc_template': '{theme}话题的听说读写快速切换练习',
                    'icon': '⚡',
                    'minutes': 20
                },
                {
                    'title': '游戏化练习',
                    'desc_template': '通过小游戏巩固{theme}学习内容',
                    'icon': '🎮',
                    'minutes': 15
                }
            ]
        }
        
        # 资源库（按主题分类）
        theme_resources = {
            "教育学习": {
                'vocabulary': 'https://www.xdf.cn/ielts/vocabulary/education',
                'listening': 'https://www.ielts.org/en-us/prepare/free-ielts-practice-tests/listening',
                'integrated': 'https://ieltsliz.com/ielts-education-topic/'
            },
            "科技发展": {
                'vocabulary': 'https://www.xdf.cn/ielts/vocabulary/technology',
                'listening': 'https://www.cambridgeenglish.org/exams-and-tests/ielts/preparation/',
                'integrated': 'https://www.ieltsadvantage.com/technology-essays/'
            },
            "美食旅游": {
                'vocabulary': 'https://www.xdf.cn/ielts/vocabulary/travel',
                'listening': 'https://www.youtube.com/playlist?list=PLD6t6ckHsruYVv8Jm5nFxJX3q3ZQ5Z5Y5',
                'integrated': 'https://ieltsliz.com/ielts-travel-tourism-topic/'
            },
            "文化艺术": {
                'vocabulary': 'https://www.xdf.cn/ielts/vocabulary/art',
                'listening': 'https://www.ielts.org/en-us/prepare/free-ielts-practice-tests/listening',
                'integrated': 'https://www.ieltsadvantage.com/culture-essays/'
            }
        }
        
        # 生成12周任务
        for week in range(weeks):
            theme_info = weekly_themes[week]
            theme_name = theme_info['theme_name']
            
            for day in range(7):
                plan_date = (start_date + timedelta(days=week*7 + day)).strftime('%Y-%m-%d')
                
                # 每天3个短时高频任务
                daily_tasks = []
                
                # 任务1：词汇任务（每天都有，重点满足需求）
                vocab_task = random.choice(task_templates['vocabulary'])
                daily_tasks.append({
                    'type': 'vocabulary',
                    'template': vocab_task,
                    'resource_type': 'vocabulary'
                })
                
                # 任务2：听力任务（重点满足需求）
                listening_task = random.choice(task_templates['listening'])
                daily_tasks.append({
                    'type': 'listening',
                    'template': listening_task,
                    'resource_type': 'listening'
                })
                
                # 任务3：综合任务（游戏化/任务型）
                integrated_task = random.choice(task_templates['integrated'])
                daily_tasks.append({
                    'type': 'integrated',
                    'template': integrated_task,
                    'resource_type': 'integrated'
                })
                
                # 创建任务
                for task_idx, task_info in enumerate(daily_tasks):
                    task_type = task_info['type']
                    template = task_info['template']
                    resource_type = task_info['resource_type']
                    
                    # 生成任务描述
                    desc = template['desc_template'].format(
                        theme=theme_name,
                        count=theme_info['vocabulary_count']
                    )
                    
                    # 获取资源链接
                    resource_url = theme_resources.get(theme_name, {}).get(resource_type)
                    if not resource_url:
                        # 默认资源
                        resource_url = {
                            'vocabulary': 'https://www.xdf.cn/ielts/vocabulary/',
                            'listening': 'https://www.ielts.org/en-us/prepare/free-ielts-practice-tests/listening',
                            'integrated': 'https://ieltsliz.com/'
                        }[resource_type]
                    
                    # 难度计算
                    difficulty = min(1 + (week // 4) + (day % 3) * 0.3, 5)
                    
                    # 积分计算（基础分 + 难度加成）
                    points = template['minutes'] // 5 + int(difficulty)
                    
                    self.add_learning_task(
                        task_date=plan_date,
                        task_type=task_type,
                        task_title=template['title'],
                        task_description=desc,
                        task_icon=template['icon'],
                        resource_url=resource_url,
                        difficulty_level=int(difficulty),
                        estimated_minutes=template['minutes'],
                        week_number=week+1,
                        theme_name=theme_name,
                        points=points
                    )
    
    def get_weekly_themes(self) -> List[Dict]:
        """获取所有主题周配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM weekly_themes ORDER BY week_number")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def add_learning_task(self, task_date: str, task_type: str, task_title: str,
                         task_description: str, task_icon: str = "📝",
                         resource_url: str = None, difficulty_level: int = 1,
                         estimated_minutes: int = 15, week_number: int = 1,
                         theme_name: str = "", points: int = 10) -> int:
        """添加学习任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO learning_tasks 
                (task_date, task_type, task_title, task_description, task_icon, 
                 resource_url, difficulty_level, estimated_minutes, week_number, 
                 theme_name, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_date, task_type, task_title, task_description, task_icon,
                  resource_url, difficulty_level, estimated_minutes, week_number,
                  theme_name, points))
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_tasks(self, date: str = None) -> List[Dict]:
        """获取某日的学习任务"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM learning_tasks 
                WHERE task_date = ?
                ORDER BY id
            ''', (date,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def complete_task(self, task_id: int):
        """完成任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE learning_tasks 
                SET completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id,))
            conn.commit()
    
    def get_user_progress(self) -> Dict:
        """获取用户进度"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_progress ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                progress = dict(row)
                progress['badges'] = json.loads(progress['badges']) if progress['badges'] else []
                return progress
            
            # 创建初始进度
            cursor.execute('''
                INSERT INTO user_progress (user_id, total_points, level)
                VALUES (1, 0, 1)
            ''')
            conn.commit()
            return {'total_points': 0, 'current_streak': 0, 'longest_streak': 0, 
                    'badges': [], 'level': 1, 'vocabulary_mastered': 0}
    
    def add_points(self, points: int):
        """添加积分"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_progress 
                SET total_points = total_points + ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM user_progress ORDER BY id DESC LIMIT 1)
            ''', (points,))
            conn.commit()
    
    def update_streak(self):
        """更新连续打卡"""
        today = datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_progress 
                SET current_streak = current_streak + 1,
                    last_active_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM user_progress ORDER BY id DESC LIMIT 1)
                AND (last_active_date IS NULL OR last_active_date < ?)
            ''', (today, today))
            conn.commit()
            
            # 更新最长连续打卡
            cursor.execute('''
                UPDATE user_progress 
                SET longest_streak = MAX(longest_streak, current_streak)
                WHERE id = (SELECT id FROM user_progress ORDER BY id DESC LIMIT 1)
            ''')
            conn.commit()
    
    def clear_existing_data(self):
        """清除现有数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM learning_tasks")
            cursor.execute("DELETE FROM weekly_themes")
            conn.commit()
            logger.info("已清除现有学习数据")

# 单例实例
db_instance_v3 = None

def get_db_v3():
    """获取数据库实例"""
    global db_instance_v3
    if db_instance_v3 is None:
        db_instance_v3 = IELTSCoachDBV3()
    return db_instance_v3
