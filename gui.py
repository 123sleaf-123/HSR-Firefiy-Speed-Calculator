import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from typing import Dict, Any

# 假设 speed 模块在同目录下
try:
    from speed import generate_team_image_table
except ImportError:
    # Mock 用于测试
    def generate_team_image_table(**kwargs):
        return Image.new('RGB', (800, 200), color='white')

# --- 配置数据 ---
CONSTANTS = {
    "FIREFLY_BASE_SPD": 104.0,
    "FIREFLY_ULT_FLAT": 60.0,
    "SUMMON_SPEED": 70.0,
    "AVATAR_SIZE": 64,
    "WINDOW_SIZE": "1100x900", # 稍微调大一点窗口以容纳新增控件
}

CANDIDATES_DATA = {
    "大丽花":       {"spd_pct": 0.30, "advance": 0.00, "base": "dahlia", "cost": 1, "img": "avatars/dahlia.jpg", "times": 1},
    "6魂大丽花":    {"spd_pct": 0.30, "advance": 0.20, "base": "dahlia", "cost": 7, "img": "avatars/dahlia6.jpg", "times": 1},
    "忘归人":       {"spd_pct": 0.00, "advance": 0.00, "base": "wang", "cost": 1,   "img": "avatars/wang.jpg", "times": 1},
    "2魂忘归人":    {"spd_pct": 0.00, "advance": 0.24, "base": "wang", "cost": 3,   "img": "avatars/wang2.jpg", "times": 1},
    "阮·梅":        {"spd_pct": 0.10, "advance": 0.00, "base": "ruan", "cost": 0,   "img": "avatars/ruan.jpg", "times": 1},
    "开拓者(555)":  {"spd_pct": 0.00, "advance": 0.24, "base": "kaituozhe", "cost": 0, "img": "avatars/aki.jpg", "times": 1},
    "开拓者":       {"spd_pct": 0.00, "advance": 0.00, "base": "kaituozhe", "cost": 0, "img": "avatars/aki.jpg", "times": 1},
    "加拉赫/灵砂":  {"spd_pct": 0.00, "advance": 0.00, "base": "heel", "cost": 0,     "img": "avatars/lingsha.jpg", "times": 1},
}

class TeamImageTableApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("星穹铁道配队计算器")
        self.root.geometry(CONSTANTS["WINDOW_SIZE"])
        
        # --- 初始化状态变量 ---
        self.font_path = None
        self.file_path = "team_table.png"
        self.tk_image = None  
        self.avatar_thumbs = {} 
        self.raw_results = []   
        self.filtered_results = [] 

        # 变量绑定
        self.target_move_vars = {
            4: tk.BooleanVar(value=True),
            5: tk.BooleanVar(value=True),
            6: tk.BooleanVar(value=False),
            7: tk.BooleanVar(value=False),
            8: tk.BooleanVar(value=False),
        }
        self.filter_vars = {
            "min_spd": tk.StringVar(value="100"),
            "max_spd": tk.StringVar(value="300"),
            "min_cost": tk.StringVar(value="0"),
            "max_cost": tk.StringVar(value="11"),
        }
        self.candidate_vars = {} 
        self.candidate_times_vars = {} # [新增] 存储每个角色的 times 变量

        # --- 构建界面 ---
        self._setup_ui()
        
        # --- 初始逻辑 ---
        self.bind_mouse_wheel()
        self.refresh_data_and_display()

    def _setup_ui(self):
        """构建整体UI布局"""
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        self._setup_control_panel(control_frame)
        
        candidates_frame = ttk.LabelFrame(self.root, text="候选角色选择 (勾选并设置触发次数)", padding=6)
        candidates_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self._setup_candidate_grid(candidates_frame)

        self._setup_display_area()

    def _setup_control_panel(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="生成表格", command=self.refresh_data_and_display).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="保存图片", command=self.save_image).pack(side=tk.LEFT, padx=2)

        filter_frame = ttk.Labelframe(parent, text="筛选条件", padding=(5, 0))
        filter_frame.pack(side=tk.LEFT, padx=15)
        
        self._create_labeled_entry(filter_frame, "速度:", self.filter_vars["min_spd"], self.filter_vars["max_spd"])
        self._create_labeled_entry(filter_frame, "Cost:", self.filter_vars["min_cost"], self.filter_vars["max_cost"])
        
        ttk.Button(filter_frame, text="应用筛选", command=self.apply_filter_only).pack(side=tk.LEFT, padx=5, pady=2)

        moves_frame = ttk.Labelframe(parent, text="目标回合", padding=(5, 0))
        moves_frame.pack(side=tk.LEFT, padx=5)
        for m in self.target_move_vars.keys():
            ttk.Checkbutton(moves_frame, text=str(m), variable=self.target_move_vars[m], 
                            command=self.refresh_data_and_display).pack(side=tk.LEFT, padx=2)

        self.info_label = ttk.Label(parent, text="就绪", font=("Microsoft YaHei", 10, "bold"))
        self.info_label.pack(side=tk.RIGHT, padx=10)

    def _create_labeled_entry(self, parent, label_text, min_var, max_var):
        f = ttk.Frame(parent)
        f.pack(side=tk.LEFT, padx=5)
        ttk.Label(f, text=label_text).pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=min_var, width=5).pack(side=tk.LEFT)
        ttk.Label(f, text="-").pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=max_var, width=5).pack(side=tk.LEFT)

    def _setup_candidate_grid(self, parent):
        """生成候选人网格，包含图片、复选框和次数输入"""
        grid_frame = ttk.Frame(parent)
        grid_frame.pack(fill=tk.X, expand=True)
        
        cols = 8
        for idx, (name, data) in enumerate(CANDIDATES_DATA.items()):
            # 1. 勾选状态变量
            is_checked_var = tk.BooleanVar(value=True)
            self.candidate_vars[name] = is_checked_var
            
            # 2. 次数状态变量 [新增]
            times_val_var = tk.IntVar(value=data.get("times", 1))
            self.candidate_times_vars[name] = times_val_var

            # 单元格容器
            cell = ttk.Frame(grid_frame, borderwidth=1, relief="solid") # 加个边框看清楚范围
            cell.grid(row=idx // cols, column=idx % cols, padx=4, pady=4, sticky="n")
            
            # 图片
            try:
                if os.path.exists(data["img"]):
                    pil_img = Image.open(data["img"]).convert("RGBA")
                    pil_img = pil_img.resize((CONSTANTS["AVATAR_SIZE"], CONSTANTS["AVATAR_SIZE"]), Image.LANCZOS)
                    tk_thumb = ImageTk.PhotoImage(pil_img)
                    self.avatar_thumbs[name] = tk_thumb
                    lbl = tk.Label(cell, image=tk_thumb)
                else:
                    raise FileNotFoundError
            except Exception:
                lbl = tk.Label(cell, text="No Img", width=8, height=4, bg="#eee")
            lbl.pack(pady=(2,0))

            # 复选框 (放在图片下面)
            cb = ttk.Checkbutton(cell, text=name, variable=is_checked_var, 
                            command=self.refresh_data_and_display)
            cb.pack(pady=(2,0))
            
            # 次数输入控制区域 [新增]
            times_frame = ttk.Frame(cell)
            times_frame.pack(pady=(0, 5))
            
            ttk.Label(times_frame, text="×", font=("Arial", 9, "bold"), foreground="#666").pack(side=tk.LEFT)
            
            # Spinbox 用于输入次数
            spin = ttk.Spinbox(
                times_frame, 
                from_=1, 
                to=10, 
                width=3, 
                textvariable=times_val_var,
                command=self.refresh_data_and_display # 点击上下箭头触发
            )
            spin.pack(side=tk.LEFT)
            
            # 绑定回车键，防止手动输入不刷新
            spin.bind("<Return>", lambda e: self.refresh_data_and_display())
            spin.bind("<FocusOut>", lambda e: self.refresh_data_and_display())

        # 全选控制
        ctrl_frame = ttk.Frame(parent)
        ctrl_frame.pack(side=tk.RIGHT, anchor="n")
        ttk.Button(ctrl_frame, text="全选", command=lambda: self._toggle_all(True)).pack(pady=2)
        ttk.Button(ctrl_frame, text="反选", command=lambda: self._toggle_all(False)).pack(pady=2)

    def _setup_display_area(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(main_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _toggle_all(self, state: bool):
        for var in self.candidate_vars.values():
            var.set(state)
        self.refresh_data_and_display()

    def _get_selected_candidates(self) -> Dict[str, Any]:
        """[修改] 获取当前勾选的候选人数据，并注入动态的 times 值"""
        selected = {}
        for name, var in self.candidate_vars.items():
            if var.get():
                # 复制原始数据，避免修改全局常量
                cand_data = CANDIDATES_DATA[name].copy()
                
                # 获取动态设置的 times
                try:
                    # 使用 get() 获取 IntVar 的值
                    current_times = self.candidate_times_vars[name].get()
                    cand_data["times"] = current_times
                except Exception:
                    # 如果输入无效，保持默认值 1
                    cand_data["times"] = 1
                
                selected[name] = cand_data
        return selected

    def apply_filter_only(self):
        """仅执行筛选逻辑"""
        try:
            min_s = float(self.filter_vars["min_spd"].get())
            max_s = float(self.filter_vars["max_spd"].get())
            min_c = int(self.filter_vars["min_cost"].get())
            max_c = int(self.filter_vars["max_cost"].get())

            # 如果你有 self.raw_results 数据，可以在这里筛选
            # 这里的逻辑仅作为 UI 展示，实际图片生成依赖于 selected_candidates
            self.info_label.config(text=f"参数有效 | 正在重新计算...")
            
            # 重新生成图片
            self._update_display_image()
            
        except ValueError:
            self.info_label.config(text="筛选数值无效", foreground="red")

    def refresh_data_and_display(self):
        # 统一入口，刷新数据
        self.apply_filter_only()

    def _update_display_image(self, is_save=False):
        """调用外部库生成图片并显示"""
        for w in self.scrollable_frame.winfo_children():
            w.destroy()

        try:
            selected_cands = self._get_selected_candidates()
            selected_avatars = {n: d["img"] for n, d in selected_cands.items()}
            selected_moves = [m for m, v in self.target_move_vars.items() if v.get()]

            pil_img = generate_team_image_table(
                candidates=selected_cands, # 这里传进去的 candidates 现在包含了动态的 times
                output_image=self.file_path,
                avatar_paths=selected_avatars,
                avatar_size=CONSTANTS["AVATAR_SIZE"],
                target_moves_list=selected_moves,
                font_path=self.font_path,
                filter_settings={
                    "min_spd": self.filter_vars["min_spd"].get(),
                    "max_spd": self.filter_vars["max_spd"].get(),
                    "min_cost": self.filter_vars["min_cost"].get(),
                    "max_cost": self.filter_vars["max_cost"].get()
                },
                is_save=is_save
            )

            self.tk_image = ImageTk.PhotoImage(pil_img)
            ttk.Label(self.scrollable_frame, image=self.tk_image).pack()
            self.info_label.config(text=f"生成完成，包含 {len(selected_cands)} 个角色")
            
        except Exception as e:
            ttk.Label(self.scrollable_frame, text=f"生成图片出错:\n{e}", foreground="red").pack(pady=20)

    def save_image(self):
        if not self.tk_image:
            messagebox.showwarning("警告", "当前没有生成的图片")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")],
            initialfile="team_table.png"
        )
        self.file_path = file_path
        if file_path:
            try:
                selected_cands = self._get_selected_candidates()
                selected_avatars = {n: d["img"] for n, d in selected_cands.items()}
                selected_moves = [m for m, v in self.target_move_vars.items() if v.get()]
                
                self._update_display_image(is_save=True)  # 重新生成图片以确保最新
                messagebox.showinfo("成功", f"保存成功: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    def bind_mouse_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam') 
    app = TeamImageTableApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()