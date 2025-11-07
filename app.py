from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from datetime import datetime
import sys
import socket
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'project-tracker-secret-key'


class ProjectDataManager:
    """项目数据管理类"""

    def __init__(self, data_file='data/projects.xlsx'):
        self.data_file = data_file
        self.cache = None
        self.last_modified = None

    def load_data(self):
        """加载Excel数据"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.data_file):
                print(f"数据文件不存在: {self.data_file}")
                return self._create_sample_data()

            # 检查文件是否被修改过
            current_modified = os.path.getmtime(self.data_file)
            if self.cache is not None and current_modified == self.last_modified:
                return self.cache

            print("正在加载Excel数据...")

            # 读取Excel文件
            df = pd.read_excel(self.data_file)

            # 数据清洗和处理
            df = self._clean_data(df)

            # 缓存数据
            self.cache = self._process_data(df)
            self.last_modified = current_modified

            print(f"数据加载成功，共 {len(df)} 条记录")
            return self.cache

        except Exception as e:
            print(f"数据加载错误: {e}")
            return self._create_sample_data()

    def _clean_data(self, df):
        """数据清洗"""
        # 填充空值
        df = df.fillna('')

        # 确保列名一致性
        expected_columns = ['序号', '项目名称', '项目性质', '责任单位', '分管区领导',
                            '预计开工时间', '项目总投资', '项目进展情况', '开工情况', '纳税情况', '备注']

        for col in expected_columns:
            if col not in df.columns:
                df[col] = ''

        # 数据类型转换
        if '项目总投资' in df.columns:
            df['项目总投资'] = pd.to_numeric(df['项目总投资'], errors='coerce').fillna(0)

        # 处理预计开工时间 - 将Excel日期序列号转换为日期字符串
        if '预计开工时间' in df.columns:
            df['预计开工时间'] = df['预计开工时间'].apply(self._convert_excel_date)

        return df

    def _convert_excel_date(self, excel_date):
        """将Excel日期序列号转换为可读的日期字符串"""
        try:
            # 如果是数字（Excel日期序列号）
            if isinstance(excel_date, (int, float)):
                # Excel日期序列号是从1900-01-01开始的天数
                base_date = datetime(1900, 1, 1)
                result_date = base_date + pd.Timedelta(days=excel_date - 2)  # Excel有个1900闰年bug，所以减2
                return result_date.strftime('%Y年%m月')
            # 如果是字符串，直接返回
            elif isinstance(excel_date, str):
                return excel_date
            else:
                return str(excel_date)
        except:
            return str(excel_date)

    def _process_data(self, df):
        """处理数据并分组"""
        # 按开工状态分组
        started_projects = []
        not_started_projects = []

        # 统计已纳统项目
        nashuitong_projects = []

        for _, project in df.iterrows():
            project_dict = project.to_dict()
            if project_dict.get('开工情况') == '已开工':
                started_projects.append(project_dict)
            else:
                not_started_projects.append(project_dict)

            # 统计纳税情况为"已纳统"的项目
            if project_dict.get('纳税情况') == '已纳统':
                nashuitong_projects.append(project_dict)

        status_groups = {
            '已开工': started_projects,
            '未开工': not_started_projects
        }

        # 按分管领导分组
        leader_groups = {}
        for _, project in df.iterrows():
            leader = project.get('分管区领导')
            if leader and str(leader).strip():
                if leader not in leader_groups:
                    leader_groups[leader] = []
                leader_groups[leader].append(project.to_dict())

        return {
            'all_data': df.to_dict('records'),
            'status_groups': status_groups,
            'leader_groups': leader_groups,
            'total_count': len(df),
            'started_count': len(started_projects),
            'nashuitong_count': len(nashuitong_projects),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _create_sample_data(self):
        """创建示例数据（当Excel文件不存在时）"""
        print("创建示例数据...")
        sample_data = [
            {
                '序号': 1,
                '项目名称': '陈梅湾安置型商品房P（2024）083、098号地块',
                '项目性质': '新开工',
                '责任单位': '区住更局',
                '分管区领导': '陈聪',
                '预计开工时间': '2025年3月',
                '项目总投资': 160000,
                '项目进展情况': '备案项目（中建二局）。',
                '开工情况': '已开工',
                '纳税情况': '已纳统',
                '备注': ''
            },
            {
                '序号': 2,
                '项目名称': '木兰农创中心',
                '项目性质': '续建',
                '责任单位': '盘龙水投公司',
                '分管区领导': '阮诗军',
                '预计开工时间': '2024年6月',
                '项目总投资': 150000,
                '项目进展情况': '2024年4月2日已中标（武汉建工基础设施工程有限公司，武汉市政工程设计研究院有限责任公司，中信建筑设计研究总院有限公司）。',
                '开工情况': '已开工',
                '纳税情况': '已纳统',
                '备注': ''
            },
            {
                '序号': 3,
                '项目名称': 'S115孝昌京珠李集互通至黄陂区改扩建',
                '项目性质': '续建',
                '责任单位': '区交通运输局',
                '分管区领导': '彭斌祥',
                '预计开工时间': '2023年6月',
                '项目总投资': 105700,
                '项目进展情况': '7月21日申报《武汉环境建设集团有限责任公司》。',
                '开工情况': '已开工',
                '纳税情况': '已纳统',
                '备注': ''
            }
        ]

        df = pd.DataFrame(sample_data)
        return self._process_data(df)

    def search_projects(self, query, data=None):
        """搜索项目"""
        if data is None:
            data = self.load_data()

        if not query:
            return data['all_data']

        query = query.lower().strip()
        filtered_projects = []

        for project in data['all_data']:
            # 搜索项目名称、分管领导、责任单位、项目进展
            if (query in str(project.get('项目名称', '')).lower() or
                    query in str(project.get('分管区领导', '')).lower() or
                    query in str(project.get('责任单位', '')).lower() or
                    query in str(project.get('项目进展情况', '')).lower() or
                    query in str(project.get('项目性质', '')).lower()):
                filtered_projects.append(project)

        return filtered_projects


# 初始化数据管理器
data_manager = ProjectDataManager()


def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个socket连接到一个公共DNS服务器
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def generate_qr_code(url):
    """生成二维码"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"生成二维码失败: {e}")
        return None


@app.route('/')
def index():
    """主页面 - 显示所有项目"""
    data = data_manager.load_data()

    # 获取访问信息
    local_ip = get_local_ip()
    access_url = f"http://{local_ip}:5002"
    qr_code = generate_qr_code(access_url)

    return render_template('index.html',
                           projects=data['all_data'],
                           total_count=data['total_count'],
                           started_count=data['started_count'],
                           nashuitong_count=data['nashuitong_count'],
                           last_updated=data['last_updated'],
                           local_ip=local_ip,
                           access_url=access_url,
                           qr_code=qr_code)


@app.route('/status/<status_type>')
def projects_by_status(status_type):
    """按状态查看项目"""
    data = data_manager.load_data()

    if status_type == 'started':
        projects = data['status_groups']['已开工']
        title = '已开工项目'
    elif status_type == 'not-started':
        projects = data['status_groups']['未开工']
        title = '未开工项目'
    else:
        projects = data['all_data']
        title = '所有项目'

    # 计算已纳统数量
    nashuitong_count = len([p for p in projects if p.get('纳税情况') == '已纳统'])

    return render_template('index.html',
                           projects=projects,
                           total_count=len(projects),
                           started_count=len([p for p in projects if p.get('开工情况') == '已开工']),
                           nashuitong_count=nashuitong_count,
                           page_title=title,
                           last_updated=data['last_updated'])


@app.route('/leader/<leader_name>')
def projects_by_leader(leader_name):
    """按分管领导查看项目"""
    data = data_manager.load_data()

    if leader_name in data['leader_groups']:
        projects = data['leader_groups'][leader_name]
        title = f'{leader_name} 分管项目'
    else:
        projects = []
        title = '未找到相关项目'

    # 计算已纳统数量
    nashuitong_count = len([p for p in projects if p.get('纳税情况') == '已纳统'])

    return render_template('index.html',
                           projects=projects,
                           total_count=len(projects),
                           started_count=len([p for p in projects if p.get('开工情况') == '已开工']),
                           nashuitong_count=nashuitong_count,
                           page_title=title,
                           last_updated=data['last_updated'])


@app.route('/search')
def search_projects():
    """搜索项目"""
    query = request.args.get('q', '').strip()
    data = data_manager.load_data()

    filtered_projects = data_manager.search_projects(query, data)

    # 计算已纳统数量
    nashuitong_count = len([p for p in filtered_projects if p.get('纳税情况') == '已纳统'])

    return render_template('index.html',
                           projects=filtered_projects,
                           total_count=len(filtered_projects),
                           started_count=len([p for p in filtered_projects if p.get('开工情况') == '已开工']),
                           nashuitong_count=nashuitong_count,
                           search_query=query,
                           last_updated=data['last_updated'])


@app.route('/api/projects')
def api_projects():
    """API接口 - 返回JSON格式的项目数据"""
    data = data_manager.load_data()
    return jsonify({
        'success': True,
        'data': data['all_data'],
        'total_count': data['total_count'],
        'started_count': data['started_count'],
        'nashuitong_count': data['nashuitong_count'],
        'last_updated': data['last_updated']
    })


def init_directories():
    """初始化必要的目录结构"""
    directories = ['templates', 'static', 'data']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"创建目录: {directory}")


def check_dependencies():
    """检查必要的依赖包"""
    required_packages = {
        'openpyxl': 'openpyxl',
        'pandas': 'pandas',
        'flask': 'flask',
        'qrcode': 'qrcode[pil]',
        'PIL': 'Pillow'
    }

    all_installed = True
    for package, install_name in required_packages.items():
        try:
            if package == 'PIL':
                from PIL import Image
            else:
                __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装，请运行: pip install {install_name}")
            all_installed = False

    return all_installed


def create_template_file():
    """创建模板文件"""
    template_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>项目进度跟踪系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 10px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }
        .header h1 {
            font-size: 1.5rem;
            margin-bottom: 15px;
        }
        .stats {
            display: flex;
            gap: 15px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.2);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            flex: 1;
        }
        .stat-card.started {
            background: rgba(76, 175, 80, 0.3);
        }
        .stat-card.nashuitong {
            background: rgba(255, 152, 0, 0.3);
        }
        .stat-number {
            display: block;
            font-size: 2rem;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        .search-box {
            margin-bottom: 15px;
        }
        .search-box input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            font-size: 1rem;
            outline: none;
        }
        .search-box input:focus {
            border-color: #667eea;
        }
        .project-card {
            background: white;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
            width: 100%;
        }
        .project-card.started {
            border-left-color: #4CAF50;
        }
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .project-name {
            flex: 1;
            font-size: 1.1rem;
            color: #2c3e50;
            margin-right: 10px;
        }
        .status-badges {
            display: flex;
            gap: 5px;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            white-space: nowrap;
        }
        .status-badge.started {
            background: #4CAF50;
            color: white;
        }
        .status-badge.not-started {
            background: #ff9800;
            color: white;
        }
        .status-badge.nashuitong {
            background: #2196F3;
            color: white;
        }
        .detail-item {
            margin-bottom: 8px;
            display: flex;
        }
        .detail-item strong {
            color: #666;
            min-width: 80px;
        }
        .leader {
            color: #e74c3c;
            font-weight: bold;
        }
        .unit {
            color: #3498db;
            font-weight: bold;
        }
        .progress-text {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            margin-top: 5px;
            border-left: 3px solid #667eea;
        }
        .project-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }
        .meta-item {
            font-size: 0.8rem;
            color: #666;
            background: #f8f9fa;
            padding: 3px 6px;
            border-radius: 4px;
        }
        .last-updated {
            text-align: center;
            color: #666;
            font-size: 0.8rem;
            margin-top: 10px;
        }
        .mobile-access {
            background: white;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .mobile-access h3 {
            margin-bottom: 10px;
            color: #2c3e50;
        }
        .mobile-access p {
            margin-bottom: 10px;
            color: #666;
        }
        .qr-code {
            max-width: 200px;
            margin: 0 auto 10px;
        }
        .qr-code img {
            width: 100%;
            height: auto;
        }
        .access-url {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            word-break: break-all;
        }
        @media (max-width: 768px) {
            .stats {
                flex-direction: column;
                gap: 10px;
            }
            .project-header {
                flex-direction: column;
                align-items: flex-start;
            }
            .status-badges {
                margin-top: 8px;
            }
            .detail-item {
                flex-direction: column;
            }
            .detail-item strong {
                min-width: auto;
                margin-bottom: 2px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部统计信息 -->
        <div class="header">
            <h1>📊 项目进度跟踪</h1>
            <div class="stats">
                <div class="stat-card">
                    <span class="stat-number">{{ total_count }}</span>
                    <span class="stat-label">总项目数</span>
                </div>
                <div class="stat-card started">
                    <span class="stat-number">{{ started_count }}</span>
                    <span class="stat-label">已开工</span>
                </div>
                <div class="stat-card nashuitong">
                    <span class="stat-number">{{ nashuitong_count }}</span>
                    <span class="stat-label">已纳统</span>
                </div>
            </div>
        </div>

        <!-- 手机访问提示 -->
        {% if local_ip and local_ip != '127.0.0.1' %}
        <div class="mobile-access">
            <h3>📱 手机访问</h3>
            <p>使用手机扫描二维码或输入下方地址访问</p>
            {% if qr_code %}
            <div class="qr-code">
                <img src="{{ qr_code }}" alt="扫描二维码访问">
            </div>
            {% endif %}
            <div class="access-url">{{ access_url }}</div>
            <p style="margin-top: 10px; font-size: 0.8rem; color: #666;">
                确保手机和电脑连接同一WiFi网络
            </p>
        </div>
        {% endif %}

        <!-- 搜索框 -->
        <div class="search-box">
            <form action="/search" method="get">
                <input type="text" name="q" placeholder="搜索项目名称、分管领导、责任单位..." 
                       value="{{ search_query or '' }}">
            </form>
        </div>

        <!-- 页面标题 -->
        {% if page_title %}
        <h2 style="margin-bottom: 15px;">{{ page_title }}</h2>
        {% endif %}

        <!-- 项目列表 -->
        <div class="projects-list">
            {% for project in projects %}
            <div class="project-card {% if project.开工情况 == '已开工' %}started{% endif %}">
                <div class="project-header">
                    <h3 class="project-name">{{ project.项目名称 }}</h3>
                    <div class="status-badges">
                        <span class="status-badge {% if project.开工情况 == '已开工' %}started{% else %}not-started{% endif %}">
                            {{ project.开工情况 }}
                        </span>
                        {% if project.纳税情况 == '已纳统' %}
                        <span class="status-badge nashuitong">
                            {{ project.纳税情况 }}
                        </span>
                        {% endif %}
                    </div>
                </div>

                <div class="project-details">
                    <div class="detail-item">
                        <strong>分管领导:</strong>
                        <span class="leader">{{ project.分管区领导 }}</span>
                    </div>

                    <div class="detail-item">
                        <strong>责任单位:</strong>
                        <span class="unit">{{ project.责任单位 }}</span>
                    </div>

                    <div class="detail-item">
                        <strong>预计开工:</strong>
                        <span>{{ project.预计开工时间 }}</span>
                    </div>

                    <div class="detail-item">
                        <strong>项目进展:</strong>
                        <div class="progress-text">{{ project.项目进展情况 }}</div>
                    </div>

                    <div class="project-meta">
                        <span class="meta-item">💰 {{ project.项目总投资 }}万元</span>
                        <span class="meta-item">🏷️ {{ project.项目性质 }}</span>
                        {% if project.备注 %}
                        <span class="meta-item">📝 {{ project.备注 }}</span>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        {% if not projects %}
        <div style="text-align: center; padding: 40px; color: #666;">
            <p>暂无项目数据</p>
        </div>
        {% endif %}

        <div class="last-updated">
            最后更新: {{ last_updated }}
        </div>
    </div>
</body>
</html>'''

    template_path = 'templates/index.html'
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template_content)
    print(f"已创建模板文件: {template_path}")


if __name__ == '__main__':
    # 检查依赖
    if not check_dependencies():
        print("请安装缺少的依赖包后再运行程序")
        sys.exit(1)

    # 初始化目录
    init_directories()

    # 创建模板文件
    create_template_file()

    # 预加载数据
    print("预加载数据...")
    data_manager.load_data()

    # 获取本机IP
    local_ip = get_local_ip()
    access_url = f"http://{local_ip}:5002"

    # 生成二维码
    qr_code = generate_qr_code(access_url)
    if qr_code:
        print("✓ 已生成手机访问二维码")

    # 启动Flask应用
    print("\n" + "=" * 50)
    print("项目跟踪系统启动成功!")
    print(f"本地访问: http://localhost:5005")
    print(f"手机访问: {access_url}")

    if local_ip != "127.0.0.1":
        print("✓ 已检测到局域网IP，手机可以访问")
        if qr_code:
            print("✓ 已生成二维码，手机扫描即可访问")
    else:
        print("⚠ 无法获取局域网IP，请检查网络连接")

    print("=" * 50 + "\n")

    # 允许局域网内其他设备访问
    app.run(host='0.0.0.0', port=5005, debug=True)  # 生产环境建议将debug设为False