import streamlit as st
import random
import json

st.set_page_config(layout="wide")

st.title("🎲 消費者行為大富翁")

# 讀取資料
board = json.load(open("board.json",encoding="utf8"))
questions = json.load(open("questions.json",encoding="utf8"))
cards = json.load(open("chance_cards.json",encoding="utf8"))

# 初始化
if "pos" not in st.session_state:
    st.session_state.pos=[0]*13
    st.session_state.money=[2000]*13
    st.session_state.owner=[None]*40
    st.session_state.turn=0
    st.session_state.question=None

tokens=["🔴","🔵","🟢","🟡","🟣","🟠","⚫","⚪","🟤","🔺","🔻","🔷","🔶"]
flags=["🚩","🏳️‍🌈","🏴","🏁","🏳️","🚩","🏳️‍🌈","🏴","🏁","🏳️","🚩","🏳️‍🌈","🏴"]

# 排行榜
st.sidebar.title("🏆排行榜")

ranking=sorted(
[(i,st.session_state.money[i]) for i in range(13)],
key=lambda x:x[1],
reverse=True
)

for r in ranking:
    st.sidebar.write(f"第{r[0]+1}組 {tokens[r[0]]} 💰{r[1]}")

# 棋盤
st.header("棋盤")

cols=st.columns(10)

for i in range(40):

    text=board[i]

    if st.session_state.owner[i]!=None:
        text+=flags[st.session_state.owner[i]]

    for t,p in enumerate(st.session_state.pos):
        if p==i:
            text+=tokens[t]

    cols[i%10].button(text,key=i)

team=st.session_state.turn%13

st.header(f"現在輪到 第{team+1}組")

if st.button("🎲 擲骰子"):

    dice=random.randint(1,6)

    pos=st.session_state.pos[team]
    pos=(pos+dice)%40
    st.session_state.pos[team]=pos

    space=board[pos]

    st.write("骰子:",dice)
    st.write("走到:",space)

    if space in ["機會","命運"]:

        card=random.choice(cards)
        st.write(card["text"])
        st.session_state.money[team]+=card["value"]

    else:

        q=random.choice(questions)
        st.session_state.question=q

# 題目
if st.session_state.question:

    q=st.session_state.question

    ans=st.radio(q["question"],q["options"])

    if st.button("提交答案"):

        team=st.session_state.turn%13
        pos=st.session_state.pos[team]

        if q["options"].index(ans)==q["answer"]:

            st.success("答對！佔領成功")
            st.session_state.owner[pos]=team

        else:

            fee=random.choice([100,200,300,400])
            st.error(f"答錯 支付 {fee}")
            st.session_state.money[team]-=fee

        st.session_state.question=None
        st.session_state.turn+=1