"""
雅思备考智能教练 - 简化版数据库
只关注：学习计划 + 打卡记录 + 用户配置
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IELTSCoachDB:
    def __init__(self, db_path: str = None):
        # 支持环境变量配置数据库路径，便于部署
        if db_path is None:
            db_path = os.getenv("IELTS_DB_PATH", "ielts_coach.db")
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
                    target_score REAL NOT NULL,  -- 目标分数 7.5
                    current_level TEXT NOT NULL, -- 当前水平 "四级440+"
                    daily_hours INTEGER NOT NULL, -- 每日学习时间 2
                    vocab_tool TEXT,             -- 词汇工具 "墨墨背单词"
                    start_date TEXT NOT NULL,    -- 开始日期
                    exam_date TEXT,              -- 考试日期（可选）
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 学习计划表（系统生成的每日任务）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_date TEXT NOT NULL,      -- 任务日期
                    task_type TEXT NOT NULL,      -- 听力/阅读/写作/口语
                    task_description TEXT NOT NULL, -- 任务描述
                    resource_url TEXT,            -- 资源链接
                    difficulty_level INTEGER,     -- 难度等级 1-5
                    week_number INTEGER,          -- 第几周
                    phase TEXT,                   -- 阶段：基础/专项/冲刺
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(plan_date, task_type)
                )
            ''')
            
            # 打卡记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkin_date TEXT NOT NULL,   -- 打卡日期
                    task_type TEXT NOT NULL,      -- 听力/阅读/写作/口语
                    completed BOOLEAN DEFAULT 0,  -- 是否完成
                    completed_at TIMESTAMP,       -- 完成时间
                    notes TEXT,                   -- 备注（可选）
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(checkin_date, task_type)
                )
            ''')
            
            # 能力评估表（用于雷达图）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skill_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_date TEXT NOT NULL, -- 评估日期
                    listening_score REAL,          -- 听力分数 1-9
                    reading_score REAL,           -- 阅读分数
                    writing_score REAL,           -- 写作分数  
                    speaking_score REAL,          -- 口语分数
                    overall_score REAL,           -- 总分
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("雅思教练数据库初始化完成")
    
    # 用户配置相关
    def set_user_config(self, target_score: float, current_level: str, 
                       daily_hours: int, vocab_tool: str = "墨墨背单词",
                       exam_date: str = None) -> int:
        """设置用户配置"""
        start_date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 清空旧配置（只保留最新）
            cursor.execute("DELETE FROM user_config")
            
            cursor.execute('''
                INSERT INTO user_config 
                (target_score, current_level, daily_hours, vocab_tool, start_date, exam_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (target_score, current_level, daily_hours, vocab_tool, start_date, exam_date))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_config(self) -> Optional[Dict]:
        """获取用户配置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # 学习计划相关
    def generate_initial_plan(self, weeks: int = 12):
        """生成初始学习计划（简化版，后续会替换为智能算法）"""
        user_config = self.get_user_config()
        if not user_config:
            raise ValueError("请先设置用户配置")
        
        start_date = datetime.strptime(user_config['start_date'], '%Y-%m-%d')
        
        # 简单示例：生成12周的计划
        for week in range(weeks):
            for day in range(7):  # 每周7天
                plan_date = (start_date + timedelta(days=week*7 + day)).strftime('%Y-%m-%d')
                
                # 每天4个任务：听说读写
                tasks = [
                    {
                        'type': 'listening',
                        'desc': '听力练习',
                        'url': 'https://example.com/listening',
                        'difficulty': min(week // 4 + 1, 5)  # 每4周难度+1
                    },
                    {
                        'type': 'reading', 
                        'desc': '阅读练习',
                        'url': 'https://example.com/reading',
                        'difficulty': min(week // 4 + 1, 5)
                    },
                    {
                        'type': 'writing',
                        'desc': '写作练习', 
                        'url': 'https://example.com/writing',
                        'difficulty': min(week // 4 + 1, 5)
                    },
                    {
                        'type': 'speaking',
                        'desc': '口语练习',
                        'url': 'https://example.com/speaking',
                        'difficulty': min(week // 4 + 1, 5)
                    }
                ]
                
                for task in tasks:
                    self.add_study_plan(
                        plan_date=plan_date,
                        task_type=task['type'],
                        task_description=task['desc'],
                        resource_url=task['url'],
                        difficulty_level=task['difficulty'],
                        week_number=week + 1,
                        phase='基础' if week < 4 else ('专项' if week < 8 else '冲刺')
                    )
    
    def add_study_plan(self, plan_date: str, task_type: str, task_description: str,
                      resource_url: str = None, difficulty_level: int = 1,
                      week_number: int = 1, phase: str = '基础') -> int:
        """添加学习计划"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO study_plans 
                (plan_date, task_type, task_description, resource_url, difficulty_level, week_number, phase)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (plan_date, task_type, task_description, resource_url, difficulty_level, week_number, phase))
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_plan(self, date: str = None) -> List[Dict]:
        """获取某日的学习计划"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM study_plans 
                WHERE plan_date = ?
                ORDER BY 
                    CASE task_type
                        WHEN 'listening' THEN 1
                        WHEN 'reading' THEN 2
                        WHEN 'writing' THEN 3
                        WHEN 'speaking' THEN 4
                        ELSE 5
                    END
            ''', (date,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # 打卡相关
    def checkin_task(self, date: str, task_type: str, completed: bool = True, notes: str = None):
        """打卡任务"""
        completed_at = datetime.now().isoformat() if completed else None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO checkins 
                (checkin_date, task_type, completed, completed_at, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (date, task_type, 1 if completed else 0, completed_at, notes))
            conn.commit()
    
    def get_daily_checkins(self, date: str = None) -> Dict[str, bool]:
        """获取某日的打卡情况"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_type, completed FROM checkins 
                WHERE checkin_date = ?
            ''', (date,))
            rows = cursor.fetchall()
            return {row['task_type']: bool(row['completed']) for row in rows}
    
    def get_weekly_completion(self, start_date: str, end_date: str) -> Dict:
        """获取每周完成率"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    checkin_date,
                    COUNT(*) as total_tasks,
                    SUM(completed) as completed_tasks
                FROM checkins 
                WHERE checkin_date BETWEEN ? AND ?
                GROUP BY checkin_date
                ORDER BY checkin_date
            ''', (start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # 能力评估相关
    def add_skill_assessment(self, listening_score: float, reading_score: float,
                           writing_score: float, speaking_score: float,
                           overall_score: float = None, notes: str = None):
        """添加能力评估"""
        if overall_score is None:
            overall_score = (listening_score + reading_score + writing_score + speaking_score) / 4
        
        assessment_date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO skill_assessments 
                (assessment_date, listening_score, reading_score, writing_score, speaking_score, overall_score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (assessment_date, listening_score, reading_score, writing_score, speaking_score, overall_score, notes))
            conn.commit()
    
    def get_latest_assessment(self) -> Optional[Dict]:
        """获取最新的能力评估"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM skill_assessments 
                ORDER BY assessment_date DESC 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None

# 单例实例
db_instance = None

def get_db():
    """获取数据库实例"""
    global db_instance
    if db_instance is None:
        db_instance = IELTSCoachDB()
    return db_instance