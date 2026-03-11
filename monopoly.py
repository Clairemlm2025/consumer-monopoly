import streamlit as st
import random
import json
import os
import tempfile
import threading
import time
from datetime import datetime

st.set_page_config(page_title="消費者行為大富翁", layout="wide")

# =========================================================
# 檔案設定
# =========================================================
STATE_FILE = "game_state.json"
STATE_LOCK = threading.Lock()

# =========================================================
# 讀取外部資料
# =========================================================
with open("board.json", "r", encoding="utf-8") as f:
    BOARD = json.load(f)

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("chance_cards.json", "r", encoding="utf-8") as f:
    CARD_DATA = json.load(f)
    CHANCE_CARDS = CARD_DATA["chance"]
    FATE_CARDS = CARD_DATA["fate"]

# =========================================================
# 常數
# =========================================================
NUM_GROUPS = 13
START_MONEY = 2000
PASS_START_BONUS = 200

GROUP_COLORS = [
    "#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa",
    "#fb8c00", "#00acc1", "#d81b60", "#6d4c41", "#546e7a",
    "#3949ab", "#7cb342", "#c0ca33"
]

GROUP_ICONS = [
    "🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "🔷",
    "🌸", "🟤", "⚫", "💎", "🍏", "⭐"
]

# =========================================================
# 工具函式
# =========================================================
def atomic_write_json(path, data):
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)

def make_session_id():
    return f"{time.time()}_{random.randint(1000,9999)}"

def default_state():
    return {
        "positions": [0] * NUM_GROUPS,
        "money": [START_MONEY] * NUM_GROUPS,
        "owner": [None] * len(BOARD),
        "turn": 0,
        "current_group": 0,
        "phase": "roll",   # roll / answer
        "current_question": None,
        "current_space": None,
        "last_roll": None,
        "last_message": "遊戲開始，請第 1 組擲骰。",
        "group_locks": {},  # {"0": "session_xxx"}
        "log": [],
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def load_state():
    with STATE_LOCK:
        if not os.path.exists(STATE_FILE):
            state = default_state()
            atomic_write_json(STATE_FILE, state)
            return state
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_state(state):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with STATE_LOCK:
        atomic_write_json(STATE_FILE, state)

def reset_game():
    state = default_state()
    save_state(state)
    return state

def add_log(state, text):
    ts = datetime.now().strftime("%H:%M:%S")
    state["log"].insert(0, f"[{ts}] {text}")
    state["log"] = state["log"][:60]

def next_group(g):
    return (g + 1) % NUM_GROUPS

def owned_count(state, g):
    return sum(1 for x in state["owner"] if x == g)

def draw_question():
    return random.choice(QUESTIONS)

def draw_card(card_type):
    if card_type == "chance":
        return random.choice(CHANCE_CARDS)
    return random.choice(FATE_CARDS)

# =========================================================
# 使用者 session
# =========================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = make_session_id()

if "player_group" not in st.session_state:
    st.session_state.player_group = None

session_id = st.session_state.session_id

# =========================================================
# 顯示用
# =========================================================
def render_cell_html(idx, state):
    space = BOARD[idx]
    owner = state["owner"][idx]
    tokens_here = [g for g, p in enumerate(state["positions"]) if p == idx]

    bg = "#ffffff"
    border = "#cfd8dc"

    if space["type"] == "start":
        bg = "#fff8e1"
        border = "#ffb300"
    elif space["type"] == "chance":
        bg = "#e3f2fd"
        border = "#42a5f5"
    elif space["type"] == "fate":
        bg = "#fce4ec"
        border = "#ec407a"
    else:
        bg = "#f8f9fa"

    owner_label = ""
    if owner is not None:
        owner_label = f'<div style="font-size:11px;font-weight:700;color:{GROUP_COLORS[owner]};">🚩 第{owner+1}組</div>'

    toll_line = ""
    if space["type"] == "brand":
        toll_line = f'<div style="font-size:11px;color:#455a64;">過路費 ${space["toll"]}</div>'

    token_html = "".join(
        f'<span style="margin-right:3px;font-size:16px;">{GROUP_ICONS[g]}</span>'
        for g in tokens_here
    )

    return f"""
    <div style="
        height:110px;
        border:2px solid {border};
        background:{bg};
        border-radius:12px;
        padding:8px;
        box-sizing:border-box;
        overflow:hidden;
        display:flex;
        flex-direction:column;
        justify-content:flex-start;
    ">
        <div style="font-size:11px;color:#607d8b;font-weight:700;">#{idx}</div>
        <div style="font-size:15px;font-weight:800;line-height:1.15;margin:2px 0 4px 0;">
            {space["name"]}
        </div>
        <div style="font-size:11px;color:#78909c;">{space["category"]}</div>
        {toll_line}
        {owner_label}
        <div style="margin-top:auto;min-height:22px;white-space:nowrap;overflow:hidden;">
            {token_html}
        </div>
    </div>
    """

def render_board(state):
    size = 11
    coords = []

    for c in range(size):
        coords.append((0, c))
    for r in range(1, size - 1):
        coords.append((r, size - 1))
    for c in range(size - 1, -1, -1):
        coords.append((size - 1, c))
    for r in range(size - 2, 0, -1):
        coords.append((r, 0))

    grid = [["" for _ in range(size)] for _ in range(size)]
    for i in range(len(BOARD)):
        r, c = coords[i]
        grid[r][c] = render_cell_html(i, state)

    center_html = """
    <div style="
        height:100%;
        border:2px dashed #90a4ae;
        border-radius:18px;
        background:linear-gradient(135deg,#fff3e0,#e3f2fd);
        display:flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        flex-direction:column;
        padding:20px;
        box-sizing:border-box;
    ">
        <div style="font-size:30px;font-weight:900;">🎲 消費者行為大富翁</div>
        <div style="font-size:15px;color:#455a64;margin-top:8px;">13組同步・固定過路費・品牌搶地</div>
    </div>
    """

    html = """
    <style>
    .board-wrap {
        display:grid;
        grid-template-columns: repeat(11, minmax(70px, 1fr));
        gap:8px;
        width:100%;
    }
    .board-center {
        grid-column:2 / span 9;
        grid-row:2 / span 9;
    }
    </style>
    <div class="board-wrap">
    """

    for r in range(size):
        for c in range(size):
            if 1 <= r <= 9 and 1 <= c <= 9:
                if r == 1 and c == 1:
                    html += f'<div class="board-center">{center_html}</div>'
                else:
                    continue
            else:
                html += grid[r][c] if grid[r][c] else "<div></div>"

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# =========================================================
# 遊戲流程
# =========================================================
def animate_dice():
    placeholder = st.empty()
    final_num = 1
    for _ in range(10):
        final_num = random.randint(1, 6)
        placeholder.markdown(
            f"<div style='font-size:42px;font-weight:900;text-align:center;'>🎲 {final_num}</div>",
            unsafe_allow_html=True
        )
        time.sleep(0.08)
    return final_num

def process_roll(state, group_idx):
    dice = animate_dice()
    old_pos = state["positions"][group_idx]
    new_pos = (old_pos + dice) % len(BOARD)

    if old_pos + dice >= len(BOARD):
        state["money"][group_idx] += PASS_START_BONUS
        add_log(state, f"第 {group_idx+1} 組通過起點，獲得 ${PASS_START_BONUS}")

    state["positions"][group_idx] = new_pos
    state["current_space"] = new_pos
    state["last_roll"] = dice

    space = BOARD[new_pos]

    # 先顯示棋子已到新位置，再判斷事件
    if space["type"] == "start":
        state["phase"] = "roll"
        state["current_group"] = next_group(group_idx)
        state["current_question"] = None
        msg = f"第 {group_idx+1} 組擲出 {dice} 點，停在起點。下一組：第 {state['current_group']+1} 組。"
        state["last_message"] = msg
        add_log(state, msg)
        return state

    if space["type"] == "chance":
        card = draw_card("chance")
        state["money"][group_idx] += card["money"]
        state["phase"] = "roll"
        state["current_group"] = next_group(group_idx)
        state["current_question"] = None
        sign = "+" if card["money"] >= 0 else ""
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【機會】。"
            f"{card['title']}：{card['text']}（{sign}${card['money']}）"
            f" 下一組：第 {state['current_group']+1} 組。"
        )
        state["last_message"] = msg
        add_log(state, msg)
        return state

    if space["type"] == "fate":
        card = draw_card("fate")
        state["money"][group_idx] += card["money"]
        state["phase"] = "roll"
        state["current_group"] = next_group(group_idx)
        state["current_question"] = None
        sign = "+" if card["money"] >= 0 else ""
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【命運】。"
            f"{card['title']}：{card['text']}（{sign}${card['money']}）"
            f" 下一組：第 {state['current_group']+1} 組。"
        )
        state["last_message"] = msg
        add_log(state, msg)
        return state

    owner = state["owner"][new_pos]

    # 空地：出題
    if owner is None:
        state["phase"] = "answer"
        state["current_question"] = draw_question()
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【{space['name']}】。"
            f" 此格未被佔領，請答題。答對可佔領，答錯支付固定過路費 ${space['toll']}。"
        )
        state["last_message"] = msg
        add_log(state, msg)
        return state

    # 自己的地
    if owner == group_idx:
        state["phase"] = "roll"
        state["current_group"] = next_group(group_idx)
        state["current_question"] = None
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到自己的【{space['name']}】。"
            f" 安全通過，下一組：第 {state['current_group']+1} 組。"
        )
        state["last_message"] = msg
        add_log(state, msg)
        return state

    # 別人的地：不能搶，直接付費
    toll = space["toll"]
    state["money"][group_idx] -= toll
    state["money"][owner] += toll
    state["phase"] = "roll"
    state["current_group"] = next_group(group_idx)
    state["current_question"] = None
    msg = (
        f"第 {group_idx+1} 組擲出 {dice} 點，來到第 {owner+1} 組已佔領的【{space['name']}】。"
        f" 不可再搶佔，直接支付過路費 ${toll}。下一組：第 {state['current_group']+1} 組。"
    )
    state["last_message"] = msg
    add_log(state, msg)
    return state

def process_answer(state, group_idx, selected_idx):
    q = state["current_question"]
    pos = state["current_space"]
    space = BOARD[pos]

    if selected_idx == q["answer"]:
        state["owner"][pos] = group_idx
        msg = (
            f"第 {group_idx+1} 組回答正確，成功佔領【{space['name']}】。"
            f" 理論概念：{q['concept']}。"
        )
    else:
        toll = space["toll"]
        state["money"][group_idx] -= toll
        correct = q["options"][q["answer"]]
        msg = (
            f"第 {group_idx+1} 組回答錯誤，支付固定過路費 ${toll}。"
            f" 正確答案：{correct}。理論概念：{q['concept']}。"
        )

    state["phase"] = "roll"
    state["current_group"] = next_group(group_idx)
    state["current_question"] = None
    state["current_space"] = None
    state["last_message"] = msg + f" 下一組：第 {state['current_group']+1} 組。"
    add_log(state, state["last_message"])
    return state

# =========================================================
# 載入狀態
# =========================================================
state = load_state()

# =========================================================
# 側邊欄：身份與組別鎖定
# =========================================================
with st.sidebar:
    st.header("玩家設定")
    role = st.radio("身份", ["老師 / 主控", "玩家"], index=1)

    if role == "玩家":
        current_player_group = st.session_state.player_group
        if current_player_group is None:
            choice = st.selectbox("選擇你的組別", list(range(NUM_GROUPS)), format_func=lambda x: f"第 {x+1} 組")
            if st.button("加入此組", use_container_width=True):
                state = load_state()
                lock = state["group_locks"].get(str(choice))
                if lock is None:
                    state["group_locks"][str(choice)] = session_id
                    save_state(state)
                    st.session_state.player_group = choice
                    st.success(f"已加入第 {choice+1} 組")
                    st.rerun()
                elif lock == session_id:
                    st.session_state.player_group = choice
                    st.success(f"已回到第 {choice+1} 組")
                    st.rerun()
                else:
                    st.error("這一組已經有其他帳號控制，不能加入。")
        else:
            st.success(f"你目前是第 {current_player_group+1} 組 {GROUP_ICONS[current_player_group]}")
            if st.button("退出本組", use_container_width=True):
                state = load_state()
                lock = state["group_locks"].get(str(current_player_group))
                if lock == session_id:
                    state["group_locks"].pop(str(current_player_group), None)
                    save_state(state)
                st.session_state.player_group = None
                st.rerun()

    st.markdown("---")
    st.caption(f"最後更新：{state['updated_at']}")
    if st.button("🔄 重新整理", use_container_width=True):
        st.rerun()

    if role == "老師 / 主控":
        st.markdown("---")
        if st.button("♻️ 重設整局遊戲", type="primary", use_container_width=True):
            state = reset_game()
            st.session_state.player_group = None
            st.success("遊戲已重設")
            st.rerun()

# =========================================================
# 權限判斷
# =========================================================
current_group = state["current_group"]
player_group = st.session_state.player_group

if role == "老師 / 主控":
    can_control = True
else:
    can_control = (player_group is not None and player_group == current_group)

# =========================================================
# 頂部資訊
# =========================================================
st.title("🎲 消費者行為大富翁")

c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
with c1:
    st.metric("目前回合", f"第 {current_group+1} 組")
with c2:
    st.metric("目前階段", "擲骰" if state["phase"] == "roll" else "答題")
with c3:
    st.metric("上次骰子", state["last_roll"] if state["last_roll"] is not None else "-")
with c4:
    st.info(state["last_message"])

# =========================================================
# 主畫面左右欄
# =========================================================
left, right = st.columns([2.2, 1], gap="large")

with left:
    st.subheader("棋盤")
    render_board(state)

with right:
    st.subheader("即時排行榜")
    ranking = []
    for g in range(NUM_GROUPS):
        ranking.append({
            "group": g,
            "owned": owned_count(state, g),
            "money": state["money"][g],
            "position": state["positions"][g]
        })
    ranking.sort(key=lambda x: (x["owned"], x["money"]), reverse=True)

    for idx, item in enumerate(ranking, start=1):
        g = item["group"]
        st.markdown(
            f"""
            <div style="
                border:1px solid #e0e0e0;
                border-radius:12px;
                padding:10px 12px;
                margin-bottom:8px;
                background:linear-gradient(90deg,{GROUP_COLORS[g]}18,white);
            ">
                <div style="font-weight:900;">#{idx} 第 {g+1} 組 {GROUP_ICONS[g]}</div>
                <div>💰 現金：${item['money']}</div>
                <div>🚩 佔領：{item['owned']}</div>
                <div>📍 位置：{item['position']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("最新紀錄")
    for line in state["log"][:12]:
        st.caption(line)

# =========================================================
# 操作區
# =========================================================
st.markdown("---")
st.subheader("操作區")

if role == "玩家" and player_group is None:
    st.warning("請先在左側選擇並加入你的組別。")

if role == "玩家" and player_group is not None and not can_control:
    st.warning(f"現在輪到第 {current_group+1} 組，請等待該組操作。")

if state["phase"] == "roll":
    if can_control:
        if st.button("🎲 擲骰", type="primary", use_container_width=True):
            state = load_state()
            current_group = state["current_group"]

            if role == "玩家":
                # 再確認鎖定權
                lock = state["group_locks"].get(str(player_group))
                if player_group != current_group or lock != session_id:
                    st.error("目前不是你這組的回合，或你沒有控制權。")
                    st.stop()

            state = process_roll(state, current_group)
            save_state(state)
            st.rerun()

if state["phase"] == "answer" and state["current_question"] is not None:
    q = state["current_question"]
    pos = state["current_space"]
    space = BOARD[pos]

    st.markdown(
        f"""
        <div style="
            border:1px solid #ffe082;
            background:#fff8e1;
            border-radius:14px;
            padding:14px;
            margin-bottom:14px;
        ">
            <div style="font-size:14px;color:#795548;">目前所在格</div>
            <div style="font-size:22px;font-weight:900;">【{space['name']}】</div>
            <div style="font-size:14px;color:#546e7a;">
                答對可佔領；答錯支付固定過路費 ${space['toll']}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"**題目：** {q['question']}")
    answer = st.radio("請選擇答案", q["options"], key=f"ans_{state['updated_at']}")

    if can_control:
        if st.button("✅ 提交答案", type="primary", use_container_width=True):
            state = load_state()
            current_group = state["current_group"]

            if role == "玩家":
                lock = state["group_locks"].get(str(player_group))
                if player_group != current_group or lock != session_id:
                    st.error("目前不是你這組的答題回合，或你沒有控制權。")
                    st.stop()

            # 重新抓最新題目
            q = state["current_question"]
            selected_idx = q["options"].index(answer)
            state = process_answer(state, current_group, selected_idx)
            save_state(state)
            st.rerun()
    else:
        st.warning("目前正在由當前回合組別答題。")

# =========================================================
# 規則說明
# =========================================================
with st.expander("規則說明"):
    st.markdown("""
- 共 13 組，起始現金皆為 **$2000**
- 通過起點可獲得 **$200**
- 走到未被佔領的品牌格：  
  - 答對：成功佔領  
  - 答錯：支付該格固定過路費  
- 走到已被別組佔領的格子：  
  - **不可再搶佔**
  - **不回答題目**
  - 直接支付固定過路費給原佔領組  
- 走到自己已佔領的格子：安全通過  
- 機會 / 命運卡金額只會是 **100 / 200 / 300 / 400**
- 一組只能有一個帳號控制，其他人不能加入該組
- 只有當前回合那一組可以擲骰與答題
- 排名先比 **佔領格數**，再比 **現金**
    """)