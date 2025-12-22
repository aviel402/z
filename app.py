import random
import uuid
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "rpg_legend_secret"

# מסד נתונים פנימי (בזיכרון ה-RAM)
players = {}

# --- מחלקות המשחק ---

class Enemy:
    def __init__(self, name, level):
        self.name = name
        self.level = level
        self.max_hp = 20 + (level * 10)
        self.hp = self.max_hp
        self.damage = 3 + (level * 2)
        self.xp_reward = 20 * level
        self.gold_reward = random.randint(10, 25) * level

class Player:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.name = "גיבור"
        self.hp = 100
        self.max_hp = 100
        self.level = 1
        self.xp = 0
        self.next_level_xp = 100
        self.gold = 50
        self.damage = 10
        self.potions = 3
        self.location = "town"  # town, forest, cave
        self.in_combat = False
        self.current_enemy = None
        self.weapon_level = 1
        self.logs = ["הגעת לממלכה. המטרה: הבס את אביר הצללים במערה."]

    def add_log(self, text):
        self.logs.insert(0, text)
        if len(self.logs) > 5:
            self.logs.pop()

    def heal(self):
        if self.potions > 0:
            if self.hp >= self.max_hp:
                self.add_log("החיים שלך מלאים!")
                return
            heal_amount = 40
            self.hp = min(self.max_hp, self.hp + heal_amount)
            self.potions -= 1
            self.add_log(f"שתית שיקוי. החיים עלו ל-{self.hp}. נותרו {self.potions} שיקויים.")
        else:
            self.add_log("אין לך שיקויים! לך לחנות.")

    def gain_xp(self, amount):
        self.xp += amount
        self.add_log(f"קיבלת {amount} ניסיון!")
        if self.xp >= self.next_level_xp:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.xp = 0
        self.next_level_xp = int(self.next_level_xp * 1.5)
        self.max_hp += 20
        self.hp = self.max_hp
        self.damage += 5
        self.add_log(f"🎉 עלית לרמה {self.level}! כוח וחיים גדלו.")

# --- ממשק HTML ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RPG Legends</title>
    <style>
        body {
            background-color: #1a1a1d; color: #c5c6c7; font-family: 'Segoe UI', Tahoma, sans-serif;
            margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; min-height: 100vh;
        }
        .game-card {
            background: #2b2e31; width: 100%; max-width: 500px; padding: 15px; border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.5); border-top: 4px solid #66fcf1;
        }
        h2, h3 { margin: 5px 0; color: #66fcf1; text-align: center; }
        
        /* Stats Bar */
        .stats { display: flex; justify-content: space-between; background: #0b0c10; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }
        .stat-item { text-align: center; }
        .hp-val { color: #ff4d4d; font-weight: bold; }
        .gold-val { color: #ffd700; font-weight: bold; }
        
        /* HP Bar */
        .hp-container { background: #444; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 2px; }
        .hp-fill { height: 100%; background: #ff4d4d; width: {{ (p.hp / p.max_hp) * 100 }}%; transition: width 0.3s; }

        /* Game Screen */
        .scene {
            background: url('{{ bg_image }}') no-repeat center; 
            background-size: cover; background-color: #222;
            height: 150px; border-radius: 8px; margin-bottom: 15px; position: relative;
            display: flex; justify-content: center; align-items: center; font-size: 40px; text-shadow: 0 0 10px black;
        }
        .scene-text { position: absolute; bottom: 5px; font-size: 14px; background: rgba(0,0,0,0.7); padding: 2px 8px; border-radius: 4px; color: white;}

        /* Logs */
        .logs { background: #111; color: #45a29e; padding: 10px; height: 80px; overflow-y: auto; border-radius: 5px; margin-bottom: 15px; font-size: 13px; font-family: monospace; border: 1px solid #333; }
        .log-line { margin-bottom: 4px; border-bottom: 1px solid #222; }

        /* Actions Grid */
        .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button {
            background: #1f2833; border: 1px solid #45a29e; color: white; padding: 15px;
            font-size: 16px; cursor: pointer; border-radius: 8px; font-weight: bold; transition: 0.2s;
        }
        button:hover { background: #45a29e; color: black; }
        button:disabled { opacity: 0.5; cursor: not-allowed; border-color: #555; }
        
        .combat-btn { background: #3e1212; border-color: #ff4d4d; }
        .heal-btn { background: #0f3d0f; border-color: #4dff4d; }
        .shop-btn { background: #3d3d0f; border-color: #ffff4d; }

    </style>
</head>
<body>

    <div class="game-card">
        <h2>⚔️ ממלכת הצללים 🛡️</h2>
        
        <div class="stats">
            <div class="stat-item">❤️ {{ p.hp }}/{{ p.max_hp }}<div class="hp-container"><div class="hp-fill"></div></div></div>
            <div class="stat-item">⭐ רמה {{ p.level }}</div>
            <div class="stat-item">💰 {{ p.gold }}</div>
            <div class="stat-item">🧪 {{ p.potions }}</div>
        </div>

        <!-- The Visual Scene -->
        <div class="scene" style="background: {{ bg_color }}">
            {{ emoji_icon }}
            <div class="scene-text">{{ location_name }}</div>
        </div>

        <div class="logs">
            {% for log in p.logs %}
                <div class="log-line">➜ {{ log }}</div>
            {% endfor %}
        </div>

        <div class="actions">
            {% if p.hp <= 0 %}
                <!-- מסך מוות -->
                <button onclick="window.location.href='/restart'" style="grid-column: span 2; background: red;">☠️ מתת! התחל מחדש</button>
            
            {% elif p.in_combat %}
                <!-- מצב קרב -->
                <button class="combat-btn" onclick="window.location.href='/action/attack'">⚔️ התקפה</button>
                <button class="heal-btn" onclick="window.location.href='/action/heal'">🧪 שתה שיקוי</button>
                <button onclick="window.location.href='/action/flee'">🏃 ברח (אבד זהב)</button>
            
            {% elif p.location == 'town' %}
                <!-- עיר -->
                <button onclick="window.location.href='/travel/forest'">🌲 צא ליער (רמות 1-3)</button>
                <button style="border-color: red" onclick="window.location.href='/travel/cave'">💀 למערת הבוס (רמה 5+)</button>
                <button class="shop-btn" onclick="window.location.href='/shop/buy_potion'">🧪 קנה שיקוי (30 💰)</button>
                <button class="shop-btn" onclick="window.location.href='/shop/upgrade_weapon'">⚔️ שדרג נשק (100 💰)</button>
                <button class="heal-btn" onclick="window.location.href='/action/inn'">🏨 פונדק - שינה מלאה (10 💰)</button>

            {% elif p.location == 'forest' or p.location == 'cave' %}
                <!-- בחוץ בחיפוש -->
                <button class="combat-btn" onclick="window.location.href='/action/explore'">🔍 סייר באזור (חפש אויבים)</button>
                <button onclick="window.location.href='/travel/town'">🏠 חזור לעיר (בטוח)</button>
            {% endif %}
        </div>
    </div>

</body>
</html>
"""

# --- פונקציות עזר לשרת ---

def get_player():
    # בודק לפי ה-IP או יוצר משתמש זמני בדפדפן אם הוא חדש
    # (לשם הפשטות במשחק Web רגיל נשתמש בעוגיה, כאן משתמש בזיכרון)
    uid = request.cookies.get('rpg_uid')
    if uid and uid in players:
        return players[uid]
    return None

def create_new_player():
    new_p = Player()
    players[new_p.id] = new_p
    return new_p

# --- Routes ---

@app.route('/')
def home():
    p = get_player()
    if not p:
        p = create_new_player()
        resp = redirect(url_for('home'))
        resp.set_cookie('rpg_uid', p.id)
        return resp

    # הגדרות תצוגה
    bg_color = "#333"
    icon = "🏠"
    loc_name = "הכפר הבטוח"

    if p.in_combat:
        bg_color = "#4a1c1c"
        icon = f"😈 {p.current_enemy.name} (רמה {p.current_enemy.level})"
        loc_name = "זירת קרב"
    elif p.location == "forest":
        bg_color = "#1b4d3e"
        icon = "🌲🌲🌲"
        loc_name = "היער האפל"
    elif p.location == "cave":
        bg_color = "#2c2c2c"
        icon = "🦇🏔️🦇"
        loc_name = "מערת האבדון"

    return render_template_string(HTML_TEMPLATE, p=p, bg_color=bg_color, emoji_icon=icon, location_name=loc_name)

@app.route('/restart')
def restart():
    # מוחק דמות ויוצר חדשה
    p = create_new_player()
    resp = redirect(url_for('home'))
    resp.set_cookie('rpg_uid', p.id)
    return resp

@app.route('/travel/<destination>')
def travel(destination):
    p = get_player()
    if not p or p.hp <= 0 or p.in_combat: return redirect('/')
    
    if destination == "cave" and p.level < 3:
        p.add_log("השומר במערה עוצר אותך: 'רק לוחמים ברמה 3 ומעלה!'")
    else:
        p.location = destination
        p.add_log(f"עברת ל-{destination}.")
    
    return redirect('/')

@app.route('/shop/<action>')
def shop(action):
    p = get_player()
    if not p or p.hp <= 0 or p.in_combat or p.location != "town": return redirect('/')

    if action == "buy_potion":
        if p.gold >= 30:
            p.gold -= 30
            p.potions += 1
            p.add_log("קנית שיקוי חיים.")
        else:
            p.add_log("אין לך מספיק זהב (30).")
    
    elif action == "upgrade_weapon":
        cost = p.weapon_level * 100
        if p.gold >= cost:
            p.gold -= cost
            p.damage += 5
            p.weapon_level += 1
            p.add_log(f"שיפרת את הנשק! נזק כעת: {p.damage}")
        else:
            p.add_log(f"אין מספיק זהב לשדרוג (צריך {cost}).")

    return redirect('/')

@app.route('/action/<act>')
def perform_action(act):
    p = get_player()
    if not p: return redirect('/')

    # ---- לינה בפונדק ----
    if act == "inn" and p.location == "town":
        if p.gold >= 10:
            p.gold -= 10
            p.hp = p.max_hp
            p.add_log("ישנת בפונדק. החיים מלאים לגמרי! 💤")
        else:
            p.add_log("אין לך מספיק כסף ללינה (10).")
    
    # ---- שיקוי (בכל מצב) ----
    elif act == "heal":
        p.heal()
        # אם בקרב, האויב תוקף אחרי השיקוי
        if p.in_combat:
            enemy_turn(p)

    # ---- סייר וחפש אויבים (Exploration) ----
    elif act == "explore" and not p.in_combat:
        if p.hp <= 0: return redirect('/')
        
        # 30% סיכוי לא למצוא כלום
        if random.random() > 0.7:
            p.add_log("שקט... אין אויבים באזור.")
        else:
            start_combat(p)

    # ---- קרב: התקפה ----
    elif act == "attack" and p.in_combat:
        enemy = p.current_enemy
        
        # תור השחקן
        # קריטיקל היט (סיכוי קטן)
        is_crit = random.random() > 0.8
        dmg = p.damage * 2 if is_crit else p.damage
        enemy.hp -= dmg
        
        log = f"תקפת את {enemy.name} וגרמת {dmg} נזק!"
        if is_crit: log += " (פגיעה קריטית!)"
        p.add_log(log)

        if enemy.hp <= 0:
            # ניצחון
            p.in_combat = False
            p.gold += enemy.gold_reward
            p.gain_xp(enemy.xp_reward)
            p.add_log(f"🏆 ניצחת! קיבלת {enemy.gold_reward} זהב.")
            
            if enemy.name == "אביר הצללים":
                p.add_log("🔥🔥🔥 ניצחת את המשחק!!! הפכת לאגדה! 🔥🔥🔥")
        else:
            # תור האויב
            enemy_turn(p)

    # ---- קרב: בריחה ----
    elif act == "flee" and p.in_combat:
        loss = int(p.gold * 0.2)
        p.gold -= loss
        p.in_combat = False
        p.add_log(f"ברחת כל עוד נפשך בך... הפלת {loss} מטבעות תוך כדי ריצה.")

    return redirect('/')

# --- לוגיקה קרבית ---

def start_combat(p):
    if p.location == "forest":
        enemies = [("זאב רעב", 1), ("שדון יער", 2), ("עכביש ענק", 3)]
    elif p.location == "cave":
        enemies = [("עטלף ערפד", 4), ("שומר שלד", 5), ("אביר הצללים", 10)] # הבוס הוא רמה 10
    
    choice = random.choice(enemies)
    # בדיקה מיוחדת לבוס - מופיע רק אם שחקן חזק, אחרת עטלף
    if choice[0] == "אביר הצללים" and p.level < 6:
        choice = ("שומר שלד חזק", 5)

    p.current_enemy = Enemy(choice[0], choice[1])
    p.in_combat = True
    p.add_log(f"⚠️ {p.current_enemy.name} (רמה {p.current_enemy.level}) קפץ עליך!")

def enemy_turn(p):
    enemy = p.current_enemy
    damage = max(1, enemy.damage - random.randint(0, 2)) # קצת רנדומליות
    p.hp -= damage
    p.add_log(f"ה-{enemy.name} תקף אותך ב-{damage} נזק.")
    
    if p.hp <= 0:
        p.add_log("☠️ הובסת בקרב...")
        p.in_combat = False # המשחק יראה כפתור RESTART במסך הבא

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)