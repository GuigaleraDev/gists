import pandas as pd
import streamlit as st
import plotly.express as px
import os  # Para verificar se os CSVs existem

st.title('GIS - Visão Geral')
st.set_page_config(page_title='Python', layout='wide')

# Nomes dos arquivos CSV que ESTÃO no repositório
PROJETOS_FILE = 'dados_projetos.csv'  # Salvo da "Planilha1"
INDICADORES_FILE = 'dados_indicadores.csv'  # Salvo do "Relatório_Extraído"


def clean_numeric_columns(df):
    """
    Função auxiliar para limpar e converter colunas numéricas.
    """
    colunas_numericas = ['resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']
    for coluna in colunas_numericas:
        if coluna in df.columns:
            df[coluna] = df[coluna].astype(str).str.replace(',', '.', regex=False)
            df[coluna] = df[coluna].str.replace('[^0-9.]', '', regex=True)
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
    return df


@st.cache_data  # Cache para performance
def load_csv_from_repo(filepath):
    """
    Carrega um arquivo CSV que está junto com o código no repositório.
    """
    try:
        if not os.path.exists(filepath):
            st.error(f"Erro Crítico: Arquivo '{filepath}' não encontrado. Faça o 'git add' e 'git push' dele.")
            return pd.DataFrame()

        # --- MODIFICADO: Tenta ler com VÍRGULA primeiro ---
        try:
            df = pd.read_csv(filepath, sep=',')
        except pd.errors.ParserError:
            # Se falhar (talvez por causa de vírgulas nos dados), tenta com PONTO E VÍRGULA
            st.warning(f"Falha ao ler {filepath} com ','. Tentando com ';'.")
            df = pd.read_csv(filepath, sep=';')

        # Padroniza nomes das colunas para minúsculas logo na leitura
        df.columns = df.columns.str.strip().str.lower()

        return df

    except Exception as e:
        st.error(
            f"Erro ao carregar o arquivo CSV '{filepath}': {e}. Verifique se ele foi salvo como CSV (separado por vírgula).")
        return pd.DataFrame()


# --- LÓGICA PRINCIPAL DO APP ---

st.info(f"Carregando dados dos arquivos '{PROJETOS_FILE}' e '{INDICADORES_FILE}'...")

df_projetos = load_csv_from_repo(PROJETOS_FILE)
df_indicadores = load_csv_from_repo(INDICADORES_FILE)

if df_projetos.empty or df_indicadores.empty:
    st.error("Falha ao carregar um ou ambos os arquivos CSV base. Verifique os logs e se os arquivos estão no GitHub.")
    st.stop()

# --- LÓGICA DE LIMPEZA e RENOMEAÇÃO (pré-merge) ---
st.subheader("Processo de Limpeza e Preparação")

# Verifica as colunas chave (em minúsculo, pois já foram convertidas)
if 'id gis' not in df_projetos.columns:
    st.error(f"Erro Crítico: Coluna 'id gis' não encontrada em '{PROJETOS_FILE}' (vinda de 'Planilha1').")
    st.write("Colunas encontradas:", df_projetos.columns.tolist())
    st.stop()

if 'nº projeto' not in df_indicadores.columns:
    st.error(
        f"Erro Crítico: Coluna 'nº projeto' não encontrada em '{INDICADORES_FILE}' (vinda de 'Relatório_Extraído').")
    st.write("Colunas encontradas:", df_indicadores.columns.tolist())
    st.stop()

# Limpa IDs inválidos e Renomeia as colunas chave para 'numero do projeto'
invalid_values_for_keys = ['n/a', 'pendente', 'null']

# Limpa df_projetos ('id gis')
df_projetos.dropna(subset=['id gis'], inplace=True)
df_projetos['id gis'] = df_projetos['id gis'].astype(str).str.strip().str.split('.').str[0]
df_projetos = df_projetos[~df_projetos['id gis'].str.lower().isin(invalid_values_for_keys)]
df_projetos.rename(columns={'id gis': 'numero do projeto'}, inplace=True)
st.info(f"'{PROJETOS_FILE}' limpo (usando 'id gis').")

# Limpa df_indicadores ('nº projeto')
df_indicadores.dropna(subset=['nº projeto'], inplace=True)
df_indicadores['nº projeto'] = df_indicadores['nº projeto'].astype(str).str.strip().str.split('.').str[0]
df_indicadores = df_indicadores[~df_indicadores['nº projeto'].str.lower().isin(invalid_values_for_keys)]
df_indicadores.rename(columns={'nº projeto': 'numero do projeto'}, inplace=True)
st.info(f"'{INDICADORES_FILE}' limpo (usando 'nº projeto').")

# Remove colunas duplicadas de Localização ANTES do merge
colunas_para_dropar = ['município', 'unidade', 'regional', 'estado', 'negócio', 'ano']
colunas_encontradas_para_dropar = [col for col in df_indicadores.columns if col in colunas_para_dropar]

if colunas_encontradas_para_dropar:
    df_indicadores = df_indicadores.drop(columns=colunas_encontradas_para_dropar)
    st.info(f"Colunas duplicadas removidas de '{INDICADORES_FILE}': {colunas_encontradas_para_dropar}")

# --- LÓGICA DE MERGE (UNIÃO) ---
try:
    st.info("Unindo (merge) os dados...")
    df = pd.merge(df_projetos, df_indicadores, on='numero do projeto', how='left')
    st.success("Dados unidos com sucesso!")

    df = clean_numeric_columns(df)

except Exception as e:
    st.error(f"Erro Crítico ao unir as planilhas: {e}")
    st.stop()

if df.empty:
    st.warning("O DataFrame final após a união está vazio. Verifique a compatibilidade dos IDs.")
    st.stop()

# --- Bloco de FILTROS (Lógica de Cascata) ---
with st.sidebar:
    st.markdown("---")
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
        else:
            st.sidebar.warning("Nenhum ano válido encontrado.")


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


    opcoes_regional = criar_opcoes_filtro(df_para_filtros, 'regional')
    regional_selecionado = st.selectbox('Regional', opcoes_regional, index=0)
    if regional_selecionado != "Selecione":
        df_para_filtros = df_para_filtros[
            df_para_filtros['regional'].astype(str).str.title() == regional_selecionado
            ]

    opcoes_estado = criar_opcoes_filtro(df_para_filtros, 'estado')
    estado_selecionado = st.selectbox('Estado', opcoes_estado, index=0)
    if estado_selecionado != "Selecione":
        df_para_filtros = df_para_filtros[
            df_para_filtros['estado'].astype(str).str.title() == estado_selecionado
            ]

    opcoes_municipio = criar_opcoes_filtro(df_para_filtros, 'município')
    municipio_selecionado = st.selectbox('Município', opcoes_municipio, index=0)
    if municipio_selecionado != "Selecione":
        df_para_filtros = df_para_filtros[
            df_para_filtros['município'].astype(str).str.title() == municipio_selecionado
            ]

    opcoes_negocio = criar_opcoes_filtro(df_para_filtros, 'negócio')
    negocio_selecionado = st.selectbox('Negócio', opcoes_negocio, index=0)
    if negocio_selecionado != "Selecione":
        df_para_filtros = df_para_filtros[
            df_para_filtros['negócio'].astype(str).str.title() == negocio_selecionado
            ]

    opcoes_unidade = criar_opcoes_filtro(df_para_filtros, 'unidade')
    unidade_selecionada = st.selectbox('Unidade', opcoes_unidade, index=0)
    if unidade_selecionada != "Selecione":
        df_para_filtros = df_para_filtros[
            df_para_filtros['unidade'].astype(str).str.title() == unidade_selecionada
            ]

    df_filtrado = df_para_filtros.copy()
# --- FIM DO BLOCO DE FILTROS ---


# --- LÓGICA DE EXIBIÇÃO ---
st.markdown("---")

if (ano_selecionado != 'Selecione' or
        regional_selecionado != 'Selecione' or
        estado_selecionado != 'Selecione' or
        municipio_selecionado != 'Selecione' or
        negocio_selecionado != 'Selecione' or
        unidade_selecionada != 'Selecione'):

    if not df_filtrado.empty:
        st.subheader('Análise de Metas')

        tipos_grafico = ['Resultado Ciclo', 'Resultado Previsto', 'Meta 100', 'Meta 300', 'Meta 500']
        colunas_soma = ['resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']
        valores_grafico = []

        for col in colunas_soma:
            if col in df_filtrado.columns:
                valores_grafico.append(df_filtrado[col].fillna(0).sum())
            else:
                valores_grafico.append(0)

        dados_grafico = pd.DataFrame({
            'Tipo': tipos_grafico,
            'Valor': valores_grafico
        })

        fig_horizontal = px.bar(
            dados_grafico,
            x='Valor',
            y='Tipo',
            orientation='h',
            text_auto=True,
            title='Comparação Total de Resultado e Metas',
            color='Tipo',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_horizontal, use_container_width=True)

        st.markdown('---')
        st.subheader('Dados Detalhados (Pós-Filtro)')
        st.dataframe(df_filtrado)

        st.markdown('---')
        st.subheader('Análise de Metas Batidas')

        colunas_meta_base = ['resultado ciclo', 'meta100', 'meta300', 'meta500']
        colunas_meta_existentes = [col for col in colunas_meta_base if col in df_filtrado.columns]

        if not colunas_meta_existentes or 'resultado ciclo' not in colunas_meta_existentes:
            st.warning(
                "Não foi possível analisar metas batidas. Colunas 'resultado ciclo' ou 'meta100/300/500' não encontradas.")
        else:
            df_com_metas = df_filtrado.dropna(subset=colunas_meta_existentes, how='all')

            filtro_metas = (df_com_metas['resultado ciclo'] >= df_com_metas.get('meta100', float('inf')))
            if 'meta300' in df_com_metas:
                filtro_metas = filtro_metas | (df_com_metas['resultado ciclo'] >= df_com_metas['meta300'])
            if 'meta500' in df_com_metas:
                filtro_metas = filtro_metas | (df_com_metas['resultado ciclo'] >= df_com_metas['meta500'])

            df_metas_batidas = df_com_metas[filtro_metas].copy()

            if not df_metas_batidas.empty:

                st.subheader('Resultado vs Metas por Indicador')

                if 'nome do indicador' in df_metas_batidas.columns:
                    df_metas_batidas['nome do indicador'] = df_metas_batidas['nome do indicador'].astype(
                        str).str.strip().str.title()
                    df_metas_batidas['nome do indicador'] = df_metas_batidas['nome do indicador'].replace('Evasão',
                                                                                                          '% de evasão')

                cols_agrupar = ['resultado ciclo', 'resultado previsto', 'meta100', 'meta300', 'meta500']
                cols_agrupar_existentes = [col for col in cols_agrupar if col in df_metas_batidas.columns]

                if 'nome do indicador' in df_metas_batidas.columns:
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
                        elif coluna == 'meta100':
                            temp_df['Tipo'] = 'Meta 100'
                        elif coluna == 'meta300':
                            temp_df['Tipo'] = 'Meta 300'
                        elif coluna == 'meta500':
                            temp_df['Tipo'] = 'Meta 500'
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
                        title='Comparação de Resultado e Metas por Indicador',
                        color_discrete_map={
                            'Resultado Ciclo': 'royalblue',
                            'Resultado Previsto': 'skyblue',
                            'Meta 100': 'lightgreen',
                            'Meta 300': 'salmon',
                            'Meta 500': 'gold'
                        }
                    )
                    st.plotly_chart(fig_detalhe, use_container_width=True)
                else:
                    st.warning("Coluna 'nome do indicador' não encontrada para gerar o gráfico detalhado.")

                contagem = {}
                if 'meta100' in df_metas_batidas:
                    contagem['Meta 100'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta100']).sum()
                if 'meta300' in df_metas_batidas:
                    contagem['Meta 300'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta300']).sum()
                if 'meta500' in df_metas_batidas:
                    contagem['Meta 500'] = (df_metas_batidas['resultado ciclo'] >= df_metas_batidas['meta500']).sum()

                df_contagem = pd.DataFrame(list(contagem.items()), columns=['Meta', 'Total'])

                if not df_contagem.empty:
                    st.subheader('Contagem de Metas Batidas')
                    fig = px.bar(
                        df_contagem,
                        x='Meta',
                        y='Total',
                        text_auto=True,
                        color='Meta',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.subheader('Lista de Registros que Bateram a Meta')

                colunas_exibicao = ['numero do projeto', 'nome do indicador', 'tipo de agregaçao',
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
        st.info("Nenhum dado encontrado para a sua seleção. Por favor, ajuste os filtros na barra lateral.")

else:
    st.info("Por favor, use os filtros na barra lateral para selecionar dados e exibir as visualizações.")