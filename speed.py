import itertools
import csv
from PIL import Image, ImageDraw, ImageFont
import os
import os
import itertools
from PIL import Image, ImageDraw, ImageFont

def get_default_font(font_path=None, size=16):
    """辅助函数：尝试获取可用字体，防止报错"""
    # 1. 尝试用户提供的路径
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    
    # 2. 尝试常见的系统中文路径 (Windows/Mac/Linux)
    system_fonts = [
        "msyh.ttc", "simhei.ttf", "arialuni.ttf",  # Windows
        "/System/Library/Fonts/PingFang.ttc",      # MacOS
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf" # Linux
    ]
    for f in system_fonts:
        try:
            return ImageFont.truetype(f, size)
        except:
            continue
            
    # 3. 最后回退到默认（不支持中文）
    return ImageFont.load_default()

def generate_team_image_table(
    candidates: dict,
    output_image="team_table.png",
    avatar_paths=None,
    avatar_size=64,
    target_moves_list=[4, 5],
    font_path=None,
    is_save=False,
    provided_results=None,  # 接收外部计算好的列表
    filter_settings=None    # 接收筛选配置: {'min_spd': 0, 'max_spd': 999, ...}
):
    """
    生成配队图片表格。
    优先使用 provided_results，如果没有，则根据 candidates 和 filter_settings 现场计算。
    """
    
    # 常量定义
    CONSTANTS = {
        "firefly_base_spd": 104.0,
        "firefly_ult_flat": 60.0,
        "summon_speed": 70.0
    }

    # 1. 准备数据
    final_results = []

    if provided_results is not None:
        # A. 优先路径：直接使用外部传进来的已筛选数据
        final_results = provided_results
    else:
        # B. 后备路径：内部计算 (保持原有逻辑，但加入 filter_settings)
        if avatar_paths is None:
            avatar_paths = {name: None for name in candidates}
            
        candidate_names = list(candidates.keys())
        
        # 解析筛选条件
        f_min_spd = float(filter_settings.get('min_spd', 0)) if filter_settings else 0
        f_max_spd = float(filter_settings.get('max_spd', 999)) if filter_settings else 999
        f_min_cost = int(filter_settings.get('min_cost', 0)) if filter_settings else 0
        f_max_cost = int(filter_settings.get('max_cost', 99)) if filter_settings else 99

        for team in itertools.combinations(candidate_names, 3):
            bases = [candidates[m]["base"] for m in team]
            if len(bases) != len(set(bases)):
                continue

            total_advance = total_spd_pct = total_cost = 0
            avatars = []
            for member in team:
                d = candidates[member]
                total_advance += d["advance"] * d["times"]
                total_spd_pct += d["spd_pct"]
                total_cost += d["cost"]
                avatars.append(avatar_paths.get(member))

            for moves in target_moves_list:
                countdown_av = 10000.0 / CONSTANTS["summon_speed"]
                intervals = moves - 1
                total_distance = (10000.0 * intervals) - (10000.0 * total_advance)
                req_ingame_speed = total_distance / countdown_av
                req_panel_speed = req_ingame_speed - CONSTANTS["firefly_ult_flat"] - (CONSTANTS["firefly_base_spd"] * total_spd_pct)
                display_speed = max(0, req_panel_speed, CONSTANTS["firefly_base_spd"])
                
                # === 内部筛选逻辑 ===
                if not (f_min_spd <= display_speed <= f_max_spd):
                    continue
                if not (f_min_cost <= total_cost <= f_max_cost):
                    continue

                final_results.append({
                    "team": team,
                    "avatars": avatars,
                    "moves": moves,
                    "advance_pct": total_advance * 100,
                    "spd_pct": total_spd_pct * 100,
                    "speed": display_speed,
                    "cost": total_cost
                })
        
        # 排序
        final_results.sort(key=lambda x: x["cost"], reverse=True)

    # 如果没有结果，生成一张提示图
    if not final_results:
        font = get_default_font(font_path, 20)
        img = Image.new("RGB", (400, 100), "white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "未找到符合条件的配队", fill="black", font=font)
        if is_save: img.save(output_image)
        return img

    # 2. 绘图设置
    font_main = get_default_font(font_path, 16)
    font_bold = get_default_font(font_path, 18) # 简单起见，加粗可以用稍大号字体代替，或者加载具体的bold字体

    # 尺寸计算
    avatar_area_width = avatar_size * 3 + 30  # 3个头像 + 间隙
    text_area_width = 280
    row_height = max(avatar_size + 20, 90) # 保证高度足够放下文本
    margin = 15
    
    total_width = avatar_area_width + text_area_width + margin * 2
    total_height = len(final_results) * row_height + margin * 2

    img = Image.new("RGB", (total_width, total_height), "white")
    draw = ImageDraw.Draw(img)

    # 3. 绘制每一行
    y = margin
    for r in final_results:
        x = margin

        # --- A. 绘制头像 ---
        current_avatars = r.get("avatars", [])
        # 如果传入的是 provided_results，avatars 可能是路径列表
        
        for i, avatar_path in enumerate(current_avatars):
            avatar_x = x + i * (avatar_size + 10)
            
            # 绘制底图
            has_img = False
            if avatar_path and os.path.exists(avatar_path):
                try:
                    avatar_img = Image.open(avatar_path).convert("RGBA")
                    avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                    img.paste(avatar_img, (avatar_x, y), avatar_img)
                    has_img = True
                except:
                    pass
            
            if not has_img:
                draw.rectangle([avatar_x, y, avatar_x+avatar_size, y+avatar_size], outline="#ccc", width=1)
                # 尝试取名字首字
                name = r["team"][i] if i < len(r["team"]) else "?"
                draw.text((avatar_x+20, y+20), name[0], fill="#999", font=font_main)

            # 绘制标记 (Cost红点)
            # 需要回溯 candidates 获取 cost，防止 provided_results 里没有详细 cost 数据
            # 但通常 provided_results 应该包含 cost。为了保险，我们尝试从 candidates 查
            char_name = r["team"][i]
            char_data = candidates.get(char_name, {})
            cost = char_data.get("cost", 0)
            times = char_data.get("times", 1)

            # 红点 (Cost > 1)
            if cost > 1:
                draw.ellipse([avatar_x + avatar_size - 18, y, avatar_x + avatar_size, y + 18], fill="#ff4d4f")
                draw.text((avatar_x + avatar_size - 13, y - 1), str(cost-1), fill="white", font=font_main)
            
            # 蓝点 (555)
            if "555" in char_name:
                 draw.ellipse([avatar_x + avatar_size - 18, y + 22, avatar_x + avatar_size, y + 40], fill="#1890ff")
                 draw.text((avatar_x + avatar_size - 13, y + 21), "5", fill="white", font=font_main)

            if times > 1:
                 draw.ellipse([avatar_x + avatar_size - 18, y + 44, avatar_x + avatar_size, y + 62], fill="#52c41a")
                 draw.text((avatar_x + avatar_size - 13, y + 43), str(times), fill="white", font=font_main)

        x += avatar_area_width

        # --- B. 绘制文本 ---
        # 使用 provided_results 中的预计算数据
        text_lines = [
            f"目标: {r['moves']} 动",
            f"金数: {r['cost']}         面板速度: {r['speed']:.1f}",
            f"全队拉条: {r.get('advance_pct', 0):.0f}%",
            f"全队速加: {r.get('spd_pct', 0):.0f}%",
        ]
        
        text_y = y + 5
        for line in text_lines:
            draw.text((x, text_y), line, fill="#333", font=font_main)
            text_y += 18
            
        # 绘制分割线
        y += row_height
        if y < total_height - margin:
            draw.line([margin, y - 5, total_width - margin, y - 5], fill="#eee", width=1)

    # 4. 保存与返回
    if is_save:
        try:
            img.save(output_image)
            print(f"表格已保存: {output_image}")
        except Exception as e:
            print(f"保存失败: {e}")
            
    return img

# ========== 使用示例 ==========
if __name__ == "__main__":
    # 请将你的头像放在 avatars/ 目录下，并按角色名命名
    avatar_map = {
        "大丽花": "avatars/dahlia.jpg",
        "6魂大丽花": "avatars/dahlia6.jpg",
        "忘归人": "avatars/wang.jpg",
        "2魂忘归人": "avatars/wang2.jpg",
        "阮·梅": "avatars/ruan.jpg",
        "开拓者(555)": "avatars/aki.jpg",
        "开拓者": "avatars/aki.jpg",
        "加拉赫/灵砂": "avatars/lingsha.jpg",
    }

    # ========== 配置 ==========
    candidates = {
        "大丽花":       {"spd_pct": 0.30, "advance": 0.00, "base": "dahlia", "cost": 1},
        "6魂大丽花":    {"spd_pct": 0.30, "advance": 0.20, "base": "dahlia", "cost": 7},
        "忘归人":       {"spd_pct": 0.00, "advance": 0.00, "base": "wang", "cost": 1},
        "2魂忘归人":    {"spd_pct": 0.00, "advance": 0.24, "base": "wang", "cost": 3},
        "阮·梅":        {"spd_pct": 0.10, "advance": 0.00, "base": "ruan", "cost": 0},
        "开拓者(555)":  {"spd_pct": 0.00, "advance": 0.24, "base": "kaituozhe", "cost": 0},
        "开拓者":  {"spd_pct": 0.00, "advance": 0.00, "base": "kaituozhe", "cost": 0},
        "加拉赫/灵砂":  {"spd_pct": 0.00, "advance": 0.00, "base": "heel", "cost": 0},
    }

    generate_team_image_table(
        candidates=candidates,
        output_image="team_combinations_with_avatars.png",
        avatar_paths=avatar_map,
        avatar_size=64,
        font_path="SimSun/SimSun.ttf",  # 可选，换成你系统的中文字体
        is_save=True
    )