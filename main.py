import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="Dashboard - Case Comercial", layout="wide")
st.title("Campanha de Vendas")

COR_ANTES = '#96e637'
COR_DURANTE = '#0000bf'
PALETA = [COR_ANTES, COR_DURANTE]

@st.cache_data
def carregar_dados():
    df = pd.read_csv("Acompanhamento_Campanha.csv", sep=None, engine='python')
    df['Período'] = df['Mês'].apply(lambda x: 'Antes' if x <= 3 else 'Durante')
    df['Período'] = pd.Categorical(df['Período'], categories=['Antes', 'Durante'], ordered=True)
    df['Faturamento'] = df['Volume de vendas (t)'] * df['Preço de Venda Líquido (R$/t)']
    df['Lucro Total'] = (df['Preço de Venda Líquido (R$/t)'] - df['Custos de produção (R$/t)']) * df['Volume de vendas (t)']
    return df

try:
    df = carregar_dados()
except FileNotFoundError:
    st.error("Arquivo Acompanhamento_Campanha.csv não encontrado. Verifique se ele está na mesma pasta que o app.py.")
    st.stop()

aba_executiva, aba_detalhada = st.tabs(["Dashboard", "Detalhes"])

with aba_executiva:
    st.header("1. Resultado da Campanha")

    df_global = df.groupby('Período')[['Volume de vendas (t)', 'Lucro Total']].sum().reset_index()

    col1, col2, col3 = st.columns(3)
    lucro_antes = df_global.loc[df_global['Período']=='Antes', 'Lucro Total'].values[0]
    lucro_durante = df_global.loc[df_global['Período']=='Durante', 'Lucro Total'].values[0]
    crescimento_lucro = ((lucro_durante / lucro_antes) - 1) * 100

    col1.metric(label="Lucro Total (Antes)", value=f"R$ {lucro_antes:,.0f}".replace(',','.'))
    col2.metric(label="Lucro Total (Durante)", value=f"R$ {lucro_durante:,.0f}".replace(',','.'), delta=f"{crescimento_lucro:.2f}%")
    col3.markdown("**Resposta:** A campanha foi um sucesso! O ganho de volume compensou a perda de margem unitária, adicionando valor real ao Lucro Total da empresa.")

    fig_lucro = px.bar(df_global, x='Período', y='Lucro Total', text_auto='.3s', title="Evolução do Lucro Total", color='Período', color_discrete_sequence=PALETA)
    fig_vol = px.bar(df_global, x='Período', y='Volume de vendas (t)', text_auto='.3s', title="Evolução do Volume Total", color='Período', color_discrete_sequence=PALETA)

    col1_graf, col2_graf = st.columns(2)
    col1_graf.plotly_chart(fig_lucro, use_container_width=True)
    col2_graf.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")
            # GRAFICO NOVO: Evolução Mensal
    st.header("2. Evolução Mensal do Lucro (Timeline)")
    st.markdown("Como o Lucro se comportou mês a mês antes e durante o período promocional.")
    
    # 1. Agrupar e garantir a ordem correta para a linha não ficar "torta"
    df_mensal = df.groupby('Mês')['Lucro Total'].sum().reset_index().sort_values('Mês')
    
    # 2. Transformar o número em texto ("Mês 1", "Mês 2") para o eixo X ficar perfeitamente alinhado
    df_mensal['Mês_Texto'] = df_mensal['Mês'].apply(lambda x: f"Mês {x}")
    
    fig_linha = px.line(df_mensal, x='Mês_Texto', y='Lucro Total', markers=True, title="Curva de Lucro ao longo dos Meses", text='Lucro Total')
    
    # 3. Tirando o aspecto "escuro": Linha mais grossa e marcadores maiores com borda clara
    fig_linha.update_traces(
        textposition="bottom right", 
        texttemplate='%{text:.3s}', 
        line=dict(color=COR_ANTES, width=4), 
        marker=dict(color=COR_ANTES, size=12, line=dict(color='white', width=2))
    )
    
    # 4. Ajustando a marcação verde de fundo (índices 2.5 a 5.5 cobrem exatamente os meses 4, 5 e 6)
    fig_linha.add_vrect(
        x0=2.5, x1=5.5, 
        fillcolor=COR_DURANTE, opacity=0.15, 
        line_width=0, annotation_text=" Período da Campanha", annotation_position="top left"
    )
    
    st.plotly_chart(fig_linha, use_container_width=True)


    st.markdown("---")

    st.header("2. Visão de Preço, Volume e Efetividade por Segmento")

    df_seg = df.groupby(['Segmento', 'Período']).agg(
        Volume_Total=('Volume de vendas (t)', 'sum'),
        Faturamento_Total=('Faturamento', 'sum'),
        Volume_Medio=('Volume de vendas (t)', 'mean'),
        Lucro_Total=('Lucro Total', 'sum')
    ).reset_index()
    df_seg['Preço Médio Ponderado'] = df_seg['Faturamento_Total'] / df_seg['Volume_Total']

    tab1, tab2, tab3 = st.tabs(["Crescimento do Lucro (Efetividade)", "Preço Médio Ponderado", "Volume Médio"])

    with tab1:
        fig_efetividade = px.bar(df_seg, x='Segmento', y='Lucro_Total', color='Período', barmode='group', text_auto='.3s', color_discrete_sequence=PALETA)
        st.plotly_chart(fig_efetividade, use_container_width=True)
    with tab2:
        fig_preco = px.bar(df_seg, x='Segmento', y='Preço Médio Ponderado', color='Período', barmode='group', text_auto='.2f', color_discrete_sequence=PALETA)
        fig_preco.update_layout(yaxis_range=[200, 400]) 
        st.plotly_chart(fig_preco, use_container_width=True)
    with tab3:
        fig_vol_medio = px.bar(df_seg, x='Segmento', y='Volume_Medio', color='Período', barmode='group', text_auto='.0f', color_discrete_sequence=PALETA)
        st.plotly_chart(fig_vol_medio, use_container_width=True)

    st.markdown("---")
    st.header("3. Top 5 Clientes da Campanha")

    df_durante = df[df['Período'] == 'Durante']
    top5 = df_durante.groupby('Cód.Cliente').agg(
        Volume_Comprado=('Volume de vendas (t)', 'sum'),
        Faturamento=('Faturamento', 'sum'),
        Lucro_Total=('Lucro Total', 'sum')
    ).reset_index()

    top5 = top5.rename(columns={'Volume_Comprado': 'Volume Comprado (t)', 'Faturamento': 'Faturamento (R$)', 'Lucro_Total': 'Lucro Total (R$)'})
    top5 = top5.sort_values(by='Lucro Total (R$)', ascending=False).head(5).reset_index(drop=True)
    top5.index = top5.index + 1 

    st.dataframe(top5.style.format({"Volume Comprado (t)": "{:,.0f} t", "Faturamento (R$)": "R$ {:,.2f}", "Lucro Total (R$)": "R$ {:,.2f}"}), use_container_width=True)
    # Gráfico de Funil do Top 5 devolvido com a cor verde da campanha!
    fig_top5 = px.funnel(top5, x='Lucro Total (R$)', y='Cód.Cliente', title="Representatividade do Top 5 no Lucro", color_discrete_sequence=[COR_DURANTE])
    st.plotly_chart(fig_top5, use_container_width=True)

with aba_detalhada:
    st.header("Filtro de dados por Segmento ou Cliente")
    
    tipo_filtro = st.radio("Deseja filtrar por:", ["Segmento", "Cliente"], horizontal=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if tipo_filtro == "Segmento":
        lista_opcoes = df['Segmento'].unique()
        selecao = st.selectbox("Selecione o Segmento:", lista_opcoes)
        df_filtrado = df[df['Segmento'] == selecao]
    else:
        lista_opcoes = sorted(df['Cód.Cliente'].unique())
        selecao = st.selectbox("Selecione o Cliente:", lista_opcoes)
        df_filtrado = df[df['Cód.Cliente'] == selecao]
        
    st.markdown("---")
    

    df_resumo_filtro = df_filtrado.groupby('Período')[['Volume de vendas (t)', 'Lucro Total', 'Faturamento']].sum().reset_index()
    
    
    try:
        lucro_a = df_resumo_filtro.loc[df_resumo_filtro['Período']=='Antes', 'Lucro Total'].values[0]
        lucro_d = df_resumo_filtro.loc[df_resumo_filtro['Período']=='Durante', 'Lucro Total'].values[0]
        var_lucro = ((lucro_d / lucro_a) - 1) * 100
        
        vol_a = df_resumo_filtro.loc[df_resumo_filtro['Período']=='Antes', 'Volume de vendas (t)'].values[0]
        vol_d = df_resumo_filtro.loc[df_resumo_filtro['Período']=='Durante', 'Volume de vendas (t)'].values[0]
        var_vol = ((vol_d / vol_a) - 1) * 100
        
    
        st.subheader(f"Desempenho: {selecao}")
        col_f1, col_f2 = st.columns(2)
        col_f1.metric("Variação de Lucro Total", f"R$ {lucro_d:,.0f}".replace(',','.'), f"{var_lucro:.2f}%")
        col_f2.metric("Variação de Volume (t)", f"{vol_d:,.0f} t".replace(',','.'), f"{var_vol:.2f}%")
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns(2)
        
        fig_f_lucro = px.bar(df_resumo_filtro, x='Período', y='Lucro Total', title=f"Lucro: {selecao}", text_auto='.3s', color='Período', color_discrete_sequence=PALETA)
        fig_f_vol = px.bar(df_resumo_filtro, x='Período', y='Volume de vendas (t)', title=f"Volume: {selecao}", text_auto='.3s', color='Período', color_discrete_sequence=PALETA)
        
        col_g1.plotly_chart(fig_f_lucro, use_container_width=True)
        col_g2.plotly_chart(fig_f_vol, use_container_width=True)
        
    except IndexError:
        st.warning("Não há dados suficientes nos dois períodos para comparar este item.")

