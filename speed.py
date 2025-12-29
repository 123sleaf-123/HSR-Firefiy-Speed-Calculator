import itertools
import csv
from PIL import Image, ImageDraw, ImageFont
import os

def generate_team_image_table(
    candidates=None,
    output_image="team_table.png",
    avatar_paths=None,
    avatar_size=64,
    font_path=None,  # 可选：中文ttf字体路径，如 "simhei.ttf"
    is_save=False
):    
    firefly_base_spd = 104.0
    firefly_ult_flat = 60.0
    summon_speed = 70.0
    target_moves_list = [4, 5]
    # ==========================

    # 加载默认头像（如果未提供）
    if avatar_paths is None:
        avatar_paths = {name: None for name in candidates}

    # 收集结果
    results = []
    candidate_names = list(candidates.keys())
    for team in itertools.combinations(candidate_names, 3):
        bases = [candidates[m]["base"] for m in team]
        if len(bases) != len(set(bases)):
            continue

        total_advance = total_spd_pct = total_cost = 0
        avatars = []
        for member in team:
            d = candidates[member]
            total_advance += d["advance"]
            total_spd_pct += d["spd_pct"]
            total_cost += d["cost"]
            avatars.append(avatar_paths.get(member))

        for moves in target_moves_list:
            countdown_av = 10000.0 / summon_speed
            intervals = moves - 1
            total_distance = (10000.0 * intervals) - (10000.0 * total_advance)
            req_ingame_speed = total_distance / countdown_av
            req_panel_speed = req_ingame_speed - firefly_ult_flat - (firefly_base_spd * total_spd_pct)
            display_speed = max(0, req_panel_speed, firefly_base_spd)
            
            # 过滤条件
            # if display_speed > 180 or display_speed < 160:
            #     continue

            results.append({
                "team": team,
                "avatars": avatars,
                "moves": moves,
                "advance_pct": total_advance * 100,
                "spd_pct": total_spd_pct * 100,
                "speed": display_speed,
                "cost": total_cost
            })

    # 按 cost 降序
    results.sort(key=lambda x: x["cost"], reverse=True)

    # ========== 绘图设置 ==========
    # 字体
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 16)
            font_bold = ImageFont.truetype(font_path, 18)
        else:
            # 尝试默认中文字体（Linux/Windows/macOS）
            font = ImageFont.truetype("simhei.ttf", 16)
            font_bold = ImageFont.truetype("simhei.ttf", 18)
    except:
        # 回退到默认字体（可能不支持中文）
        font = ImageFont.load_default()
        font_bold = font

    # 尺寸
    avatar_area_width = avatar_size * 3 + 20  # 3头像 + 间距
    text_area_width = 300
    row_height = max(avatar_size + 20, 40)
    margin = 10
    total_width = avatar_area_width + text_area_width + margin * 2
    total_height = len(results) * row_height + margin * 2

    # 创建画布
    img = Image.new("RGB", (total_width, total_height), "white")
    draw = ImageDraw.Draw(img)

    # ========== 绘制每一行 ==========
    y = margin
    for r in results:
        x = margin

        # --- 绘制头像 ---
        for i, avatar_path in enumerate(r["avatars"]):
            avatar_x = x + i * (avatar_size + 5)
            if avatar_path and os.path.exists(avatar_path):
                try:
                    avatar = Image.open(avatar_path).convert("RGBA")
                    avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
                    img.paste(avatar, (avatar_x, y), avatar)
                    cost = candidates[r["team"][i]]["cost"]
                    if cost > 1:
                        # 画个小红点表示有cost
                        draw.ellipse([avatar_x + avatar_size - 20, y + 5, avatar_x + avatar_size - 5, y + 20], fill="red")
                        draw.text((avatar_x + avatar_size - 14, y + 4), str(cost-1), fill="white", font=font_bold)
                    if r["team"][i] == "开拓者(555)":
                        # 画个小蓝点表示555
                        draw.ellipse([avatar_x + avatar_size - 20, y + 25, avatar_x + avatar_size - 5, y + 40], fill="blue")
                        draw.text((avatar_x + avatar_size - 18, y + 24), "5", fill="white", font=font_bold)
                except Exception as e:
                    # 头像加载失败，画个占位符
                    draw.rectangle([avatar_x, y, avatar_x+avatar_size, y+avatar_size], outline="gray")
                    draw.text((avatar_x+5, y+5), "?", fill="gray", font=font)
            else:
                # 无头像，画名字首字
                draw.rectangle([avatar_x, y, avatar_x+avatar_size, y+avatar_size], outline="lightgray")
                char = r["team"][i][0] if r["team"][i] else "?"
                draw.text((avatar_x + avatar_size//2 - 5, y + avatar_size//2 - 8), char, fill="black", font=font)
        x += avatar_area_width

        # --- 绘制文本数据 ---
        text_lines = [
            f"金数: {r['cost']}",
            f"目标: {r['moves']}动 面板: {r['speed']:.1f}",
            f"拉条: {r['advance_pct']:.0f}%",
            f"速加: {r['spd_pct']:.0f}%",
            # f"面板: {r['speed']:.1f}",
        ]
        for line in text_lines:
            draw.text((x, y), line, fill="black", font=font)
            y += 18
        y = y - 18 * len(text_lines) + row_height  # 回到下一行基线

    # 保存
    if is_save:
        img.save(output_image)
    print(f"长图表格已生成: {output_image}")
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