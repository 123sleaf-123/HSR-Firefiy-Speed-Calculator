import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import itertools
import os
from speed import generate_team_image_table

class TeamImageTableApp:
    def __init__(self, root):
        self.root = root
        self.root.title("星穹铁道配队计算器")
        self.root.geometry("800x600")
        
        # 配置数据
        self.candidates = {
            "大丽花":       {"spd_pct": 0.30, "advance": 0.00, "base": "dahlia", "cost": 1},
            "6魂大丽花":    {"spd_pct": 0.30, "advance": 0.20, "base": "dahlia", "cost": 7},
            "忘归人":       {"spd_pct": 0.00, "advance": 0.00, "base": "wang", "cost": 1},
            "2魂忘归人":    {"spd_pct": 0.00, "advance": 0.24, "base": "wang", "cost": 3},
            "阮·梅":        {"spd_pct": 0.10, "advance": 0.00, "base": "ruan", "cost": 0},
            "开拓者(555)":  {"spd_pct": 0.00, "advance": 0.24, "base": "kaituozhe", "cost": 0},
            "开拓者(555*2)":  {"spd_pct": 0.00, "advance": 0.48, "base": "kaituozhe", "cost": 0},
            "开拓者":       {"spd_pct": 0.00, "advance": 0.00, "base": "kaituozhe", "cost": 0},
            "加拉赫/灵砂":  {"spd_pct": 0.00, "advance": 0.00, "base": "heel", "cost": 0},
        }
        
        self.firefly_base_spd = 104.0
        self.firefly_ult_flat = 60.0
        self.summon_speed = 70.0
        # 目标回合选择（UI上绑定到复选框）
        self.target_move_vars = {
            4: tk.BooleanVar(value=True),
            5: tk.BooleanVar(value=True),
            6: tk.BooleanVar(value=False),
        }
        self.avatar_size = 64
        self.font_path = None
        
        # 头像映射
        self.avatar_map = {
            "大丽花": "avatars/dahlia.jpg",
            "6魂大丽花": "avatars/dahlia6.jpg",
            "忘归人": "avatars/wang.jpg",
            "2魂忘归人": "avatars/wang2.jpg",
            "阮·梅": "avatars/ruan.jpg",
            "开拓者(555)": "avatars/aki.jpg",
            "开拓者(555*2)": "avatars/aki2.jpg",
            "开拓者": "avatars/aki.jpg",
            "加拉赫/灵砂": "avatars/lingsha.jpg",
        }
        
        # 创建控制面板
        self.create_control_panel()
        
        # 创建主显示区域
        self.create_display_area()
        
        # 生成初始数据
        self.results = []
        self.generate_data()
        
        # 绑定鼠标滚轮事件
        self.bind_mouse_wheel()
        
    def create_control_panel(self):
        """创建控制面板"""
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # 生成图片按钮
        ttk.Button(control_frame, text="生成配队表格", 
                  command=self.generate_and_display).pack(side=tk.LEFT, padx=5)
        
        # 保存图片按钮
        ttk.Button(control_frame, text="保存图片", 
                  command=self.save_image).pack(side=tk.LEFT, padx=5)
        
        # 筛选条件
        ttk.Label(control_frame, text="筛选:").pack(side=tk.LEFT, padx=5)
        

        self.min_speed_var = tk.StringVar(value="100")
        self.max_speed_var = tk.StringVar(value="300")
        self.min_cost_var = tk.StringVar(value="0")
        self.max_cost_var = tk.StringVar(value="11")

        ttk.Label(control_frame, text="最低速度:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.min_speed_var, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(control_frame, text="最高速度:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.max_speed_var, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(control_frame, text="最低cost:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.min_cost_var, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(control_frame, text="最高cost:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.max_cost_var, width=6).pack(side=tk.LEFT, padx=2)

        
        ttk.Button(control_frame, text="应用筛选", 
                  command=self.apply_filter).pack(side=tk.LEFT, padx=5)

        # 目标回合选择按钮（4/5/6）
        ttk.Label(control_frame, text="目标回合:").pack(side=tk.LEFT, padx=5)
        for m in (4, 5, 6):
            cb = ttk.Checkbutton(control_frame, text=str(m), variable=self.target_move_vars[m],
                                 command=self.on_target_moves_change)
            cb.pack(side=tk.LEFT, padx=2)
        
        # 显示信息标签
        self.info_label = ttk.Label(control_frame, text="")
        self.info_label.pack(side=tk.RIGHT, padx=10)
        
        # 候选角色勾选区域（放在控制面板下方）
        self.candidate_vars = {}
        # 缩略图缓存，避免PhotoImage被垃圾回收
        self.avatar_thumbs = {}
        candidates_frame = ttk.LabelFrame(self.root, text="候选角色", padding=6)
        candidates_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        # 内部用于换行的容器（使用 grid 以便自动换行）
        candidates_inner = ttk.Frame(candidates_frame)
        candidates_inner.pack(fill=tk.X)

        # 每个候选创建一个勾选框，默认全选；按列数换行
        cols = 8
        for idx, name in enumerate(self.candidates.keys()):
            var = tk.BooleanVar(value=True)
            self.candidate_vars[name] = var

            # 单个候选的容器（头像 + 复选框）
            cand_frame = ttk.Frame(candidates_inner)
            r = idx // cols
            c = idx % cols
            cand_frame.grid(row=r, column=c, padx=6, pady=4, sticky="nw")

            # 头像缩略图（用 tk.Label 支持 image）
            avatar_path = self.avatar_map.get(name)
            if avatar_path and os.path.exists(avatar_path):
                try:
                    im = Image.open(avatar_path).convert("RGBA")
                    im = im.resize((self.avatar_size, self.avatar_size), Image.LANCZOS)
                    thumb = ImageTk.PhotoImage(im)
                    self.avatar_thumbs[name] = thumb
                    img_label = tk.Label(cand_frame, image=thumb)
                except Exception:
                    img_label = tk.Label(cand_frame, text="?", width=8, height=4, bg="lightgray")
            else:
                img_label = tk.Label(cand_frame, text="?", width=8, height=4, bg="lightgray")
            img_label.pack(side=tk.TOP)

            # 复选框（显示名字）
            cb = ttk.Checkbutton(cand_frame, text=name, variable=var, command=self.on_candidate_change)
            cb.pack(side=tk.TOP)

        # 全选/取消全选按钮，放在右侧
        btn_frame = ttk.Frame(candidates_frame)
        btn_frame.pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="全选", command=self.select_all_candidates).pack(side=tk.TOP, pady=2)
        ttk.Button(btn_frame, text="取消全选", command=self.deselect_all_candidates).pack(side=tk.TOP, pady=2)
        
    def create_display_area(self):
        """创建图片显示区域"""
        # 创建滚动区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建Canvas和滚动条
        self.canvas = tk.Canvas(main_frame, bg="white")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        
        # 创建可滚动的框架
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 将框架添加到Canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def bind_mouse_wheel(self):
        """绑定鼠标滚轮事件"""
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)  # Linux上滚
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)  # Linux下滚
        
    def on_mouse_wheel(self, event):
        """处理鼠标滚轮事件"""
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        return "break"

    def on_candidate_change(self):
        """候选勾选变更时重新生成数据并应用当前筛选"""
        # 重新生成组合并尝试应用当前数值筛选
        self.generate_data()
        try:
            self.apply_filter()
        except Exception:
            # 如果筛选输入无效，则只刷新显示
            self.generate_and_display()

    def on_target_moves_change(self):
        """目标回合勾选变更时重新生成数据并应用当前筛选"""
        self.generate_data()
        try:
            self.apply_filter()
        except Exception:
            self.generate_and_display()

    def select_all_candidates(self):
        for v in self.candidate_vars.values():
            v.set(True)
        self.on_candidate_change()

    def deselect_all_candidates(self):
        for v in self.candidate_vars.values():
            v.set(False)
        self.on_candidate_change()
    
    def generate_data(self):
        """生成配队数据"""
        self.results = []
        # 仅使用被勾选的候选
        candidate_names = [n for n, v in self.candidate_vars.items() if v.get()]
        if len(candidate_names) < 3:
            # 不足3人则没有组合
            self.results = []
            self.filtered_results = []
            return
        
        for team in itertools.combinations(candidate_names, 3):
            bases = [self.candidates[m]["base"] for m in team]
            if len(bases) != len(set(bases)):
                continue

            total_advance = total_spd_pct = total_cost = 0
            avatars = []
            for member in team:
                d = self.candidates[member]
                total_advance += d["advance"]
                total_spd_pct += d["spd_pct"]
                total_cost += d["cost"]
                avatars.append(self.avatar_map.get(member))

            # 根据UI复选框获取目标回合列表
            moves_list = [m for m, var in self.target_move_vars.items() if var.get()]
            if not moves_list:
                continue

            for moves in moves_list:
                countdown_av = 10000.0 / self.summon_speed
                intervals = moves - 1
                total_distance = (10000.0 * intervals) - (10000.0 * total_advance)
                req_ingame_speed = total_distance / countdown_av
                req_panel_speed = req_ingame_speed - self.firefly_ult_flat - (self.firefly_base_spd * total_spd_pct)
                display_speed = max(0, req_panel_speed, self.firefly_base_spd)
                
                self.results.append({
                    "team": team,
                    "avatars": avatars,
                    "moves": moves,
                    "advance_pct": total_advance * 100,
                    "spd_pct": total_spd_pct * 100,
                    "speed": display_speed,
                    "cost": total_cost
                })
        
        # 按 cost 降序排序
        self.results.sort(key=lambda x: x["cost"], reverse=True)
        self.filtered_results = self.results.copy()
    
    def apply_filter(self):
        """应用速度筛选"""
        try:
            min_speed = float(self.min_speed_var.get())
            max_speed = float(self.max_speed_var.get())
            min_cost = int(self.min_cost_var.get())
            max_cost = int(self.max_cost_var.get())

            self.filtered_results = [
                r for r in self.results
                if min_speed <= r["speed"] <= max_speed and min_cost <= r["cost"] <= max_cost
            ]
            self.info_label.config(text=f"找到 {len(self.filtered_results)} 个配队")
            self.generate_and_display()
        except ValueError:
            self.info_label.config(text="请输入有效的速度和cost范围")
    
    def generate_and_display(self):
        """生成并显示图片"""
        # 清空之前的显示
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.filtered_results:
            label = ttk.Label(self.scrollable_frame, text="未找到符合条件的配队", font=("Arial", 14))
            label.pack(pady=20)
            return
        
        # 创建PIL图像
        img = self.create_pil_image()
        
        # 转换为Tkinter可显示的格式
        self.tk_image = ImageTk.PhotoImage(img)
        
        # 在滚动框架中显示图片
        image_label = ttk.Label(self.scrollable_frame, image=self.tk_image)
        image_label.pack()
        
        self.info_label.config(text=f"显示 {len(self.filtered_results)} 个配队")
    
    def create_pil_image(self):
        """创建PIL图像"""
        # 仅传入被勾选的候选与对应头像
        selected_candidates = {name: self.candidates[name] for name, v in self.candidate_vars.items() if v.get()}
        selected_avatars = {name: self.avatar_map.get(name) for name in selected_candidates.keys()}
        selected_moves = [m for m, var in self.target_move_vars.items() if var.get()]
        return generate_team_image_table(
            candidates=selected_candidates,
            output_image="team_table.png",
            avatar_paths=selected_avatars,
            avatar_size=self.avatar_size,
            target_moves_list=selected_moves,
            font_path=self.font_path
        )
    
    def save_image(self):
        """保存图片到本地"""
        if not hasattr(self, 'filtered_results') or not self.filtered_results:
            tk.messagebox.showwarning("警告", "请先生成图片")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile="team_table.png"
        )
        
        if file_path:
            try:
                img = self.create_pil_image()
                img.save(file_path)
                self.info_label.config(text=f"图片已保存到: {file_path}")
                tk.messagebox.showinfo("成功", f"图片已保存到:\n{file_path}")
            except Exception as e:
                tk.messagebox.showerror("错误", f"保存失败: {str(e)}")

def main():
    root = tk.Tk()
    app = TeamImageTableApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()