import streamlit as st
import random
import json
import time
import os

st.set_page_config(page_title="消費者行為大富翁", layout="wide")

# ---------------------------------------------------
# 讀取 JSON 資料
# ---------------------------------------------------

with open("board.json", "r", encoding="utf-8") as f:
    BOARD = json.load(f)

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("chance_cards.json", "r", encoding="utf-8") as f:
    CARD_DATA = json.load(f)
    CHANCE_CARDS = CARD_DATA["chance"]
    FATE_CARDS = CARD_DATA["fate"]

# ---------------------------------------------------
# 基本設定
# ---------------------------------------------------

NUM_GROUPS = 13
START_MONEY = 2000

GROUP_COLORS = [
"#e53935","#1e88e5","#43a047","#fdd835","#8e24aa",
"#fb8c00","#00acc1","#d81b60","#6d4c41","#546e7a",
"#3949ab","#7cb342","#c0ca33"
]

GROUP_ICONS = [
"🔴","🔵","🟢","🟡","🟣","🟠","🔷",
"🌸","🟤","⚫","💎","🍏","⭐"
]

# ---------------------------------------------------
# 初始化
# ---------------------------------------------------

if "positions" not in st.session_state:
    st.session_state.positions = [0]*NUM_GROUPS
    st.session_state.money = [START_MONEY]*NUM_GROUPS
    st.session_state.owner = [None]*len(BOARD)
    st.session_state.turn = 0
    st.session_state.phase = "roll"
    st.session_state.question = None
    st.session_state.current_space = None

# ---------------------------------------------------
# UI
# ---------------------------------------------------

st.title("🎲 消費者行為大富翁")

current_group = st.session_state.turn % NUM_GROUPS

st.info(f"目前輪到：第 {current_group+1} 組 {GROUP_ICONS[current_group]}")

# ---------------------------------------------------
# 擲骰動畫
# ---------------------------------------------------

def roll_dice():

    placeholder = st.empty()

    for i in range(10):
        num = random.randint(1,6)
        placeholder.markdown(f"# 🎲 {num}")
        time.sleep(0.05)

    return random.randint(1,6)

# ---------------------------------------------------
# 棋盤顯示
# ---------------------------------------------------

st.subheader("棋盤")

cols = st.columns(10)

for i,space in enumerate(BOARD):

    owner = st.session_state.owner[i]

    text = f"**{space['name']}**"

    if space["type"]=="brand":
        text += f"\n\n過路費 ${space['toll']}"

    if owner is not None:
        text += f"\n\n🚩 第{owner+1}組"

    tokens = [g for g,p in enumerate(st.session_state.positions) if p==i]

    token_text=""

    for g in tokens:
        token_text+=GROUP_ICONS[g]

    text+=f"\n\n{token_text}"

    cols[i%10].markdown(text)

# ---------------------------------------------------
# 擲骰
# ---------------------------------------------------

if st.session_state.phase=="roll":

    if st.button("🎲 擲骰"):

        dice = roll_dice()

        pos = st.session_state.positions[current_group]

        new_pos = (pos+dice)%len(BOARD)

        st.session_state.positions[current_group] = new_pos

        space = BOARD[new_pos]

        st.session_state.current_space = new_pos

        if space["type"]=="start":

            st.success("回到起點")

            st.session_state.money[current_group]+=200

            st.session_state.turn+=1

        elif space["type"]=="chance":

            card=random.choice(CHANCE_CARDS)

            st.warning(card["title"])

            st.write(card["text"])

            st.session_state.money[current_group]+=card["money"]

            st.session_state.turn+=1

        elif space["type"]=="fate":

            card=random.choice(FATE_CARDS)

            st.error(card["title"])

            st.write(card["text"])

            st.session_state.money[current_group]+=card["money"]

            st.session_state.turn+=1

        else:

            owner = st.session_state.owner[new_pos]

            if owner is None:

                st.session_state.phase="answer"

                st.session_state.question=random.choice(QUESTIONS)

            elif owner==current_group:

                st.success("自己的地盤")

                st.session_state.turn+=1

            else:

                toll = space["toll"]

                st.warning(f"支付過路費 ${toll}")

                st.session_state.money[current_group]-=toll

                st.session_state.money[owner]+=toll

                st.session_state.turn+=1

# ---------------------------------------------------
# 答題
# ---------------------------------------------------

if st.session_state.phase=="answer":

    q=st.session_state.question

    st.subheader("回答題目")

    st.write(q["question"])

    ans = st.radio("選擇答案",q["options"])

    if st.button("提交答案"):

        idx=q["options"].index(ans)

        pos=st.session_state.current_space

        space=BOARD[pos]

        if idx==q["answer"]:

            st.success("答對！成功佔領")

            st.session_state.owner[pos]=current_group

        else:

            st.error("答錯")

            toll=space["toll"]

            st.session_state.money[current_group]-=toll

        st.write("概念:",q["concept"])

        st.session_state.phase="roll"

        st.session_state.turn+=1

# ---------------------------------------------------
# 排行榜
# ---------------------------------------------------

st.subheader("排行榜")

data=[]

for g in range(NUM_GROUPS):

    owned=sum([1 for x in st.session_state.owner if x==g])

    data.append({
        "組別":g+1,
        "現金":st.session_state.money[g],
        "佔領":owned
    })

data=sorted(data,key=lambda x:(x["佔領"],x["現金"]),reverse=True)

st.table(data)