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
            "开拓者":       {"spd_pct": 0.00, "advance": 0.00, "base": "kaituozhe", "cost": 0},
            "加拉赫/灵砂":  {"spd_pct": 0.00, "advance": 0.00, "base": "heel", "cost": 0},
        }
        
        self.firefly_base_spd = 104.0
        self.firefly_ult_flat = 60.0
        self.summon_speed = 70.0
        self.target_moves_list = [4, 5]
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
        
        self.min_speed_var = tk.StringVar(value="160")
        self.max_speed_var = tk.StringVar(value="180")
        
        ttk.Label(control_frame, text="最低速度:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.min_speed_var, width=6).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(control_frame, text="最高速度:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(control_frame, textvariable=self.max_speed_var, width=6).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(control_frame, text="应用筛选", 
                  command=self.apply_filter).pack(side=tk.LEFT, padx=5)
        
        # 显示信息标签
        self.info_label = ttk.Label(control_frame, text="")
        self.info_label.pack(side=tk.RIGHT, padx=10)
        
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
    
    def generate_data(self):
        """生成配队数据"""
        self.results = []
        candidate_names = list(self.candidates.keys())
        
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

            for moves in self.target_moves_list:
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
            
            self.filtered_results = [
                r for r in self.results 
                if min_speed <= r["speed"] <= max_speed
            ]
            
            self.info_label.config(text=f"找到 {len(self.filtered_results)} 个配队")
            self.generate_and_display()
        except ValueError:
            self.info_label.config(text="请输入有效的速度范围")
    
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
        return generate_team_image_table(
            candidates=self.candidates,
            output_image="team_table.png",
            avatar_paths=self.avatar_map,
            avatar_size=self.avatar_size,
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