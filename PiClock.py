#!/usr/bin/env python
from appbase import AppBase
from rgbmatrix import graphics
import requests
import datetime
import time
import random
import math

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
TEST_MODE = True  
API_KEY = 'YOUR_OPENWEATHER_KEY_HERE'
LAT = "29.8732" 
LON = "-95.2635"

class PiClock(AppBase):
    def __init__(self, *args, **kwargs):
        super(PiClock, self).__init__(*args, **kwargs)
        self.currentTemp = "72"
        self.currentIconCode = "01d"
        self.currentDesc = "Loading..."
        self.currentLocation = "Houston"
        self.callTimer = datetime.datetime.now()
        
        # --- AIRPLANE INIT ---
        self.active_planes = []
        self.next_spawn_time = time.time() + 5
        
        # --- STAR & SHOOTING STAR INIT ---
        self.stars = [{'x': random.randint(0, 63), 'y': random.randint(0, 32), 'offset': random.random() * 6.28} for _ in range(18)]
        self.ss_active = False
        self.ss_x, self.ss_y, self.ss_speed = -10.0, 0.0, 0.0
        self.next_ss_time = time.time() + 30

        # Fonts
        self.tmmFont = graphics.Font()
        self.tmmFont.LoadFont("./fonts/9x18.bdf")
        self.smmFont = graphics.Font()
        self.smmFont.LoadFont("./fonts/4x6.bdf")
        self.cmmFont = graphics.Font()
        self.cmmFont.LoadFont("./fonts/5x7.bdf")
        
        self.scroll_pos = 0
        self.last_scroll_update = time.time()

    def lerp_color(self, c1, c2, factor):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3))

    def get_time_factor(self):
        now = datetime.datetime.now()
        hour = now.hour + now.minute / 60.0
        if 6 <= hour < 8: return (hour - 6) / 2.0
        if 8 <= hour < 18: return 1.0
        if 18 <= hour < 20: return 1.0 - (hour - 18) / 2.0
        return 0.0

    def get_temp_color(self):
        try:
            temp = int(self.currentTemp)
            if temp <= 32: return (0, 100, 255)   
            if temp <= 60: return (0, 180, 180)   
            if temp <= 80: return (0, 180, 0)     
            if temp <= 95: return (255, 100, 0)   
            return (200, 0, 0)                    
        except: return (200, 200, 200)

    def get_seasonal_clock_color(self):
        month = datetime.datetime.now().month
        if month in [12, 1, 2]: return (100, 150, 255) 
        if month in [3, 4, 5]: return (50, 200, 50)     
        if month in [6, 7, 8]: return (255, 200, 0)   
        return (255, 100, 0)                                 

    def get_condition_color(self, code):
        grp = code[:2]
        if grp == "01": return (255, 230, 150)   
        if grp == "02": return (200, 220, 255)  
        if grp in ["03", "04"]: return (150, 150, 160)
        if grp in ["09", "10"]: return (100, 150, 255)
        if grp == "11": return (200, 100, 255)   
        if grp == "13": return (200, 230, 255)
        return (150, 150, 160)

    def getData(self):
        self.callTimer = datetime.datetime.now() + datetime.timedelta(minutes=10)
        try:
            r = requests.get("https://api.openweathermap.org/data/2.5/weather", 
                             params={'lat': LAT, 'lon': LON, 'appid': API_KEY, 'units': 'imperial'}, timeout=10)
            data = r.json()
            self.currentTemp = str(int(data['main']['temp']))
            self.currentIconCode = data['weather'][0]['icon']
            self.currentDesc = data['weather'][0]['description'].capitalize()
            self.currentLocation = "Houston"
            self.scroll_pos = 0 
        except: pass

    def spawn_plane(self):
        direction = random.choice([-1, 1]) 
        start_x = -15.0 if direction == 1 else 70.0
        drift = random.uniform(-0.05, 0.05) 
        
        self.active_planes.append({
            'x': start_x, 
            'y': random.uniform(5.0, 25.0),
            'dir': direction, 
            'speed': random.uniform(0.2, 0.45), 
            'drift': drift,
            'strobe_type': random.choice([(255, 0, 0), (255, 255, 255)])
        })

    def draw_mini_cloud(self, canvas, x, y, c1, c2):
        pixels = [(2,0,c1),(3,0,c1),(4,0,c1),(1,1,c1),(2,1,c1),(3,1,c1),(4,1,c1),(5,1,c1),(0,2,c2),(1,2,c2),(2,2,c2),(3,2,c2),(4,2,c2),(5,2,c2),(6,2,c2)]
        for dx, dy, col in pixels:
            if 0 <= x+dx < 64 and 0 <= y+dy < 64:
                canvas.SetPixel(int(x+dx), int(y+dy), *col)

    def draw_cloud_shape(self, canvas, x, y, c1, c2):
        circles = [(6,6,4,c1), (11,8,3,c1), (3,9,3,c2), (8,10,4,c2)]
        for cx, cy, r, col in circles:
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    if dx*dx + dy*dy <= r*r:
                        if 0 <= x+cx+dx < 64 and 0 <= y+cy+dy < 64:
                            canvas.SetPixel(x+cx+dx, y+cy+dy, *col)

    def draw_massive_weather_icon(self, canvas, x, y, code, factor):
        grp = code[:2]
        now = datetime.datetime.now()
        current_hour = now.hour + now.minute / 60.0
        
        is_actually_night = (current_hour >= 20.0 or current_hour < 6.0)
        is_day = "d" in code and not is_actually_night
        t = time.time()
        
        # --- ORBIT POSITIONING (The path they all follow) ---
        if 6.0 <= current_hour < 20.0:
            progress = (current_hour - 6.0) / 14.0
            target_x = int(progress * 64) - 4
            target_y = int(22 - (20 * math.sin(math.pi * progress)))
        else:
            if current_hour >= 20.0: progress = (current_hour - 20.0) / 10.0 
            else: progress = (current_hour + 4.0) / 10.0
            target_x = int(progress * 64) - 4
            target_y = int(18 - (15 * math.sin(math.pi * progress)))

        # --- 1. SUN / MOON / PARTLY CLOUDY (STAYS THE SAME) ---
        if grp in ["01", "02"]:
            if is_day:
                step = int(t * 8)
                sun_pixels = [(1,0),(2,0),(3,0),(0,1),(1,1),(2,1),(3,1),(4,1),(0,2),(1,2),(2,2),(3,2),(4,2),(0,3),(1,3),(2,3),(3,3),(4,3),(1,4),(2,4),(3,4)]
                sun_rays = [(2,-2),(2,6),(-2,2),(6,2),(-1,-1),(5,-1),(-1,5),(5,5)]
                for px, py in sun_pixels + sun_rays:
                    shm = 180 + ((step * 2 + px + py) % 8 * 10)
                    if 0 <= target_x+px < 64 and 0 <= target_y+py < 64:
                        canvas.SetPixel(target_x+px, target_y+py, shm, int(shm * 0.75), 0)
                if grp == "02":
                    self.draw_mini_cloud(canvas, target_x + 4, target_y + 2, (240,240,240), (160,160,160))
            else:
                day_of_year = now.timetuple().tm_yday
                phase = ((day_of_year - 6) % 29.53) / 29.53 
                for dx in range(8):
                    for dy in range(8):
                        x_rel, y_rel = (dx - 4) / 3.5, (dy - 4) / 3.5
                        dist = (x_rel**2 + y_rel**2)**0.5
                        if dist < 1.0:
                            angle = math.cos(math.pi * 2 * phase)
                            if x_rel * angle + (1.0 - x_rel**2)**0.5 * (1.0 if phase > 0.5 else -1.0) > 0:
                                if 0 <= target_x+dx < 64 and 0 <= target_y+dy < 64:
                                    canvas.SetPixel(target_x+dx, target_y+dy, 210, 210, 230)

        # --- 2. HEAVY WEATHER (CLOUDY, RAIN, SNOW, STORM) ---
        elif grp in ["03", "04", "09", "10", "11", "13"]:
            c1, c2 = (140, 140, 150), (90, 90, 100) # Overcast
            if grp in ["09", "10", "11"]: c1, c2 = (80, 80, 90), (40, 40, 50) # Dark Storm
            if grp == "13": c1, c2 = (200, 200, 210), (140, 140, 150) # Snow
            
            # --- SPACED OUT CLUSTER ---
            # Increased offsets to separate the clouds
            # Format: (horizontal_offset, vertical_offset)
            spaced_offsets = [
                (-12, 2),  # Far Left & slightly lower
                (0, -5),   # Center & higher
                (12, 2)    # Far Right & slightly lower
            ]
            
            for ox, oy in spaced_offsets:
                # Use draw_cloud_shape for the sun-sized heavy clouds
                self.draw_cloud_shape(canvas, target_x + ox - 4, target_y + oy - 4, c1, c2)

            # Lightning for Storms (Strikes from any of the three clouds)
            if grp == "11" and (int(t * 4) % 12 == 0):
                strike_ox, strike_oy = random.choice(spaced_offsets)
                for bx, by in [(0,0), (1,1), (0,2), (1,3)]:
                    lx, ly = target_x + strike_ox + bx, target_y + strike_oy + 8 + by
                    if 0 <= lx < 64 and 0 <= ly < 64:
                        canvas.SetPixel(lx, ly, 255, 255, 100)

        # --- 3. FOG / WIND (STAYS THE SAME) ---
        elif grp == "50":
            w_c = (150, 180, 200)
            for i, ly in enumerate([10, 18, 26]):
                offset = int(t * (10 + i * 5)) % 64
                for dx in range(12):
                    canvas.SetPixel((offset + dx) % 64, ly, *w_c)

    def draw_houston(self, canvas, factor):
        t = time.time()
        grp = self.currentIconCode[:2]
        is_foggy = (grp == "50")
        is_stormy = grp in ["09", "10", "11"]
        is_cloudy = grp in ["02", "03", "04"]
        is_night_mode = (factor < 0.4 or is_stormy)

        now = datetime.datetime.now()
        hr = now.hour + now.minute / 60.0
        glow_factor = 0.0
        if 5.5 <= hr <= 8.0: glow_factor = 0 - abs(hr - 6.5) / 1.5
        elif 18.0 <= hr <= 20.5: glow_factor = 0 - abs(hr - 19.5) / 1.5
        glow_factor = max(0, min(0.6, glow_factor))

        day_sky, night_sky, glow_color = (25, 75, 150), (0, 0, 0), (255, 100, 40)
        if is_cloudy: day_sky = (27, 67, 107)
        elif is_stormy: day_sky = (30, 35, 45)
        elif is_foggy: day_sky = (100, 110, 120)

        base_sky = self.lerp_color(night_sky, day_sky, factor)
        final_sky = base_sky if (is_stormy or is_foggy) else self.lerp_color(base_sky, glow_color, glow_factor * 0.6)
        
        for x in range(64):
            for y in range(64): 
                horizon_boost = max(0, (y - 20) // 10) if not is_night_mode else 0
                canvas.SetPixel(x, y, min(255, final_sky[0] + horizon_boost * 5), min(255, final_sky[1] + horizon_boost * 3), final_sky[2])

        if factor < 0.3 and not is_stormy:
            for s in self.stars:
                lum = int(100 + 155 * (0.5 + 0.5 * math.sin(t * 2 + s['offset'])))
                canvas.SetPixel(s['x'], s['y'], lum, lum, lum)
            if not self.ss_active and t > self.next_ss_time:
                self.ss_active, self.ss_x, self.ss_y = True, random.randint(0, 40), random.randint(0, 15)
                self.ss_speed, self.next_ss_time = random.uniform(1.5, 3.0), t + random.randint(20, 60)
            if self.ss_active:
                self.ss_x += self.ss_speed
                self.ss_y += (self.ss_speed * 0.5)
                if 0 <= self.ss_x < 64 and 0 <= self.ss_y < 64:
                    canvas.SetPixel(int(self.ss_x), int(self.ss_y), 255, 255, 255)
                    if 0 <= self.ss_x-1 < 64: canvas.SetPixel(int(self.ss_x-1), int(self.ss_y), 150, 150, 150)
                else: self.ss_active = False

        buildings = [(1, 10, 38, 'BofA'), (13, 8, 42, 'BgR'), (23, 11, 52, 'Ch'), (35, 10, 38, 'Ws'), (46, 9, 44, 'Pz'), (56, 10, 32, 'BgL'), (38, 27, 10, 'Tc')]

        for xs, w, h, btype in buildings:
            day_gray, night_gray = (100, 105, 115), (20, 20, 30)
            if btype in ['BofA', 'BgR']: day_gray, night_gray = (135, 85, 75), (35, 22, 22)
            if btype in ['BgL', 'BgR']: day_gray, night_gray = (90, 95, 105), (15, 15, 25)
            base_c = self.lerp_color(night_gray, day_gray, factor)
            high_c = self.lerp_color((day_gray[0]+25, day_gray[1]+25, day_gray[2]+30), (night_gray[0]+12, night_gray[1]+12, night_gray[2]+15), 1.0 - factor)

            for x in range(xs, xs + w):
                if not (0 <= x < 64): continue
                rel_x, curr_top = x - xs, 64 - h
                
                if btype == 'Tc':
                    dome_y = (64 - h) - (5 * math.sin((rel_x / (w-1)) * math.pi))
                    dome_c = (210, 0, 0) if is_night_mode else base_c
                    if is_night_mode and is_foggy: dome_c = self.lerp_color(dome_c, final_sky, 0.5)
                    for dy in range(int(dome_y), 64-h): canvas.SetPixel(x, dy, *dome_c)
                    for by in range(64-h, 64):
                        pix_c = high_c if rel_x < 2 else base_c
                        if is_night_mode:
                            lx, ly = rel_x, 64 - by 
                            is_letter = (5<=ly<=9) and ((2<=lx<=4 and (ly==9 or lx==3)) or (6<=lx<=8 and (ly in [5,9] or lx in [6,8])) or (10<=lx<=12 and ((ly>=8 and lx!=11) or (lx==11 and ly<=8))) or (14<=lx<=16 and (ly in [5,9] or lx in [14,16])) or (18<=lx<=20 and (ly==9 or lx==19)) or (22<=lx<=24 and (ly==9 or lx in [22,24] or ly==7)))
                            if is_letter: pix_c = (int(180+75*math.sin(t*3)), 0, 0)
                        canvas.SetPixel(x, by, *pix_c)
                    continue 

                if btype == 'Ws' and rel_x == 3:
                    for ay in range(64-49, int(curr_top)): canvas.SetPixel(x, ay, *high_c)
                    if is_night_mode: canvas.SetPixel(x, 64-49, int(127+127*math.sin((t*4)+3.14)), 0, 0)

                if btype == 'Pz':
                    if rel_x < 2 or rel_x > 6: curr_top += 5
                    elif rel_x == 2 or rel_x == 6: curr_top += 3
                elif btype == 'BofA':
                    if rel_x < 3: curr_top += 8
                    elif rel_x < 6: curr_top += 4

                for y in range(int(curr_top), 64):
                    pix_c = high_c if rel_x < 2 else base_c
                    if is_night_mode and (0 < rel_x < w - 1) and (x % 3 == 0) and (y % 4 == 0) and y > curr_top + 6:
                        pix_c = self.lerp_color((180, 160, 60), final_sky, 0.4) if is_foggy else (180, 160, 60)
                    canvas.SetPixel(x, y, *pix_c)

                if btype == 'Ch' and rel_x == 1 and is_night_mode:
                    canvas.SetPixel(x, int(curr_top) - 1, int(127+127*math.sin(t*4)), 0, 0)

        if grp in ["09", "10", "11"]:
            for rx in range(0, 64, 4): canvas.SetPixel(rx, int(t*30+(rx*7))%64, 100, 150, 255)
        elif grp == "13":
            for sx in range(0, 64, 6): canvas.SetPixel((sx+int(math.sin(t+sx)*3))%64, int(t*8+(sx*3))%64, 220, 230, 255)

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        test_data = [("01d","Sunny"), ("02d","Partly Cloudy"), ("03d","Overcast"), ("50d","Windy"), ("11d","Storm"), ("13d","Snow"), ("09d","Rain"), ("01n","Night")]
        self.test_idx, self.test_timer = 0, time.time()
        
        while True:
            offscreen_canvas.Clear()
            now, t = datetime.datetime.now(), time.time()
            if TEST_MODE:
                factor = 0.0 if "n" in self.currentIconCode else 1.0
                if t - self.test_timer > 6:
                    self.test_idx = (self.test_idx + 1) % len(test_data)
                    self.currentIconCode, self.currentDesc = test_data[self.test_idx]
                    self.test_timer = t
            else:
                factor = self.get_time_factor()
                if now >= self.callTimer: self.getData()

            self.draw_houston(offscreen_canvas, factor)
            self.draw_massive_weather_icon(offscreen_canvas, 0, 0, self.currentIconCode, factor)

            if t > self.next_spawn_time:
                self.spawn_plane()
                self.next_spawn_time = t + random.randint(8, 20)

            for p in self.active_planes[:]:
                p['x'] += (p['dir'] * p['speed'])
                p['y'] += p['drift']
                if 0 <= p['y'] < 64 and 0 <= p['x'] < 64:
                    offscreen_canvas.SetPixel(int(p['x']), int(p['y']), 180, 180, 180)
                    if int(t * 5) % 2 == 0:
                        sx = int(p['x']) - p['dir']
                        if 0 <= sx < 64: offscreen_canvas.SetPixel(sx, int(p['y']), *p['strobe_type'])
                if (p['dir'] == 1 and p['x'] > 80) or (p['dir'] == -1 and p['x'] < -20): self.active_planes.remove(p)

            ct = int(t) % 60
            if ct < 3:
                graphics.DrawText(offscreen_canvas, self.cmmFont, 34, 17, graphics.Color(*self.get_seasonal_clock_color()), now.strftime("%H:%M"))
                graphics.DrawText(offscreen_canvas, self.cmmFont, 29, 25, graphics.Color(3, 123, 252), self.currentLocation)
            elif 3 <= ct < 6:
                tc = self.get_temp_color()
                graphics.DrawText(offscreen_canvas, self.cmmFont, 38, 18, graphics.Color(*tc), self.currentTemp)
                tw = sum([self.tmmFont.CharacterWidth(ord(c)) for c in self.currentTemp])
                for dx in range(2):
                    for dy in range(2): offscreen_canvas.SetPixel(29 + tw + 1 + dx, 12 + dy, *tc)
            elif 6 <= ct < 9:
                words = self.currentDesc.split()
                lines = [" ".join(words[:len(words)//2]), " ".join(words[len(words)//2:])] if len(words) > 1 else [self.currentDesc, ""]
                for i, txt in enumerate(lines):
                    if txt: graphics.DrawText(offscreen_canvas, self.smmFont, 27, 17 + (i * 7), graphics.Color(*self.get_condition_color(self.currentIconCode)), txt)

            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(0.02)

if __name__ == "__main__":
    PiClock().process()