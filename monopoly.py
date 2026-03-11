import streamlit as st
import random
import json
import time

st.set_page_config(page_title="消費者行為大富翁", layout="wide")

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
# 初始化 session state
# =========================================================
def init_game():
    if "positions" not in st.session_state:
        st.session_state.positions = [0] * NUM_GROUPS
    if "money" not in st.session_state:
        st.session_state.money = [START_MONEY] * NUM_GROUPS
    if "owner" not in st.session_state:
        st.session_state.owner = [None] * len(BOARD)
    if "turn" not in st.session_state:
        st.session_state.turn = 0
    if "current_group" not in st.session_state:
        st.session_state.current_group = 0
    if "phase" not in st.session_state:
        st.session_state.phase = "roll"   # roll / answer
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "current_space" not in st.session_state:
        st.session_state.current_space = None
    if "last_roll" not in st.session_state:
        st.session_state.last_roll = None
    if "last_message" not in st.session_state:
        st.session_state.last_message = "遊戲開始，請第 1 組擲骰。"
    if "log" not in st.session_state:
        st.session_state.log = []

init_game()

# =========================================================
# 工具函式
# =========================================================
def next_group(g):
    return (g + 1) % NUM_GROUPS

def owned_count(g):
    return sum(1 for x in st.session_state.owner if x == g)

def add_log(text):
    st.session_state.log.insert(0, text)
    st.session_state.log = st.session_state.log[:50]

def draw_question():
    return random.choice(QUESTIONS)

def draw_card(card_type):
    if card_type == "chance":
        return random.choice(CHANCE_CARDS)
    return random.choice(FATE_CARDS)

def reset_game():
    st.session_state.positions = [0] * NUM_GROUPS
    st.session_state.money = [START_MONEY] * NUM_GROUPS
    st.session_state.owner = [None] * len(BOARD)
    st.session_state.turn = 0
    st.session_state.current_group = 0
    st.session_state.phase = "roll"
    st.session_state.current_question = None
    st.session_state.current_space = None
    st.session_state.last_roll = None
    st.session_state.last_message = "遊戲開始，請第 1 組擲骰。"
    st.session_state.log = []

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

# =========================================================
# 棋盤顯示
# =========================================================
def render_cell_html(idx):
    space = BOARD[idx]
    owner = st.session_state.owner[idx]
    tokens_here = [g for g, p in enumerate(st.session_state.positions) if p == idx]

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

def render_board():
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
        grid[r][c] = render_cell_html(i)

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
        <div style="font-size:15px;color:#455a64;margin-top:8px;">固定過路費・品牌搶地・課堂版</div>
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
def process_roll():
    group_idx = st.session_state.current_group
    dice = animate_dice()
    old_pos = st.session_state.positions[group_idx]
    new_pos = (old_pos + dice) % len(BOARD)

    # 通過起點獎金
    if old_pos + dice >= len(BOARD):
        st.session_state.money[group_idx] += PASS_START_BONUS
        add_log(f"第 {group_idx+1} 組通過起點，獲得 ${PASS_START_BONUS}")

    # 先移動棋子
    st.session_state.positions[group_idx] = new_pos
    st.session_state.current_space = new_pos
    st.session_state.last_roll = dice

    space = BOARD[new_pos]

    # 起點
    if space["type"] == "start":
        st.session_state.phase = "roll"
        st.session_state.current_group = next_group(group_idx)
        st.session_state.current_question = None
        msg = f"第 {group_idx+1} 組擲出 {dice} 點，停在起點。下一組：第 {st.session_state.current_group+1} 組。"
        st.session_state.last_message = msg
        add_log(msg)
        return

    # 機會
    if space["type"] == "chance":
        card = draw_card("chance")
        st.session_state.money[group_idx] += card["money"]
        st.session_state.phase = "roll"
        st.session_state.current_group = next_group(group_idx)
        st.session_state.current_question = None
        sign = "+" if card["money"] >= 0 else ""
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【機會】。"
            f"{card['title']}：{card['text']}（{sign}${card['money']}）"
            f" 下一組：第 {st.session_state.current_group+1} 組。"
        )
        st.session_state.last_message = msg
        add_log(msg)
        return

    # 命運
    if space["type"] == "fate":
        card = draw_card("fate")
        st.session_state.money[group_idx] += card["money"]
        st.session_state.phase = "roll"
        st.session_state.current_group = next_group(group_idx)
        st.session_state.current_question = None
        sign = "+" if card["money"] >= 0 else ""
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【命運】。"
            f"{card['title']}：{card['text']}（{sign}${card['money']}）"
            f" 下一組：第 {st.session_state.current_group+1} 組。"
        )
        st.session_state.last_message = msg
        add_log(msg)
        return

    # 品牌格
    owner = st.session_state.owner[new_pos]

    # 尚未被佔領：出題
    if owner is None:
        st.session_state.phase = "answer"
        st.session_state.current_question = draw_question()
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到【{space['name']}】。"
            f" 此格尚未被佔領，請回答題目。答對可佔領；答錯支付固定過路費 ${space['toll']}。"
        )
        st.session_state.last_message = msg
        add_log(msg)
        return

    # 自己的地
    if owner == group_idx:
        st.session_state.phase = "roll"
        st.session_state.current_group = next_group(group_idx)
        st.session_state.current_question = None
        msg = (
            f"第 {group_idx+1} 組擲出 {dice} 點，來到自己的【{space['name']}】。"
            f" 安全通過，下一組：第 {st.session_state.current_group+1} 組。"
        )
        st.session_state.last_message = msg
        add_log(msg)
        return

    # 別人的地：不可再搶，直接付固定過路費
    toll = space["toll"]
    st.session_state.money[group_idx] -= toll
    st.session_state.money[owner] += toll
    st.session_state.phase = "roll"
    st.session_state.current_group = next_group(group_idx)
    st.session_state.current_question = None
    msg = (
        f"第 {group_idx+1} 組擲出 {dice} 點，來到第 {owner+1} 組已佔領的【{space['name']}】。"
        f" 不可再搶佔，直接支付固定過路費 ${toll}。下一組：第 {st.session_state.current_group+1} 組。"
    )
    st.session_state.last_message = msg
    add_log(msg)

def process_answer(selected_idx):
    q = st.session_state.current_question
    group_idx = st.session_state.current_group
    pos = st.session_state.current_space
    space = BOARD[pos]

    if selected_idx == q["answer"]:
        st.session_state.owner[pos] = group_idx
        msg = (
            f"第 {group_idx+1} 組回答正確，成功佔領【{space['name']}】。"
            f" 理論概念：{q['concept']}。"
        )
    else:
        toll = space["toll"]
        st.session_state.money[group_idx] -= toll
        correct = q["options"][q["answer"]]
        msg = (
            f"第 {group_idx+1} 組回答錯誤，支付固定過路費 ${toll}。"
            f" 正確答案：{correct}。理論概念：{q['concept']}。"
        )

    st.session_state.phase = "roll"
    st.session_state.current_group = next_group(group_idx)
    st.session_state.current_question = None
    st.session_state.current_space = None
    st.session_state.last_message = msg + f" 下一組：第 {st.session_state.current_group+1} 組。"
    add_log(st.session_state.last_message)

# =========================================================
# 頁面
# =========================================================
st.title("🎲 消費者行為大富翁｜先救活版")

with st.sidebar:
    st.subheader("控制台")
    if st.button("♻️ 重設整局遊戲", type="primary", use_container_width=True):
        reset_game()
        st.rerun()

    if st.button("🔄 重新整理畫面", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.subheader("目前操作")

    st.info(f"目前回合：第 {st.session_state.current_group+1} 組")
    st.info(f"目前階段：{'擲骰' if st.session_state.phase == 'roll' else '答題'}")

    if st.session_state.phase == "roll":
        if st.button("🎲 擲骰", type="primary", use_container_width=True):
            process_roll()
            st.rerun()

    if st.session_state.phase == "answer" and st.session_state.current_question is not None:
        q = st.session_state.current_question
        pos = st.session_state.current_space
        space = BOARD[pos]

        st.warning(f"目前所在格：{space['name']}")
        st.caption(f"答對可佔領；答錯支付固定過路費 ${space['toll']}")

        sidebar_answer = st.radio(
            "請選擇答案",
            q["options"],
            key=f"sidebar_ans_{st.session_state.turn}_{pos}"
        )

        if st.button("✅ 提交答案", type="primary", use_container_width=True):
            selected_idx = q["options"].index(sidebar_answer)
            process_answer(selected_idx)
            st.session_state.turn += 1
            st.rerun()

# 頂部狀態
c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
with c1:
    st.metric("目前回合", f"第 {st.session_state.current_group+1} 組")
with c2:
    st.metric("目前階段", "擲骰" if st.session_state.phase == "roll" else "答題")
with c3:
    st.metric("上次骰子", st.session_state.last_roll if st.session_state.last_roll is not None else "-")
with c4:
    st.info(st.session_state.last_message)

left, right = st.columns([2.2, 1], gap="large")

with left:
    st.subheader("棋盤")
    render_board()

with right:
    st.subheader("即時排行榜")

    ranking = []
    for g in range(NUM_GROUPS):
        ranking.append({
            "group": g,
            "owned": owned_count(g),
            "money": st.session_state.money[g],
            "position": st.session_state.positions[g]
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
    for line in st.session_state.log[:12]:
        st.caption(line)

