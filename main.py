import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------
st.set_page_config(page_title="Dashboard - Case Comercial", layout="wide")
st.title("📊 Avaliação de Campanha de Vendas (Q2 2025)")
st.markdown("---")

# ------------------------------------------------
# 2. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ------------------------------------------------
@st.cache_data
def carregar_dados():
    # Carrega o CSV (certifique-se de que o nome do arquivo está idêntico ao que está na sua pasta)
    df = pd.read_csv("Acompanhamento_Campanha.csv", sep=None, engine='python')
    
    # Criando as colunas auxiliares
    df['Período'] = df['Mês'].apply(lambda x: 'Antes' if x <= 3 else 'Durante')
    
    # Garantindo que a ordem dos gráficos fique Antes -> Durante
    df['Período'] = pd.Categorical(df['Período'], categories=['Antes', 'Durante'], ordered=True)
    
    # Cálculos financeiros
    df['Faturamento'] = df['Volume de vendas (t)'] * df['Preço de Venda Líquido (R$/t)']
    df['Lucro Total'] = (df['Preço de Venda Líquido (R$/t)'] - df['Custos de produção (R$/t)']) * df['Volume de vendas (t)']
    
    return df

try:
    df = carregar_dados()
except FileNotFoundError:
    st.error("Arquivo CSV não encontrado. Certifique-se de que o arquivo está na mesma pasta que o app.py.")
    st.stop()

# ------------------------------------------------
# 3. VISUALIZAÇÕES E RESPOSTAS DO CASE
# ------------------------------------------------

# ---- PERGUNTA 2: AVALIAÇÃO GLOBAL DA CAMPANHA ----
st.header("1. Qual foi o resultado global da campanha?")

df_global = df.groupby('Período')[['Volume de vendas (t)', 'Lucro Total']].sum().reset_index()

col1, col2, col3 = st.columns(3)
lucro_antes = df_global.loc[df_global['Período']=='Antes', 'Lucro Total'].values[0]
lucro_durante = df_global.loc[df_global['Período']=='Durante', 'Lucro Total'].values[0]
crescimento_lucro = ((lucro_durante / lucro_antes) - 1) * 100

vol_antes = df_global.loc[df_global['Período']=='Antes', 'Volume de vendas (t)'].values[0]
vol_durante = df_global.loc[df_global['Período']=='Durante', 'Volume de vendas (t)'].values[0]

col1.metric(label="Lucro Total (Antes)", value=f"R$ {lucro_antes:,.0f}".replace(',','.'))
col2.metric(label="Lucro Total (Durante)", value=f"R$ {lucro_durante:,.0f}".replace(',','.'), delta=f"{crescimento_lucro:.2f}%")
col3.markdown("**Veredito:** A campanha foi um sucesso! Apesar do desconto, o ganho de volume compensou a perda de margem unitária, adicionando cerca de R$ 304 mil ao Lucro Total da empresa.")

# Gráficos Globais
fig_lucro = px.bar(df_global, x='Período', y='Lucro Total', text_auto='.3s', title="Evolução do Lucro Total", color='Período', color_discrete_sequence=['#A6B1C2', '#2E5BFF'])
fig_vol = px.bar(df_global, x='Período', y='Volume de vendas (t)', text_auto='.3s', title="Evolução do Volume Total", color='Período', color_discrete_sequence=['#A6B1C2', '#2E5BFF'])

col1_graf, col2_graf = st.columns(2)
col1_graf.plotly_chart(fig_lucro, use_container_width=True)
col2_graf.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")

# ---- PERGUNTAS 1 e 3: VISÃO POR SEGMENTO ----
st.header("2. Visão de Preço, Volume e Efetividade por Segmento")

# Agrupamentos para o segmento
df_seg = df.groupby(['Segmento', 'Período']).agg(
    Volume_Total=('Volume de vendas (t)', 'sum'),
    Faturamento_Total=('Faturamento', 'sum'),
    Volume_Medio=('Volume de vendas (t)', 'mean'),
    Lucro_Total=('Lucro Total', 'sum')
).reset_index()

df_seg['Preço Médio Ponderado'] = df_seg['Faturamento_Total'] / df_seg['Volume_Total']

tab1, tab2, tab3 = st.tabs(["Crescimento do Lucro (Efetividade)", "Preço Médio Ponderado", "Volume Médio"])

with tab1:
    st.subheader("Para qual segmento a campanha foi mais efetiva?")
    fig_efetividade = px.bar(df_seg, x='Segmento', y='Lucro_Total', color='Período', barmode='group', text_auto='.3s', color_discrete_sequence=['#A6B1C2', '#2E5BFF'])
    st.plotly_chart(fig_efetividade, use_container_width=True)
    st.info("💡 A campanha foi altamente efetiva no **Varejo** e nas **Construtoras** (Crescimento de quase 10% no lucro). Para os **Distribuidores**, a efetividade foi baixa (crescimento de apenas 1,5%).")

with tab2:
    st.subheader("Preço Médio de Venda Ponderado")
    fig_preco = px.bar(df_seg, x='Segmento', y='Preço Médio Ponderado', color='Período', barmode='group', text_auto='.2f', color_discrete_sequence=['#A6B1C2', '#2E5BFF'])
    fig_preco.update_layout(yaxis_range=[200, 400]) 
    st.plotly_chart(fig_preco, use_container_width=True)

with tab3:
    st.subheader("Volume Médio de Vendas")
    fig_vol_medio = px.bar(df_seg, x='Segmento', y='Volume_Medio', color='Período', barmode='group', text_auto='.0f', color_discrete_sequence=['#A6B1C2', '#2E5BFF'])
    st.plotly_chart(fig_vol_medio, use_container_width=True)

st.markdown("---")

# ---- PERGUNTA 4: TOP 5 CLIENTES ----
st.header("3. Top 5 Clientes da Campanha")

st.markdown("O ranking abaixo considera o **Lucro Total** deixado pelos clientes durante os meses de campanha, demonstrando quem trouxe o melhor resultado real de caixa.")

# Filtrar apenas o período da campanha
df_durante = df[df['Período'] == 'Durante']

# Agrupando sem usar caracteres especiais no nome das variáveis
top5 = df_durante.groupby('Cód.Cliente').agg(
    Volume_Comprado=('Volume de vendas (t)', 'sum'),
    Faturamento=('Faturamento', 'sum'),
    Lucro_Total=('Lucro Total', 'sum')
).reset_index()

# Renomeando as colunas para a tabela ficar com a apresentação correta
top5 = top5.rename(columns={
    'Volume_Comprado': 'Volume Comprado (t)',
    'Faturamento': 'Faturamento (R$)',
    'Lucro_Total': 'Lucro Total (R$)'
})

# Ordenar e pegar os Top 5
top5 = top5.sort_values(by='Lucro Total (R$)', ascending=False).head(5).reset_index(drop=True)
top5.index = top5.index + 1 # Para o ranking começar em 1 na tabela

# Estilização da tabela no Streamlit
st.dataframe(
    top5.style.format({
        "Volume Comprado (t)": "{:,.0f} t",
        "Faturamento (R$)": "R$ {:,.2f}",
        "Lucro Total (R$)": "R$ {:,.2f}"
    }), 
    use_container_width=True
)

# Gráfico do Top 5
fig_top5 = px.funnel(top5, x='Lucro Total (R$)', y='Cód.Cliente', title="Representatividade do Top 5 no Lucro", color_discrete_sequence=['#2E5BFF'])
st.plotly_chart(fig_top5, use_container_width=True)
