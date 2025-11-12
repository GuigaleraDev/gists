import pandas as pd
import streamlit as st
import plotly.express as px
import os


st.set_page_config(page_title='Python', layout='wide')




def clean_numeric_columns(df):
    colunas_numericas = ['resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']
    for coluna in colunas_numericas:
        if coluna in df.columns:
            df[coluna] = df[coluna].astype(str).str.replace(',', '.', regex=False)
            df[coluna] = df[coluna].str.replace('[^0-9.]', '', regex=True)
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
    return df


def clean_key_column(series):
    s = series.astype(str).str.strip()
    s = s.str.split(r'[.,]').str[0]
    return s


def wrap_long_labels(label, max_len=20):
    if isinstance(label, str) and len(label) > max_len:
        words = label.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > max_len:
                lines.append(current_line)
                current_line = word
            else:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
        lines.append(current_line)
        return '<br>'.join(lines)
    return label


@st.cache_data
def load_csv_from_repo(filepath):
    try:
        if not os.path.exists(filepath):
            st.error(f"Erro Crítico: Arquivo '{filepath}' não encontrado. Faça o 'git add' e 'git push' dele.")
            return pd.DataFrame()
        try:
            df = pd.read_csv(filepath, sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, sep=';', encoding='latin1')
        except (pd.errors.ParserError, UnicodeDecodeError):
            try:
                df = pd.read_csv(filepath, sep=',', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, sep=',', encoding='latin1')

        df.columns = df.columns.str.strip().str.lower()
        return df

    except Exception as e:
        st.error(f"Erro fatal ao carregar o arquivo CSV '{filepath}': {e}.")
        return pd.DataFrame()


PROJETOS_FILE = 'dados_projetos.csv'
INDICADORES_FILE = 'dados_indicadores.csv'

df_projetos = load_csv_from_repo(PROJETOS_FILE)
df_indicadores = load_csv_from_repo(INDICADORES_FILE)

if df_projetos.empty or df_indicadores.empty:
    st.error("Falha ao carregar um ou ambos os arquivos CSV base.")
    st.stop()

if 'id gis' not in df_projetos.columns or 'nº projeto' not in df_indicadores.columns:
    st.error("Colunas chave ('id gis' ou 'nº projeto') não encontradas.")
    st.stop()

invalid_values_for_keys = ['n/a', 'pendente', 'null']

df_projetos.dropna(subset=['id gis'], inplace=True)
df_projetos['id gis'] = clean_key_column(df_projetos['id gis'])
df_projetos = df_projetos[~df_projetos['id gis'].str.lower().isin(invalid_values_for_keys)]
df_projetos.rename(columns={'id gis': 'numero do projeto'}, inplace=True)

df_indicadores.dropna(subset=['nº projeto'], inplace=True)
df_indicadores['nº projeto'] = clean_key_column(df_indicadores['nº projeto'])
df_indicadores = df_indicadores[~df_indicadores['nº projeto'].str.lower().isin(invalid_values_for_keys)]
df_indicadores.rename(columns={'nº projeto': 'numero do projeto'}, inplace=True)

colunas_para_dropar = ['município', 'unidade', 'regional', 'estado', 'negócio', 'ano']
colunas_encontradas_para_dropar = [col for col in df_indicadores.columns if col in colunas_para_dropar]
if colunas_encontradas_para_dropar:
    df_indicadores = df_indicadores.drop(columns=colunas_encontradas_para_dropar)

if df_projetos.empty or df_indicadores.empty:
    st.warning("Após a limpeza de IDs, um dos arquivos ficou vazio.")
    st.stop()

try:
    df = pd.merge(df_projetos, df_indicadores, on='numero do projeto', how='left')
    df = clean_numeric_columns(df)
except Exception as e:
    st.error(f"Erro Crítico ao unir as planilhas: {e}")
    st.stop()

if df.empty:
    st.warning("O DataFrame final após a união está vazio.")
    st.stop()

with st.sidebar:
    st.header("Filtros")

    if st.button('Resetar Filtros'):
        st.experimental_rerun()

    st.markdown('---')

    invalid_filter_strings = ['n/a', 'pendente', 'null']

    df_para_filtros = df.copy()

    # --- Filtro de ANO ---
    ano_selecionado = 'Selecione'
    if 'ano' in df_para_filtros.columns:
        anos_disponiveis = []
        opcoes_raw = df_para_filtros['ano'].dropna()
        for item in opcoes_raw:
            try:
                ano_int = int(float(item))
                if 2000 <= ano_int <= 2050:
                    anos_disponiveis.append(ano_int)
            except (ValueError, TypeError):
                continue

        anos_disponiveis = sorted(list(set(anos_disponiveis)))

        if anos_disponiveis:
            anos_disponiveis_com_placeholder = ["Selecione"] + anos_disponiveis
            ano_selecionado = st.selectbox('Ano', anos_disponiveis_com_placeholder, index=0)
            if ano_selecionado != "Selecione":
                df_para_filtros = df_para_filtros[
                    pd.to_numeric(df_para_filtros['ano'], errors='coerce').fillna(0).astype(int) == ano_selecionado
                    ]


    # --- Função auxiliar para criar OPÇÕES de filtro ---
    def criar_opcoes_filtro(dataframe_filtrado, coluna_nome):
        if coluna_nome in dataframe_filtrado.columns:
            opcoes = dataframe_filtrado[coluna_nome].dropna().astype(str).str.strip()
            opcoes_validas = opcoes[~opcoes.str.lower().isin(invalid_filter_strings)]
            opcoes_display = opcoes_validas.str.title().unique().tolist()
            opcoes_display.sort()
            return ["Selecione"] + opcoes_display
        return ["Selecione"]


    # --- Filtros em Cascata ---
    colunas_filtro_cascata = ['regional', 'estado', 'município', 'negócio', 'unidade']
    selecoes = {}

    for col in colunas_filtro_cascata:
        opcoes = criar_opcoes_filtro(df_para_filtros, col)
        selecao = st.selectbox(col.capitalize(), opcoes, key=col)
        selecoes[col] = selecao

        if selecao != "Selecione":
            df_para_filtros = df_para_filtros[
                df_para_filtros[col].astype(str).str.strip().str.title() == selecao
                ]

    df_filtrado = df_para_filtros.copy()

# --- LÓGICA DE EXIBIÇÃO ---
st.markdown("---")

filtros_ativos = any(v != 'Selecione' for v in selecoes.values()) or ano_selecionado != 'Selecione'

if not df_filtrado.empty and (filtros_ativos or len(df_filtrado) < len(df)):

    st.subheader('Análise de Metas')

    tipos_grafico = ['Resultado Ciclo', 'Resultado Previsto', 'Meta 100', 'Meta 300', 'Meta 500']
    colunas_soma = ['resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']
    valores_grafico = [df_filtrado.get(col, pd.Series(0)).fillna(0).sum() for col in colunas_soma]

    dados_grafico = pd.DataFrame({'Tipo': tipos_grafico, 'Valor': valores_grafico})

    fig_horizontal = px.bar(
        dados_grafico,
        x='Valor',
        y='Tipo',
        orientation='h',
        text_auto=True,
        title='Comparação Total de Resultado e Metas',
        color='Tipo',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'Valor': 'Valor Total', 'Tipo': 'Métrica'}
    )
    st.plotly_chart(fig_horizontal, use_container_width=True)

    st.markdown('---')
    st.subheader('Análise de Metas Batidas')

    df_com_resultado = df_filtrado.dropna(subset=['resultado ciclo'])

    if df_com_resultado.empty:
        st.info("Nenhum registro com 'resultado ciclo' preenchido para analisar metas batidas.")
    else:
        m100 = df_com_resultado.get('meta100', float('inf')).fillna(float('inf'))
        m300 = df_com_resultado.get('meta300', float('inf')).fillna(float('inf'))
        m500 = df_com_resultado.get('meta500', float('inf')).fillna(float('inf'))

        filtro_metas = (df_com_resultado['resultado ciclo'] >= m100) | \
                       (df_com_resultado['resultado ciclo'] >= m300) | \
                       (df_com_resultado['resultado ciclo'] >= m500)

        df_metas_batidas = df_com_resultado[filtro_metas].copy()

        if not df_metas_batidas.empty:

            # --- SEÇÃO 1: CONTAGEM DE METAS BATIDAS ---
            contagem = {}
            if 'meta100' in df_metas_batidas:
                contagem['Meta 100'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta100'].fillna(
                    float('inf'))).sum()
            if 'meta300' in df_metas_batidas:
                contagem['Meta 300'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta300'].fillna(
                    float('inf'))).sum()
            if 'meta500' in df_metas_batidas:
                contagem['Meta 500'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta500'].fillna(
                    float('inf'))).sum()

            df_contagem = pd.DataFrame(list(contagem.items()), columns=['Meta', 'Total'])

            if not df_contagem.empty:
                st.subheader('Contagem de Metas Batidas')
                fig = px.bar(df_contagem, x='Meta', y='Total', text_auto=True, color='Meta',
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)

            # --- SEÇÃO 2: RESULTADO VS METAS POR INDICADOR (GRÁFICO CORRIGIDO) ---
            st.subheader('Resultado vs Metas por Indicador')

            df_metas_batidas['Meta100_Soma'] = df_metas_batidas.apply(
                lambda row: row['meta100'] if row['resultado ciclo'] >= row['meta100'] else 0, axis=1)
            df_metas_batidas['Meta300_Soma'] = df_metas_batidas.apply(
                lambda row: row['meta300'] if row['resultado ciclo'] >= row['meta300'] else 0, axis=1)
            df_metas_batidas['Meta500_Soma'] = df_metas_batidas.apply(
                lambda row: row['meta500'] if row['resultado ciclo'] >= row['meta500'] else 0, axis=1)

            cols_agrupar = ['resultado ciclo', 'resultado previsto', 'Meta100_Soma', 'Meta300_Soma', 'Meta500_Soma']
            cols_agrupar_existentes = [col for col in cols_agrupar if col in df_metas_batidas.columns]

            if 'nome do indicador' in df_metas_batidas.columns:
                df_metas_batidas['nome do indicador'] = df_metas_batidas['nome do indicador'].astype(
                    str).str.strip().str.title().apply(wrap_long_labels)
                df_metas_batidas['nome do indicador'] = df_metas_batidas['nome do indicador'].replace('Evasão',
                                                                                                      '% De Evasão')

                df_agrupado = df_metas_batidas.dropna(subset=['nome do indicador']) \
                    .groupby('nome do indicador')[cols_agrupar_existentes].sum().reset_index()

                dados_grafico_detalhado = pd.DataFrame()

                for coluna in cols_agrupar_existentes:
                    temp_df = df_agrupado[['nome do indicador', coluna]].copy()
                    temp_df.rename(columns={coluna: 'Valor'}, inplace=True)

                    if coluna == 'resultado ciclo':
                        temp_df['Tipo'] = 'Resultado Ciclo'
                    elif coluna == 'resultado previsto':
                        temp_df['Tipo'] = 'Resultado Previsto'
                    elif coluna == 'Meta100_Soma':
                        temp_df['Tipo'] = 'Meta 100 Atingida'
                    elif coluna == 'Meta300_Soma':
                        temp_df['Tipo'] = 'Meta 300 Atingida'
                    elif coluna == 'Meta500_Soma':
                        temp_df['Tipo'] = 'Meta 500 Atingida'
                    else:
                        temp_df['Tipo'] = coluna

                    dados_grafico_detalhado = pd.concat([dados_grafico_detalhado, temp_df])

                dados_grafico_detalhado = dados_grafico_detalhado.dropna()

                fig_detalhe = px.bar(
                    dados_grafico_detalhado,
                    x='nome do indicador',
                    y='Valor',
                    color='Tipo',
                    barmode='group',
                    text_auto=True,
                    title='Comparação de Resultado e Metas Atingidas por Indicador',
                    color_discrete_map={
                        'Resultado Ciclo': 'royalblue',
                        'Resultado Previsto': 'skyblue',
                        'Meta 100 Atingida': 'lightgreen',
                        'Meta 300 Atingida': 'lightgreen',
                        'Meta 500 Atingida': 'lightgreen'
                    },
                    labels={
                        'nome do indicador': 'Indicador',
                        'Valor': 'Valor Total',
                        'Tipo': 'Métrica'
                    }
                )
                fig_detalhe.update_xaxes(tickangle=0, automargin=True)

                st.plotly_chart(fig_detalhe, use_container_width=True)
            else:
                st.warning("Coluna 'nome do indicador' não encontrada para gerar o gráfico detalhado.")

            st.subheader('Lista de Registros que Bateram a Meta')

            colunas_exibicao = ['numero do projeto', 'nome do projeto', 'nome do indicador', 'tipo de agregaçao',
                                'regional', 'estado', 'município', 'negócio', 'unidade',
                                'resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']

            colunas_existentes = [col for col in colunas_exibicao if col in df_metas_batidas.columns]
            coluna_ordenacao = 'regional' if 'regional' in df_metas_batidas.columns else 'numero do projeto'

            if coluna_ordenacao in df_metas_batidas:
                df_metas_batidas_ordenado = df_metas_batidas.sort_values(by=coluna_ordenacao, ascending=True)
            else:
                df_metas_batidas_ordenado = df_metas_batidas

            st.dataframe(df_metas_batidas_ordenado[colunas_existentes])

        else:
            st.info("Nenhum registro encontrado que tenha batido alguma meta com os filtros aplicados.")

else:
    st.info("Por favor, use os filtros na barra lateral para selecionar dados e exibir as visualizações.")