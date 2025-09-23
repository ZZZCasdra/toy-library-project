from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask import Flask, render_template, request, redirect,flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
from flask import abort
from sqlalchemy import or_
from datetime import datetime
import os
basedir = os.path.abspath(os.path.dirname(__file__))
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-very-secret-key-123'

#uploads子目录，专门存上传的图片
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 限制最大 5 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file_storage):

    #保存上传的图片，返回可用于 url_for('static', filename=...) 的相对路径

    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    # 使用安全文件名 + 随机前缀避免重名
    safe_name = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(save_path)

    # 存数据库时只存相对 static 的路径：
    return f"uploads/{unique_name}"


#日期解析辅助函数
from datetime import datetime

def parse_date(s: str):
    """将多种常见格式的字符串解析为 date 对象；空值返回 None。"""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # 走到这里说明都没解析成功
    raise ValueError("Invalid date format. Please use a valid date.")

AGE_CODES = ["A", "B", "C", "D", "E"]
FREQ_CODES = ["A", "B", "C", "D", "E"]
#年龄映射字典
AGE_RANGE_MAPPING = {
    "A": "Birth to 6 months",
    "B": "6 months to 18 months",
    "C": "18 months to 3 years",
    "D": "3 years to 5 years",
    "E": "5 years plus"
}
# 反向映射
AGE_LABEL_TO_CODE = {v: k for k, v in AGE_RANGE_MAPPING.items()}

DEVELOPMENTAL_SKILLS = [
    "Fine Motor Skills", "Gross Motor Skills", "Hand-Eye Coordination", "Problem Solving",
    "Language & Communication", "Social Skills", "Creativity & Imagination",
    "Emotional Development", "Cognitive Development", "Sensory Exploration",
    "STEM Skills", "Musical Awareness", "Cause and Effect Understanding",
    "Independent Play", "Turn-Taking & Cooperation"
]

# 配置 SQLite 数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'borrow_records.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 定义玩具数据（全局变量）
toy_list = [
    {
        "id": 1,
        "name": "木质积木",
        "image": "images/blocks.jpeg",
        "detail": "这款玩具是一套可供儿童搭建的积木。",
        "available": True
    },
    {
        "id": 2,
        "name": "毛绒熊",
        "image": "images/bear.jpg",
        "detail": "这款动物农是一只毛绒玩具熊。",
        "available": False
    },
    {
        "id": 3,
        "name": "拼图游戏",
        "image": "images/puzzle.jpeg",
        "detail": "这款动物农是一块拼图板。",
        "available": True
    }
]

#Toy
class Toy(db.Model):
    toy_id = db.Column(db.String(10), primary_key=True)  # 玩具ID
    name = db.Column(db.String(100), nullable=False)  # 玩具名称
    brand = db.Column(db.String(100)) # 玩具品牌
    age_range = db.Column(db.String(10), nullable=False)  # 适龄范围
    toy_type = db.Column(db.String(100), nullable=False)  # 游戏类型
    keywords = db.Column(db.String(200))  # 关键词（多个词以逗号分隔）
    image = db.Column(db.String(200))  # 图片路径
    status = db.Column(db.String(20), nullable=False, default='可借')  # 借用状态
    rating = db.Column(db.Float, default=0.0)  # 玩具评分（默认0.0）

    date_loaned_out = db.Column(db.Date) # 出租日期
    last_checked = db.Column(db.Date) # 最后检查日期
    date_in_stock = db.Column(db.Date) # 入库日期
    loan_frequency = db.Column(db.String(1)) # 出租频率
    value = db.Column(db.Float) # 玩具价格
# 定义数据库模型
class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 外键关联到用户
    toy_id = db.Column(db.Integer, nullable=False)
    toy_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(10), nullable=False)
    returned = db.Column(db.Boolean, default=False)

from flask_login import UserMixin
#db.Column：定义一列
#Integer: Int; String: 字符串; nullable: 是否允许为空; unique:表示不能重复(例如一个邮箱只能注册一次); default:设置字段的默认值
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" or "guest"

#Rating模型
class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toy_id = db.Column(db.String(10), db.ForeignKey('toy.toy_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 首页
@app.route("/")#这是一个装饰器(decorator)，用户访问/路径时，执行home()函数
def home():
    featured_toys = Toy.query.order_by(Toy.rating.desc()).limit(3).all()
    return render_template("home.html", featured_toys=featured_toys)

# 玩具列表页
# @app.route("/toys")
# def toys_page():
#     return render_template("toys.html", toys=toy_list)
@app.route("/toys")
def toys():
    #toy_list = Toy.query.all()
    selected_type = request.args.get('type')
    #selected_age = request.args.get('age')
    selected_age_label = request.args.get('age')
    selected_age_code = AGE_LABEL_TO_CODE.get(selected_age_label)
    only_available = request.args.get('only_available') == 'on'
    selected_skill = request.args.get('skill')

    query = Toy.query
    if selected_type:
        query = query.filter_by(toy_type=selected_type)
    if selected_age_code:
        query = query.filter_by(age_range=selected_age_code)
    if only_available:
        query = query.filter_by(status='available')
    if selected_skill:
        query = query.filter(Toy.keywords.ilike(f"%{selected_skill}%"))

    toy_list = query.all()

    toy_types = [
        "Game", "Puzzle", "Soft Toy", "Figures", "Book", "Card game", "Multiple Toy Set",
        "Baby Toy", "Educational Toy", "Parent Child Play", "Time Telling Skills",
        "Learning Puzzle", "TV Puzzle", "Baby Puzzle", "Disney Puzzle", "Educational Game",
        "Board Game", "Action Figure", "Group Activity", "Fancy Dress", "Dressing Up",
        "Indoor Physical Play", "Outdoor Physical Play", "Construction", "Building Bricks",
        "Push Along", "Small World", "Musical", "Pretend Play", "Role Play", "Dolls House",
        "Train Set", "Dolls", "Dolls Pram", "Dolls Cot", "Tea Set"
    ]
    age_ranges = list(AGE_RANGE_MAPPING.values())

    developmental_skills = [
        "Fine Motor Skills", "Gross Motor Skills", "Hand-Eye Coordination", "Problem Solving",
        "Language & Communication", "Social Skills", "Creativity & Imagination",
        "Emotional Development", "Cognitive Development", "Sensory Exploration",
        "STEM Skills", "Musical Awareness", "Cause and Effect Understanding",
        "Independent Play", "Turn-Taking & Cooperation"
    ]

    #toy_type = request.args.get("type")

    # toy_types = db.session.query(Toy.toy_type).distinct().all()  # 获取所有不重复的toy_type
    # toy_types = [t[0] for t in toy_types]  # 解包成纯字符串列表
    return render_template("toys.html", toys=toy_list,
                           toy_types=toy_types,
                           age_ranges=age_ranges,
                           selected_type=selected_type,
                           selected_age=selected_age_label,
                           only_available=only_available,
                           developmental_skills=developmental_skills,
                           selected_skill=selected_skill)
    #return render_template("toys.html", toys=toy_list)



# 玩具详情页
# @app.route("/toy/<int:toy_id>")
# def toy_detail(toy_id):
#     toy = next((t for t in toy_list if t["id"] == toy_id), None)
#     if toy:
#         return render_template("toy_detail.html", toy=toy)
#     else:
#         return "玩具不存在", 404
@app.route("/toy/<string:toy_id>")
def toy_detail(toy_id):
    toy = Toy.query.get_or_404(toy_id)
    return render_template("toy_detail.html", toy=toy)


# 借用表单页
@app.route("/borrow/<string:toy_id>", methods=["GET", "POST"])
@login_required
def borrow(toy_id):
    #toy = next((t for t in toy_list if t["id"] == toy_id), None)
    #if not toy:
    #    return "Toy not found", 404
    toy = Toy.query.get_or_404(toy_id)

    if request.method == "POST":
        # 获取表单数据
        first = request.form.get("firstname")
        last = request.form.get("lastname")
        email = request.form.get("email")
        phone = request.form.get("phone")
        duration = request.form.get("duration")

        # 保存记录
        record = BorrowRecord(
            toy_id=toy.toy_id,
            toy_name=toy.name,
            first_name=first,
            last_name=last,
            email=email,
            phone=phone,
            duration=duration,
            user_id=current_user.id
        )
        db.session.add(record)

        toy.status = 'borrowed'#借用状态更新
        db.session.commit()

        flash("Borrow request submitted successfully.", "success")
        return render_template("borrow_success.html", toy=toy)

    return render_template("borrow.html", toy=toy)

#我的借用
@app.route("/my-borrows")
@login_required
def my_borrows():
    if current_user.role != 'guest':
        return "Only guest users can access this page", 403

    # 获取当前用户的所有借用记录
    records = BorrowRecord.query.filter_by(user_id=current_user.id).all()
    return render_template("my_borrows.html", records=records)

#评分
@app.route("/return/<int:record_id>", methods=["GET", "POST"])
@login_required
def return_and_rate(record_id):
    record = BorrowRecord.query.get_or_404(record_id)

    if record.user_id != current_user.id:
        return "You can only return your own borrowed toys", 403

    toy = Toy.query.filter_by(toy_id=record.toy_id).first()

    if request.method == "POST":
        rating_value = int(request.form.get("rating"))
        if not (1 <= rating_value <= 5):
            return "Invalid rating value", 400

        # 保存评分
        new_rating = Rating(user_id=current_user.id, toy_id=toy.toy_id, score=rating_value)
        db.session.add(new_rating)

        # 更新玩具平均评分
        all_ratings = Rating.query.filter_by(toy_id=toy.toy_id).all()
        if all_ratings:
            avg_rating = sum(r.score for r in all_ratings) / len(all_ratings)
            toy.rating = round(avg_rating, 2)

        # 标记借用记录为已归还
        record.returned = True

        # 更新玩具状态为可借
        toy.status = "available"

        db.session.commit()

        return render_template("return_success.html", toy=toy, rating=rating_value)

    return render_template("return_and_rate.html", toy=toy, record=record)


# 联系页
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        # 这里先不做存储/发送，只做最基本的非空校验与提示
        if not name or not email or not message:
            flash("Please fill in your name, email, and message.", "danger")
            return redirect(url_for("contact"))

        flash("Thanks! Your message has been sent.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        role = request.form.get("role")

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("The username or email address has already been registered", "danger")
            return redirect(url_for("register"))
        #User.query:对User表进行查询，类似SELECT * FROM User
        #.filter(xxx):设置查询的过滤条件
        #.first:如果找到了匹配的记录就返回第一条结果，没找到就返回None
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")#密码加密
        user = User(username=username, email=email, phone=phone, password=hashed_pw, role=role)#创建一个数据库表user，包含以下信息
        db.session.add(user)#准备写入数据库
        db.session.commit()#真正把数据保存到数据库

        login_user(user)  # 自动登录
        flash("Registration successful. You have been automatically logged in", "success")
        return redirect(url_for("home"))

    return render_template("register.html")#这里就是"GET"方法

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful","success")
            next_url = request.args.get("next")
            if next_url:
                parsed = urlparse(next_url)
                if parsed.netloc == "" and next_url.startswith("/"):
                    return redirect(next_url)
            return redirect(url_for("home"))
        else:
            flash("Username or password is incorrect", "danger")
            return "Username or password is incorrect"

    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return "Successfully logged out"

# @app.route("/admin")
# @login_required
# def admin_dashboard():
#     if current_user.role != 'admin':
#         abort(403)
#     return render_template("admin_dashboard.html")

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return "Only administrator can use the page", 403

    toys = Toy.query.all()
    return render_template("admin_dashboard.html", toys=toys)

@app.route("/admin/add-toy", methods=["GET", "POST"])
@login_required
def add_toy():
    if current_user.role != 'admin':
        return "Only administrator can add toys", 403


    toy_types = [
        "Game", "Puzzle", "Soft Toy", "Figures", "Book", "Card game", "Multiple Toy Set",
        "Baby Toy", "Educational Toy", "Parent Child Play", "Time Telling Skills",
        "Learning Puzzle", "TV Puzzle", "Baby Puzzle", "Disney Puzzle", "Educational Game",
        "Board Game", "Action Figure", "Group Activity", "Fancy Dress", "Dressing Up",
        "Indoor Physical Play", "Outdoor Physical Play", "Construction", "Building Bricks",
        "Push Along", "Small World", "Musical", "Pretend Play", "Role Play", "Dolls House",
        "Train Set", "Dolls", "Dolls Pram", "Dolls Cot", "Tea Set"
    ]

    if request.method == "POST":
        toy_id = request.form.get("toy_id")
        existing_toy = Toy.query.filter_by(toy_id=toy_id).first()
        if existing_toy:
            flash("Toy ID already exists. Please use a different ID.", "danger")
            return render_template("add_toy.html", toy_types=toy_types, dev_skills=DEVELOPMENTAL_SKILLS)

        name = request.form.get("name")
        age_range = request.form.get("age_range")
        toy_type = request.form.get("toy_type")
        #keywords = request.form.get("keywords")

        dev_skill = request.form.get("dev_skill")  # 从下拉菜单获取发展技能
        safety = request.form.get("safety")  # 从下拉菜单获取安全性

        extra_keyword1 = request.form.get("extra_keyword1")
        extra_keyword2 = request.form.get("extra_keyword2")
        extra_keyword3 = request.form.get("extra_keyword3")

        # 合并所有关键词（过滤掉空值）
        keyword_list = [dev_skill, safety, extra_keyword1, extra_keyword2, extra_keyword3]
        keyword_list = [k for k in keyword_list if k]
        keywords = ", ".join(keyword_list)

        #image = request.form.get("image")
        file = request.files.get("image_file")
        saved_rel_path = save_image(file)  # 可能为 None（未选择或类型不允许）

        status = request.form.get("status")
        #rating = float(request.form.get("rating"))
        rating = 0.0
        brand = request.form.get("brand")
        # date_loaned_out = request.form.get("date_loaned_out")
        # last_checked = request.form.get("last_checked")
        # date_in_stock = request.form.get("date_in_stock")
        # date_loaned_out = datetime.strptime(request.form.get("date_loaned_out"), "%Y/%m/%d").date()
        # last_checked = datetime.strptime(request.form.get("last_checked"), "%Y/%m/%d").date()
        # date_in_stock = datetime.strptime(request.form.get("date_in_stock"), "%Y/%m/%d").date()
        date_loaned_out = parse_date(request.form.get("date_loaned_out"))
        last_checked = parse_date(request.form.get("last_checked"))
        date_in_stock = parse_date(request.form.get("date_in_stock"))

        loan_frequency = request.form.get("loan_frequency")
        value = float(request.form.get("value"))

        toy = Toy(
            toy_id=toy_id,
            name=name,
            age_range=age_range,
            toy_type=toy_type,
            keywords=keywords,
            #image=image,
            image=saved_rel_path or "",
            status=status,
            rating=rating,
            brand=brand,
            date_loaned_out=date_loaned_out,
            last_checked=last_checked,
            date_in_stock=date_in_stock,
            loan_frequency=loan_frequency,
            value=value
        )
        db.session.add(toy)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template("add_toy.html", toy_types=toy_types, dev_skills=DEVELOPMENTAL_SKILLS, age_codes=AGE_CODES,
    freq_codes=FREQ_CODES )

# @app.route("/admin/edit/<string:toy_id>", methods=["GET", "POST"])
# def edit_toy(toy_id):
#     # 编辑占位符
#     return f"编辑玩具 {toy_id} 的页面开发中……"
#编辑
@app.route("/admin/edit/<string:toy_id>", methods=["GET", "POST"])
@login_required
def edit_toy(toy_id):
    if current_user.role != 'admin':
        return "Only administrator can edit toys", 403

    toy = Toy.query.get_or_404(toy_id)

    AGE_CODES = ["A", "B", "C", "D", "E"]
    freq_codes = ["A", "B", "C", "D", "E"]
    toy_types = [
        "Game", "Puzzle", "Soft Toy", "Figures", "Book", "Card game", "Multiple Toy Set",
        "Baby Toy", "Educational Toy", "Parent Child Play", "Time Telling Skills",
        "Learning Puzzle", "TV Puzzle", "Baby Puzzle", "Disney Puzzle", "Educational Game",
        "Board Game", "Action Figure", "Group Activity", "Fancy Dress", "Dressing Up",
        "Indoor Physical Play", "Outdoor Physical Play", "Construction", "Building Bricks",
        "Push Along", "Small World", "Musical", "Pretend Play", "Role Play", "Dolls House",
        "Train Set", "Dolls", "Dolls Pram", "Dolls Cot", "Tea Set"
    ]

    if request.method == "POST":
        toy.name = request.form.get("name")
        toy.brand = request.form.get("brand")
        toy.age_range = request.form.get("age_range")
        toy.toy_type = request.form.get("toy_type")
        toy.keywords = request.form.get("keywords")
        #toy.image = request.form.get("image")
        # 先保留原值
        current_image_path = toy.image

        # 如果上传了新文件就保存并替换
        file = request.files.get("image_file")
        new_rel_path = save_image(file)
        if new_rel_path:  # 只有确实上传了且类型合法才更新
            toy.image = new_rel_path
        else:
            toy.image = current_image_path

        toy.status = request.form.get("status")
        #toy.rating = float(request.form.get("rating"))

        # toy.date_loaned_out = datetime.strptime(request.form.get("date_loaned_out"), "%Y-%m-%d").date()
        # toy.last_checked = datetime.strptime(request.form.get("last_checked"), "%Y-%m-%d").date()
        # toy.date_in_stock = datetime.strptime(request.form.get("date_in_stock"), "%Y-%m-%d").date()
        toy.date_loaned_out = parse_date(request.form.get("date_loaned_out"))
        toy.last_checked = parse_date(request.form.get("last_checked"))
        toy.date_in_stock = parse_date(request.form.get("date_in_stock"))

        toy.loan_frequency = request.form.get("loan_frequency")
        toy.value = float(request.form.get("value"))

        # 新增：处理关键字字段
        dev_skill = request.form.get("dev_skill")
        safety = request.form.get("safety")
        extra1 = request.form.get("extra_keyword1")
        extra2 = request.form.get("extra_keyword2")
        extra3 = request.form.get("extra_keyword3")

        keyword_list = [dev_skill, safety, extra1, extra2, extra3]
        keyword_list = [kw.strip() for kw in keyword_list if kw.strip()]
        toy.keywords = ", ".join(keyword_list)

        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    # 初始化变量（避免未定义错误）
    dev_skill = ""
    safety = ""
    extra1 = ""
    extra2 = ""
    extra3 = []

    # 预填关键字
    existing_keywords = toy.keywords.split(",") if toy.keywords else []
    existing_keywords = [k.strip() for k in existing_keywords]

    # 自动识别已存在的 dev_skill 和 safety（如果存在）
    extras = []
    for kw in existing_keywords:
        if kw in DEVELOPMENTAL_SKILLS:
            dev_skill = kw
        elif kw in ["Safe", "Potential Risk"]:
            safety = kw
        else:
            extras.append(kw)

    extra1 = extras[0] if len(extras) > 0 else ""
    extra2 = extras[1] if len(extras) > 1 else ""
    extra3 = extras[2] if len(extras) > 2 else ""

    return render_template("edit_toy.html",
                           toy=toy,
                           toy_types=toy_types,
                           dev_skills=DEVELOPMENTAL_SKILLS,
                           age_codes=AGE_CODES,
                           freq_codes=FREQ_CODES,
                           dev_skill=dev_skill,
                           safety=safety,
                           extra1=extra1,
                           extra2=extra2,
                           extra3=extra3
                           )


# @app.route("/admin/edit/<string:toy_id>", methods=["GET", "POST"])
# def delete_toy(toy_id):
#     # 删除占位符
#     return f"删除玩具 {toy_id} 的页面开发中……"
#删除
@app.route("/admin/delete/<string:toy_id>", methods=["POST"])
@login_required
def delete_toy(toy_id):
    if current_user.role != 'admin':
        return "Only administrator can delete toys", 403

    toy = Toy.query.get_or_404(toy_id)

    #拦截已借出
    if toy.status == "borrowed":
        flash("Cannot delete: this toy is currently borrowed.", "warning")
        return redirect(url_for("admin_dashboard"))

    db.session.delete(toy)
    db.session.commit()
    flash("Toy deleted successfully","success")
    return redirect(url_for("admin_dashboard"))


# 创建数据库表
with app.app_context():
    db.create_all()

    if Toy.query.count() == 0:
        toy1 = Toy(
            toy_id="S001",
            name="toy bricks",
            brand="LEGO",
            age_range="A",
            toy_type="toy bricks",
            keywords="Hands-on Skills and Logical Thinking",
            image="images/blocks.jpeg",
            status="available",
            rating=5.0,
            date_loaned_out=datetime.strptime("2025/07/10", "%Y/%m/%d").date(),
            last_checked=datetime.strptime("2025/07/01", "%Y/%m/%d").date(),
            date_in_stock=datetime.strptime("2025/06/01", "%Y/%m/%d").date(),
            loan_frequency="B",
            value=25.00
        )
        toy2 = Toy(
            toy_id="S002",
            name="Plush Bear",
            brand="Dessny",
            age_range="B",
            toy_type="Plush Toy",
            keywords="Companionship and Emotional Development",
            image="images/bear.jpg",
            status="borrowed",
            rating=5.0,
            date_loaned_out = datetime.strptime("2025/07/10", "%Y/%m/%d").date(),
            last_checked = datetime.strptime("2025/07/01", "%Y/%m/%d").date(),
            date_in_stock = datetime.strptime("2025/06/01", "%Y/%m/%d").date(),
            loan_frequency = "B",
            value = 25.00
        )
        db.session.add_all([toy1, toy2])
        db.session.commit()

# 启动服务器
if __name__ == "__main__":
    app.run(debug=True)
