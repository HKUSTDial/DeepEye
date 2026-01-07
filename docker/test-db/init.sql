-- School Database Schema and Sample Data

-- 学生表
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    student_no VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('男', '女')),
    birth_date DATE,
    grade INT CHECK (grade BETWEEN 1 AND 12),
    class_name VARCHAR(20),
    enrollment_date DATE,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 教师表
CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    teacher_no VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('男', '女')),
    birth_date DATE,
    subject VARCHAR(50),
    title VARCHAR(50),
    hire_date DATE,
    phone VARCHAR(20),
    email VARCHAR(100),
    salary DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 课程表
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    subject VARCHAR(50),
    credit DECIMAL(3, 1),
    hours_per_week INT,
    description TEXT
);

-- 班级表
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    class_name VARCHAR(50) UNIQUE NOT NULL,
    grade INT,
    head_teacher_id INT REFERENCES teachers(id),
    classroom VARCHAR(50),
    student_count INT DEFAULT 0
);

-- 成绩表
CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id),
    course_id INT REFERENCES courses(id),
    teacher_id INT REFERENCES teachers(id),
    score DECIMAL(5, 2) CHECK (score >= 0 AND score <= 100),
    exam_type VARCHAR(20) CHECK (exam_type IN ('期中', '期末', '月考', '模拟')),
    exam_date DATE,
    semester VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 课程安排表
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    class_id INT REFERENCES classes(id),
    course_id INT REFERENCES courses(id),
    teacher_id INT REFERENCES teachers(id),
    weekday INT CHECK (weekday BETWEEN 1 AND 7),
    period INT CHECK (period BETWEEN 1 AND 8),
    semester VARCHAR(20)
);

-- ============ 插入测试数据 ============

-- 插入教师数据
INSERT INTO teachers (teacher_no, name, gender, birth_date, subject, title, hire_date, phone, email, salary) VALUES
('T001', '张明', '男', '1980-03-15', '数学', '高级教师', '2005-09-01', '13800001001', 'zhangming@school.edu', 12000.00),
('T002', '李芳', '女', '1985-07-22', '语文', '一级教师', '2010-09-01', '13800001002', 'lifang@school.edu', 10000.00),
('T003', '王强', '男', '1978-11-08', '英语', '特级教师', '2003-09-01', '13800001003', 'wangqiang@school.edu', 15000.00),
('T004', '刘娜', '女', '1990-04-30', '物理', '二级教师', '2015-09-01', '13800001004', 'liuna@school.edu', 8500.00),
('T005', '陈伟', '男', '1982-09-12', '化学', '一级教师', '2008-09-01', '13800001005', 'chenwei@school.edu', 11000.00),
('T006', '赵丽', '女', '1988-01-25', '生物', '一级教师', '2012-09-01', '13800001006', 'zhaoli@school.edu', 9500.00),
('T007', '孙涛', '男', '1975-06-18', '历史', '高级教师', '2000-09-01', '13800001007', 'suntao@school.edu', 13000.00),
('T008', '周敏', '女', '1992-12-05', '地理', '二级教师', '2018-09-01', '13800001008', 'zhoumin@school.edu', 7500.00),
('T009', '吴刚', '男', '1983-08-20', '政治', '一级教师', '2009-09-01', '13800001009', 'wugang@school.edu', 10500.00),
('T010', '郑红', '女', '1987-02-14', '体育', '一级教师', '2011-09-01', '13800001010', 'zhenghong@school.edu', 9000.00);

-- 插入课程数据
INSERT INTO courses (course_code, course_name, subject, credit, hours_per_week, description) VALUES
('MATH101', '高等数学', '数学', 4.0, 5, '包含微积分、线性代数基础'),
('CHN101', '语文', '语文', 4.0, 5, '现代文阅读与写作'),
('ENG101', '英语', '英语', 4.0, 5, '听说读写综合训练'),
('PHY101', '物理', '物理', 3.0, 4, '力学、热学、电磁学'),
('CHE101', '化学', '化学', 3.0, 4, '无机化学与有机化学基础'),
('BIO101', '生物', '生物', 2.0, 3, '细胞生物学与遗传学'),
('HIS101', '历史', '历史', 2.0, 2, '中国近现代史'),
('GEO101', '地理', '地理', 2.0, 2, '自然地理与人文地理'),
('POL101', '政治', '政治', 2.0, 2, '思想政治教育'),
('PE101', '体育', '体育', 1.0, 2, '体能训练与球类运动');

-- 插入班级数据
INSERT INTO classes (class_name, grade, head_teacher_id, classroom, student_count) VALUES
('高一(1)班', 10, 1, 'A101', 45),
('高一(2)班', 10, 2, 'A102', 43),
('高一(3)班', 10, 4, 'A103', 44),
('高二(1)班', 11, 3, 'B101', 42),
('高二(2)班', 11, 5, 'B102', 41),
('高二(3)班', 11, 6, 'B103', 40),
('高三(1)班', 12, 7, 'C101', 38),
('高三(2)班', 12, 9, 'C102', 39);

-- 插入学生数据 (每个班级若干学生)
INSERT INTO students (student_no, name, gender, birth_date, grade, class_name, enrollment_date, phone, address) VALUES
-- 高一(1)班
('S2024001', '张小明', '男', '2008-05-12', 10, '高一(1)班', '2024-09-01', '13900001001', '北京市海淀区中关村大街1号'),
('S2024002', '李小红', '女', '2008-03-25', 10, '高一(1)班', '2024-09-01', '13900001002', '北京市朝阳区建国路100号'),
('S2024003', '王小刚', '男', '2008-08-18', 10, '高一(1)班', '2024-09-01', '13900001003', '北京市西城区金融街10号'),
('S2024004', '赵小美', '女', '2008-11-30', 10, '高一(1)班', '2024-09-01', '13900001004', '北京市东城区王府井大街50号'),
('S2024005', '刘小强', '男', '2008-02-14', 10, '高一(1)班', '2024-09-01', '13900001005', '北京市丰台区南三环西路'),
-- 高一(2)班
('S2024006', '陈小芳', '女', '2008-07-08', 10, '高一(2)班', '2024-09-01', '13900001006', '上海市浦东新区陆家嘴'),
('S2024007', '周小伟', '男', '2008-09-22', 10, '高一(2)班', '2024-09-01', '13900001007', '上海市黄浦区南京路'),
('S2024008', '吴小娜', '女', '2008-04-16', 10, '高一(2)班', '2024-09-01', '13900001008', '上海市静安区愚园路'),
('S2024009', '郑小涛', '男', '2008-12-03', 10, '高一(2)班', '2024-09-01', '13900001009', '上海市徐汇区衡山路'),
('S2024010', '孙小丽', '女', '2008-06-28', 10, '高一(2)班', '2024-09-01', '13900001010', '上海市长宁区延安西路'),
-- 高二(1)班
('S2023001', '黄小华', '男', '2007-03-10', 11, '高二(1)班', '2023-09-01', '13900002001', '广州市天河区珠江新城'),
('S2023002', '林小英', '女', '2007-08-25', 11, '高二(1)班', '2023-09-01', '13900002002', '广州市越秀区北京路'),
('S2023003', '何小军', '男', '2007-01-18', 11, '高二(1)班', '2023-09-01', '13900002003', '广州市海珠区江南大道'),
('S2023004', '杨小燕', '女', '2007-11-05', 11, '高二(1)班', '2023-09-01', '13900002004', '广州市荔湾区上下九'),
('S2023005', '许小龙', '男', '2007-06-20', 11, '高二(1)班', '2023-09-01', '13900002005', '广州市白云区机场路'),
-- 高三(1)班
('S2022001', '谢小平', '男', '2006-04-15', 12, '高三(1)班', '2022-09-01', '13900003001', '深圳市南山区科技园'),
('S2022002', '罗小云', '女', '2006-09-28', 12, '高三(1)班', '2022-09-01', '13900003002', '深圳市福田区华强北'),
('S2022003', '邓小峰', '男', '2006-02-08', 12, '高三(1)班', '2022-09-01', '13900003003', '深圳市罗湖区东门'),
('S2022004', '梁小玉', '女', '2006-07-12', 12, '高三(1)班', '2022-09-01', '13900003004', '深圳市宝安区西乡'),
('S2022005', '冯小豪', '男', '2006-12-25', 12, '高三(1)班', '2022-09-01', '13900003005', '深圳市龙岗区布吉');

-- 插入成绩数据
INSERT INTO scores (student_id, course_id, teacher_id, score, exam_type, exam_date, semester) VALUES
-- 张小明的成绩
(1, 1, 1, 92.5, '期中', '2024-11-15', '2024秋季'),
(1, 2, 2, 88.0, '期中', '2024-11-15', '2024秋季'),
(1, 3, 3, 85.5, '期中', '2024-11-15', '2024秋季'),
(1, 4, 4, 90.0, '期中', '2024-11-15', '2024秋季'),
(1, 5, 5, 87.0, '期中', '2024-11-15', '2024秋季'),
-- 李小红的成绩
(2, 1, 1, 78.5, '期中', '2024-11-15', '2024秋季'),
(2, 2, 2, 95.0, '期中', '2024-11-15', '2024秋季'),
(2, 3, 3, 91.0, '期中', '2024-11-15', '2024秋季'),
(2, 4, 4, 72.5, '期中', '2024-11-15', '2024秋季'),
(2, 5, 5, 80.0, '期中', '2024-11-15', '2024秋季'),
-- 王小刚的成绩
(3, 1, 1, 95.0, '期中', '2024-11-15', '2024秋季'),
(3, 2, 2, 82.0, '期中', '2024-11-15', '2024秋季'),
(3, 3, 3, 78.5, '期中', '2024-11-15', '2024秋季'),
(3, 4, 4, 96.0, '期中', '2024-11-15', '2024秋季'),
(3, 5, 5, 93.5, '期中', '2024-11-15', '2024秋季'),
-- 黄小华(高二)的成绩
(11, 1, 1, 88.0, '期中', '2024-11-15', '2024秋季'),
(11, 2, 2, 90.5, '期中', '2024-11-15', '2024秋季'),
(11, 3, 3, 86.0, '期中', '2024-11-15', '2024秋季'),
(11, 4, 4, 91.5, '期中', '2024-11-15', '2024秋季'),
(11, 5, 5, 89.0, '期中', '2024-11-15', '2024秋季'),
-- 谢小平(高三)的成绩
(16, 1, 1, 94.0, '期中', '2024-11-15', '2024秋季'),
(16, 2, 2, 92.0, '期中', '2024-11-15', '2024秋季'),
(16, 3, 3, 89.5, '期中', '2024-11-15', '2024秋季'),
(16, 4, 4, 95.5, '期中', '2024-11-15', '2024秋季'),
(16, 5, 5, 91.0, '期中', '2024-11-15', '2024秋季'),
-- 更多历史成绩
(1, 1, 1, 89.0, '月考', '2024-10-15', '2024秋季'),
(1, 2, 2, 85.5, '月考', '2024-10-15', '2024秋季'),
(2, 1, 1, 75.0, '月考', '2024-10-15', '2024秋季'),
(2, 2, 2, 92.5, '月考', '2024-10-15', '2024秋季'),
(3, 1, 1, 93.0, '月考', '2024-10-15', '2024秋季'),
(3, 4, 4, 94.5, '月考', '2024-10-15', '2024秋季');

-- 插入课程安排
INSERT INTO schedules (class_id, course_id, teacher_id, weekday, period, semester) VALUES
-- 高一(1)班课程安排
(1, 1, 1, 1, 1, '2024秋季'), -- 周一第1节 数学
(1, 2, 2, 1, 2, '2024秋季'), -- 周一第2节 语文
(1, 3, 3, 1, 3, '2024秋季'), -- 周一第3节 英语
(1, 4, 4, 2, 1, '2024秋季'), -- 周二第1节 物理
(1, 5, 5, 2, 2, '2024秋季'), -- 周二第2节 化学
(1, 6, 6, 3, 1, '2024秋季'), -- 周三第1节 生物
(1, 7, 7, 3, 2, '2024秋季'), -- 周三第2节 历史
(1, 8, 8, 4, 1, '2024秋季'), -- 周四第1节 地理
(1, 9, 9, 4, 2, '2024秋季'), -- 周四第2节 政治
(1, 10, 10, 5, 5, '2024秋季'); -- 周五第5节 体育

-- 创建一些有用的视图
CREATE VIEW student_score_summary AS
SELECT 
    s.student_no,
    s.name AS student_name,
    s.class_name,
    c.course_name,
    sc.score,
    sc.exam_type,
    sc.exam_date
FROM students s
JOIN scores sc ON s.id = sc.student_id
JOIN courses c ON sc.course_id = c.id
ORDER BY s.student_no, c.course_name;

CREATE VIEW class_average_scores AS
SELECT 
    s.class_name,
    c.course_name,
    sc.exam_type,
    ROUND(AVG(sc.score), 2) AS avg_score,
    MAX(sc.score) AS max_score,
    MIN(sc.score) AS min_score,
    COUNT(*) AS student_count
FROM students s
JOIN scores sc ON s.id = sc.student_id
JOIN courses c ON sc.course_id = c.id
GROUP BY s.class_name, c.course_name, sc.exam_type
ORDER BY s.class_name, c.course_name;

CREATE VIEW teacher_workload AS
SELECT 
    t.teacher_no,
    t.name AS teacher_name,
    t.subject,
    COUNT(DISTINCT sch.class_id) AS class_count,
    SUM(c.hours_per_week) AS total_hours_per_week
FROM teachers t
LEFT JOIN schedules sch ON t.id = sch.teacher_id
LEFT JOIN courses c ON sch.course_id = c.id
GROUP BY t.id, t.teacher_no, t.name, t.subject
ORDER BY total_hours_per_week DESC;

-- 打印数据统计
DO $$
BEGIN
    RAISE NOTICE '========== 数据库初始化完成 ==========';
    RAISE NOTICE '教师数量: %', (SELECT COUNT(*) FROM teachers);
    RAISE NOTICE '学生数量: %', (SELECT COUNT(*) FROM students);
    RAISE NOTICE '课程数量: %', (SELECT COUNT(*) FROM courses);
    RAISE NOTICE '班级数量: %', (SELECT COUNT(*) FROM classes);
    RAISE NOTICE '成绩记录: %', (SELECT COUNT(*) FROM scores);
    RAISE NOTICE '课程安排: %', (SELECT COUNT(*) FROM schedules);
END $$;

