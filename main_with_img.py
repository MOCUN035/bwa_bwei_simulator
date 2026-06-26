import pygame
import random
import math
import sys
import struct  # 用於將數學訊號打包成音效二進位資料

# 初始化 Pygame 與 音效混音器
pygame.init()
pygame.mixer.init()

# 視窗大小設定
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("虛擬擲筊模擬器 - 神明顯靈版")
clock = pygame.time.Clock()

# 顏色定義
BACKGROUND_COLOR = (30, 30, 30)
GROUND_COLOR = (45, 45, 45)
TEXT_COLOR = (240, 240, 240)

# 遊戲狀態
STATE_HAND = 0
STATE_THROW = 1
STATE_RESULT = 2

def get_chinese_font(size):
    font_names = ['microsoftjhenghei', 'pingfangtc', 'simsun', 'stxihei', 'arial']
    for f in font_names:
        if f in pygame.font.get_fonts():
            return pygame.font.SysFont(f, size)
    return pygame.font.SysFont(None, size)

# ─── 字體大小調整 ───
font_small = get_chinese_font(22)  # 新增：用於右上角縮小提示
font_ui = get_chinese_font(36)
font_title = get_chinese_font(80)

# ─── 載入神明系列插畫 (置於 image 資料夾) ───
def load_god_images():
    """載入聖筊、笑筊、陰筊的三張土地公插畫"""
    images = {}
    size = (450, 450) # 縮放到最適合畫面的尺寸
    try:
        images["【 聖 筊 】"] = pygame.transform.scale(pygame.image.load("image/god_win.png").convert_alpha(), size)
        images["【 笑 筊 】"] = pygame.transform.scale(pygame.image.load("image/god_laugh.png").convert_alpha(), size)
        images["【 陰 筊 】"] = pygame.transform.scale(pygame.image.load("image/god_no.png").convert_alpha(), size)
        print("🎉 土地公插畫全數載入成功！")
    except Exception as e:
        print(f"⚠️ 圖片載入失敗，將啟動純程式碼神光保底模式。錯誤原因: {e}")
        images["【 聖 筊 】"] = None
        images["【 笑 筊 】"] = None
        images["【 陰 筊 】"] = None
    return images

god_images = load_god_images()
god_alpha = 0  # 用於控制插畫與神光的淡入透明度 (0 - 255)

# ─── 聲音合成器 ───

def load_bounce_sound():
    """優先讀取 bounce.wav；若無，則動態合成木頭敲擊聲"""
    try:
        return pygame.mixer.Sound("bounce.wav")
    except:
        sample_rate = 44100
        duration = 0.06
        frequency = 320
        buf = bytearray()
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            decay = math.exp(-t * 75) 
            value = int(32767 * math.sin(2 * math.pi * frequency * t) * decay)
            buf.extend(struct.pack('<h', value))
        return pygame.mixer.Sound(buffer=bytes(buf))

def load_throw_sound():
    """動態合成丟出去的「咻」破風聲"""
    try:
        return pygame.mixer.Sound("throw.wav")
    except:
        sample_rate = 44100
        duration = 0.25   # 0.25 秒的滑音
        buf = bytearray()
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            angle = 2 * math.pi * (450 * t - 0.5 * (300 / duration) * (t**2))
            envelope = math.sin(math.pi * (t / duration))
            value = int(22000 * math.sin(angle) * envelope)
            buf.extend(struct.pack('<h', value))
        return pygame.mixer.Sound(buffer=bytes(buf))

# 實例化音效物件
sound_bounce = load_bounce_sound()
sound_throw = load_throw_sound()

def create_hand_surface():
    """繪製寫實左手掌"""
    surf = pygame.Surface((180, 140), pygame.SRCALPHA)
    skin = (242, 204, 172)
    shadow = (212, 166, 133)
    
    pygame.draw.ellipse(surf, skin, (15, 25, 60, 24))
    pygame.draw.ellipse(surf, skin, (5, 49, 65, 24))
    pygame.draw.ellipse(surf, skin, (10, 73, 62, 24))
    pygame.draw.ellipse(surf, skin, (25, 95, 50, 22))
    pygame.draw.line(surf, shadow, (55, 41), (20, 37), 2)
    pygame.draw.line(surf, shadow, (62, 65), (15, 61), 2)
    pygame.draw.line(surf, shadow, (58, 89), (20, 85), 2)
    pygame.draw.ellipse(surf, skin, (45, 25, 105, 85))
    pygame.draw.ellipse(surf, skin, (120, 50, 45, 26))
    pygame.draw.line(surf, shadow, (120, 63), (140, 68), 2)
    pygame.draw.arc(surf, shadow, (65, 45, 60, 50), 0.5, 3.0, 2)
    pygame.draw.arc(surf, shadow, (50, 65, 50, 35), 0.2, 2.5, 2)
    return surf

def create_cup_surface(is_flat_side):
    """繪製精美筊杯"""
    surf = pygame.Surface((100, 100), pygame.SRCALPHA)
    if is_flat_side:
        points = []
        for theta in range(0, 181):
            rad = math.radians(theta)
            x = 50 + 40 * math.cos(rad)
            y = 50 + 40 * math.sin(rad)
            points.append((x, y))
        pygame.draw.polygon(surf, (210, 105, 30), points)
        pygame.draw.line(surf, (139, 69, 19), (10, 50), (90, 50), 3)
    else:
        points = []
        for theta in range(0, 181):
            rad = math.radians(theta)
            x = 50 + 40 * math.cos(rad)
            y = 50 - 40 * math.sin(rad)
            points.append((x, y))
        pygame.draw.polygon(surf, (150, 0, 0), points)
        pygame.draw.arc(surf, (200, 50, 50), (10, 10, 80, 80), 0, math.pi, 3)
    return surf

def draw_god_rays(surface, time_tick):
    """在神明背後繪製隨時間旋轉的金色光芒（同步往下調整中心點）"""
    # 【調整】中心點 y 從原本的 -60 改為 +80，配合土地公位置
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80
    num_rays = 12
    ray_length = 600
    
    ray_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    for i in range(num_rays):
        angle = math.radians(i * (360 / num_rays) + time_tick * 0.4)
        x1 = center_x + ray_length * math.cos(angle - 0.08)
        y1 = center_y + ray_length * math.sin(angle - 0.08)
        x2 = center_x + ray_length * math.cos(angle + 0.08)
        y2 = center_y + ray_length * math.sin(angle + 0.08)
        
        pygame.draw.polygon(ray_surf, (255, 215, 0), [(center_x, center_y), (x1, y1), (x2, y2)])
    
    ray_surf.set_alpha(int(god_alpha * 0.15))
    surface.blit(ray_surf, (0, 0))

class BwaBwei:
    def __init__(self, is_left=True):
        self.is_left = is_left
        self.surf_curved = create_cup_surface(is_flat_side=False)
        self.surf_flat = create_cup_surface(is_flat_side=True)
        self.size_radius = 40
        self.reset()

    def reset(self):
        self.x = (SCREEN_WIDTH // 2) - 65 if self.is_left else (SCREEN_WIDTH // 2) + 65
        self.y = SCREEN_HEIGHT - 180
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.v_angle = 0
        self.is_spinning = False
        self.bounce_count = 0
        self.max_bounces = 2
        self.final_state = '平'
        self.floor_y = SCREEN_HEIGHT - 100

    def throw(self, final_state):
        self.final_state = final_state
        self.is_spinning = True
        self.bounce_count = 0
        self.vy = random.uniform(-19, -23)
        self.vx = random.uniform(-6, -3) if self.is_left else random.uniform(3, 6)
        self.v_angle = random.uniform(15, 25)

    def update(self, current_state, hand_y):
        if current_state == STATE_HAND:
            self.x = (SCREEN_WIDTH // 2) - 65 if self.is_left else (SCREEN_WIDTH // 2) + 65
            self.y = hand_y - 15
            self.angle = 0
            
        elif self.is_spinning:
            self.x += self.vx
            self.y += self.vy
            self.vy += 0.6
            self.angle += self.v_angle

            # 邊界碰撞
            if self.x + self.size_radius > SCREEN_WIDTH:
                self.x = SCREEN_WIDTH - self.size_radius
                self.vx = -self.vx * 0.8
                self.v_angle *= 0.9
                sound_bounce.play()
                
            if self.x - self.size_radius < 0:
                self.x = self.size_radius
                self.vx = -self.vx * 0.8
                self.v_angle *= 0.9
                sound_bounce.play()

            # 地面碰撞
            if self.y >= self.floor_y:
                self.y = self.floor_y
                if self.bounce_count < self.max_bounces:
                    self.vy = -self.vy * 0.4
                    self.vx *= 0.6
                    self.v_angle *= 0.5
                    self.bounce_count += 1
                    sound_bounce.play()
                else:
                    if self.is_spinning:
                        sound_bounce.play()
                    self.is_spinning = False
                    self.vx = 0
                    self.vy = 0
                    self.v_angle = 0
                    self.angle = 0

    def draw(self, surface):
        if self.is_spinning:
            if (int(self.angle / 90) % 2 == 0):
                current_surf = self.surf_curved
            else:
                current_surf = self.surf_flat
        else:
            current_surf = self.surf_flat if self.final_state == '平' else self.surf_curved

        rotated_surf = pygame.transform.rotate(current_surf, self.angle)
        new_rect = rotated_surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_surf, new_rect.topleft)

def main():
    global god_alpha
    state = STATE_HAND
    cup_left = BwaBwei(is_left=True)
    cup_right = BwaBwei(is_left=False)
    
    hand_left_surf = create_hand_surface()
    hand_right_surf = pygame.transform.flip(hand_left_surf, True, False)
    
    hand_current_y = SCREEN_HEIGHT - 160
    throw_anim_timer = 0
    
    result_text = ""
    time_tick = 0

    running = True
    while running:
        time_tick += 1
        screen.fill(BACKGROUND_COLOR)
        
        # ─── 神明插畫與特效浮現邏輯 ───
        if state == STATE_RESULT:
            if god_alpha < 220:
                god_alpha += 6
            
            # 1. 繪製旋轉神光背景（已下移）
            draw_god_rays(screen, time_tick)
            
            # 2. 繪製土地公插畫
            current_god_img = god_images.get(result_text)
            if current_god_img:
                temp_god_surf = current_god_img.copy()
                temp_god_surf.set_alpha(god_alpha)
                
                # 微弱的上下浮動呼吸感
                float_offset = math.sin(time_tick * 0.06) * 6
                # 【調整】圖片中心點 y 從原本的 -60 往下大幅移動到 +80，完全避開上方文字！
                god_rect = temp_god_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80 + int(float_offset)))
                screen.blit(temp_god_surf, god_rect.topleft)
        else:
            if god_alpha > 0:
                god_alpha -= 20

        # 繪製地面
        pygame.draw.rect(screen, GROUND_COLOR, (0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 80))
        pygame.draw.line(screen, (80, 80, 80), (0, SCREEN_HEIGHT - 80), (SCREEN_WIDTH, SCREEN_HEIGHT - 80), 3)

        if state == STATE_HAND:
            hand_target_y = (SCREEN_HEIGHT - 160) + math.sin(time_tick * 0.05) * 5
        elif state == STATE_THROW and throw_anim_timer > 0:
            throw_anim_timer -= 1
            if throw_anim_timer > 10:
                hand_target_y = SCREEN_HEIGHT - 120
            else:
                hand_target_y = SCREEN_HEIGHT - 240
        else:
            hand_target_y = SCREEN_HEIGHT + 50
            
        hand_current_y += (hand_target_y - hand_current_y) * 0.15

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if state == STATE_HAND:
                        res_l = random.choice(['平', '凸'])
                        res_m = random.choice(['平', '凸'])
                        
                        if res_l != res_m: result_text = "【 聖 筊 】"
                        elif res_l == '平' and res_m == '平': result_text = "【 笑 筊 】"
                        else: result_text = "【 陰 筊 】"
                        
                        throw_anim_timer = 15
                        state = STATE_THROW
                        
                    elif state == STATE_RESULT:
                        cup_left.reset()
                        cup_right.reset()
                        state = STATE_HAND

        # 拋出瞬間
        if state == STATE_THROW and throw_anim_timer == 5:
            cup_left.throw(res_l)
            cup_right.throw(res_m)
            sound_throw.play()

        cup_left.update(state, hand_current_y)
        cup_right.update(state, hand_current_y)

        if state == STATE_THROW and throw_anim_timer == 0 and not cup_left.is_spinning and not cup_right.is_spinning:
            state = STATE_RESULT

        # 繪製雙手
        left_hand_rect = hand_left_surf.get_rect(center=(SCREEN_WIDTH // 2 - 80, int(hand_current_y)))
        right_hand_rect = hand_right_surf.get_rect(center=(SCREEN_WIDTH // 2 + 80, int(hand_current_y)))
        screen.blit(hand_left_surf, left_hand_rect.topleft)
        screen.blit(hand_right_surf, right_hand_rect.topleft)

        # 繪製筊杯
        cup_left.draw(screen)
        cup_right.draw(screen)

        # ─── 畫面文字排版 ───
        if state == STATE_HAND:
            text_prompt = font_ui.render("請誠心祈求後，按下 [ 空白鍵 ] 擲筊", True, TEXT_COLOR)
            screen.blit(text_prompt, (text_prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))))

        if state == STATE_RESULT:
            # 1. 結果大字（維持在頂部舒適區）
            res_surf = font_title.render(result_text, True, (255, 215, 0))
            screen.blit(res_surf, (res_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 240))))
            
            # 2. 說明文字
            sub_text = ""
            if result_text == "【 聖 筊 】": sub_text = "神明聽見了，同意你的請求！"
            elif result_text == "【 笑 筊 】": sub_text = "神明笑而不答，換個方式問問看吧。"
            elif result_text == "【 陰 筊 】": sub_text = "神明不認同，建議重新思考。"
            
            sub_surf = font_ui.render(sub_text, True, (220, 220, 220))
            screen.blit(sub_surf, (sub_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 160))))
            
            # 3. 【調整】重來提示：改用 font_small 縮小，並利用 topright 定位在視窗右上角
            retry_surf = font_small.render("按下 [ 空白鍵 ] 重新收回手中", True, (140, 140, 140))
            retry_rect = retry_surf.get_rect(topright=(SCREEN_WIDTH - 30, 30))
            screen.blit(retry_surf, retry_rect.topleft)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()