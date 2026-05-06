import streamlit as st
import plotly.express as px
import random
fake=[]
for i in range(3):
    fake.append(random.randint(8000,12000))
st.title("algorithme comparisions")
distance_data={"algorithmes":["HC","SA","Greedy"],"distance":fake}
fig_distance=px.bar(distance_data,x="algorithmes",y="distance",title="distance corresponding to each algorithme")
st.plotly_chart(fig_distance)

iterations=list(range(1,11))
convergence_data={
    "iteration":iterations,"HC":[random.randint(5000,10000)-i*120 for _ in range(10)],
    "Greedy":[random.randint(5000,10000)-i*80 for _ in range(10)],"SA":[random.randint(5000,10000)-i*150 for _ in range(10)]
}
fig_convergence=px.line(convergence_data,y=["HC","SA","Greedy"],x="iteration",title="convergence per iteration")
st.plotly_chart(fig_convergence)

num_Team=[10,13,17,20]
run_time={
    "Team":num_Team,"HC":[random.randint(1,3) for _ in range(4)],
"SA":[random.randint(1,9) for _ in range(4)],"Greedy":[random.randint(4,7) for _ in range(4)]
}
fig_run=px.bar(run_time,x="Team",y=["HC","SA","Greedy"],title="run time for each algo fo N team")
st.plotly_chart(fig_run)