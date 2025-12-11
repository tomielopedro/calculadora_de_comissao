import streamlit as st
import pandas as pd
import plotly.express as px
from avec_api.avec import Avec
from avec_api.models import Servico
import os

# Nome do arquivo onde salvaremos os custos
ARQUIVO_DADOS = 'dados_custos.csv'

# Tenta pegar a autorização
try:
    authorization = st.secrets['authorization']
except:
    authorization = ""

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de Lucro",
    page_icon="💇‍♀️",
    layout="wide"
)

# --- SIDEBAR (NOVA SEÇÃO) ---
with st.sidebar:
    st.header("⚙️ Configurações Globais")
    st.info("Defina aqui os valores que se aplicam a todos os cálculos.")
    
    # Custo fixo agora fica aqui
    custo_fixo_global = st.number_input(
        "Custo Fixo Rateado (R$)", 
        min_value=0.0, 
        value=10.0, 
        step=1.0,
        help="Quanto custa para o salão (luz, água, aluguel) apenas para o cliente sentar na cadeira."
    )
    
    st.divider()
    st.caption("Desenvolvido para Gestão de Salões")

# --- Funções de Carregamento ---
@st.cache_data(ttl=3600)
def carregar_dados_avec():
    """Carrega dados frescos da API"""
    try:
        if not authorization:
            return []
        avec = Avec(authorization)
        raw_services = avec.rel_0033_all()
        return [Servico(**servico) for servico in raw_services]
    except Exception as e:
        st.error(f"Erro ao carregar dados da API: {e}")
        return []

def carregar_e_mesclar_dados():
    # 1. Carrega API
    dados_api = carregar_dados_avec()
    
    if dados_api:
        # Converte Pydantic para DataFrame
        df_api = pd.DataFrame([s.model_dump() for s in dados_api])
        
        # --- CORREÇÃO DO ERRO ---
        # Verifica se a coluna 'id' existe. Se não existir, criamos uma baseada no índice.
        if 'id' not in df_api.columns:
            # Tenta achar colunas similares comuns em APIs
            possible_ids = ['uuid', '_id', 'code', 'codigo']
            found_id = next((col for col in possible_ids if col in df_api.columns), None)
            
            if found_id:
                df_api['id'] = df_api[found_id] # Usa a coluna encontrada como ID
            else:
                # Se não tem nenhum ID, usa o índice ou o nome do serviço como ID temporário
                # Isso impede o crash e permite salvar os custos
                st.warning("Aviso: Campo 'id' não encontrado na API. Usando índice temporário.")
                df_api['id'] = df_api.index.astype(str)

        # Agora é seguro converter os tipos
        # Usamos um dicionário seguro: só converte o que realmente existe
        tipos_desejados = {
            "id": "string",
            "servico": "string",
            "tempo": "int64",
            "valor": "float64",
            "categoria": "string"
        }
        
        # Filtra apenas as colunas que realmente existem no DataFrame para evitar KeyError
        tipos_para_converter = {k: v for k, v in tipos_desejados.items() if k in df_api.columns}
        
        df_api = df_api.astype(tipos_para_converter)
        
    else:
        # DataFrame vazio estruturado
        df_api = pd.DataFrame(columns=["id", "servico", "tempo", "valor", "categoria"])

    # 2. Carrega CSV Local
    if os.path.exists(ARQUIVO_DADOS):
        try:
            df_csv = pd.read_csv(ARQUIVO_DADOS)
            
            # Garante que ID seja string para bater com a API
            if 'id' in df_csv.columns:
                df_csv['id'] = df_csv['id'].astype(str)
            
            cols_custo = ['id', 'custo_produto', 'custo_lavagem']
            cols_existentes = [c for c in cols_custo if c in df_csv.columns]
            df_custos = df_csv[cols_existentes]
        except Exception as e:
            st.warning(f"Arquivo de custos recriado por incompatibilidade. Erro: {e}")
            df_custos = pd.DataFrame(columns=['id', 'custo_produto', 'custo_lavagem'])
    else:
        df_custos = pd.DataFrame(columns=['id', 'custo_produto', 'custo_lavagem'])

    # 3. Mesclagem
    if not df_api.empty and not df_custos.empty and 'id' in df_custos.columns and 'id' in df_api.columns:
        df_final = pd.merge(df_api, df_custos, on='id', how='left')
    else:
        df_final = df_api.copy()

    # Preenchimento de valores nulos
    if 'custo_produto' not in df_final.columns:
        df_final['custo_produto'] = 0.0
    if 'custo_lavagem' not in df_final.columns:
        df_final['custo_lavagem'] = 0.0
        
    df_final['custo_produto'] = df_final['custo_produto'].fillna(0.0)
    df_final['custo_lavagem'] = df_final['custo_lavagem'].fillna(0.0)

    return df_final

# --- Inicialização ---
if 'df_servicos' not in st.session_state:
    st.session_state['df_servicos'] = carregar_e_mesclar_dados()

st.title("💇‍♀️ Calculadora de Rentabilidade por Procedimento")

# --- Seção 1: Tabela Editável ---
with st.expander("📝 Gerenciar Custos dos Serviços (Salvo Automaticamente)", expanded=True):
    st.info("Edite os custos variáveis específicos de cada serviço abaixo.")
    
    column_config = {
        "id": None,
        "servico": st.column_config.TextColumn("Serviço", disabled=True),
        "valor": st.column_config.NumberColumn("Preço (API)", format="R$ %.2f", disabled=True),
        "custo_produto": st.column_config.NumberColumn("Custo Produto (R$)", format="R$ %.2f", step=1.0),
        "custo_lavagem": st.column_config.NumberColumn("Custo Lavagem (R$)", format="R$ %.2f", step=1.0),
    }

    df_editado = st.data_editor(
        st.session_state['df_servicos'],
        use_container_width=True,
        column_config=column_config,
        column_order=["servico", "valor", "custo_produto", "custo_lavagem", "categoria"],
        key="editor_servicos"
    )

    if not df_editado.equals(st.session_state['df_servicos']):
        st.session_state['df_servicos'] = df_editado
        try:
            df_editado.to_csv(ARQUIVO_DADOS, index=False)
            st.toast("✅ Custos salvos com sucesso!", icon="💾")
        except Exception as e:
            st.error(f"Erro ao salvar arquivo: {e}")

st.divider()

# --- Seção 2: A Calculadora ---
col_config, col_grafico = st.columns([1, 1.5])

with col_config:
    st.subheader("🛠️ Simulação Financeira")
    
    lista_servicos = df_editado['servico'].unique().tolist()
    servico_selecionado = st.selectbox("Escolha um serviço base:", options=lista_servicos)
    
    if not df_editado.empty:
        linha_servico = df_editado[df_editado['servico'] == servico_selecionado].iloc[0]
        valor_padrao_venda = float(linha_servico['valor'])
        custo_padrao_produtos = float(linha_servico['custo_produto']) + float(linha_servico['custo_lavagem'])
    else:
        valor_padrao_venda = 0.0
        custo_padrao_produtos = 0.0

    with st.form("form_calculadora", height=400):
        valor_procedimento = st.number_input(
            "💰 Valor do Procedimento (R$)", 
            min_value=0.0, 
            value=valor_padrao_venda, 
            step=5.0
        )

        col1, col2 = st.columns(2)
        with col1:
            perc_comissao = st.number_input("Perc. Comissão (%)", min_value=0.0, max_value=100.0, value=30.0, step=1.0)
            perc_imposto = st.number_input("Impostos (%)", min_value=0.0, max_value=100.0, value=6.0, step=0.5)
        
        with col2:
            perc_cartao = st.number_input("Taxa Maquininha (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
            
            custo_produtos = st.number_input(
                "Custo Produtos + Lavagem (R$)", 
                min_value=0.0, 
                value=custo_padrao_produtos, 
                step=1.0,
                help="Soma automática das colunas 'Custo Produto' e 'Custo Lavagem' da tabela acima."
            )
            # REMOVIDO: O input de Custo Fixo saiu daqui
        
        submitted = st.form_submit_button("Calcular Lucro", type="primary")

# --- Lógica de Cálculo ---
faturamento_bruto = valor_procedimento
val_comissao = faturamento_bruto * (perc_comissao / 100)
val_imposto = faturamento_bruto * (perc_imposto / 100)
val_cartao = faturamento_bruto * (perc_cartao / 100)
total_custos_variaveis = val_comissao + val_imposto + val_cartao + custo_produtos

lucro_bruto = faturamento_bruto - total_custos_variaveis

# --- AQUI: Usamos a variável que veio da Sidebar ---
lucro_liquido = lucro_bruto - custo_fixo_global 

margem_lucro = (lucro_liquido / faturamento_bruto * 100) if faturamento_bruto > 0 else 0

with col_grafico:
    st.subheader("📊 Resultados Financeiros")
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor Final", f"R$ {faturamento_bruto:,.2f}")
    c2.metric("Comissão", f"R$ {val_comissao:,.2f}", f"{perc_comissao}%")
    delta_color = "normal" if lucro_liquido >= 0 else "inverse"
    c3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", f"{margem_lucro:.1f}%", delta_color=delta_color)

    st.markdown("##### 📝 Extrato Detalhado")
    tabela_md = f"""
    | Item | Valor (R$) | % do Total |
    | :--- | :--- | :--- |
    | **Faturamento** | **{faturamento_bruto:.2f}** | **100%** |
    | (-) Comissão | {val_comissao:.2f} | {perc_comissao}% |
    | (-) Impostos | {val_imposto:.2f} | {perc_imposto}% |
    | (-) Taxa Cartão | {val_cartao:.2f} | {perc_cartao}% |
    | (-) Custo Prod. + Lavagem | {custo_produtos:.2f} | {(custo_produtos/faturamento_bruto*100 if faturamento_bruto else 0):.1f}% |
    | (-) Custo Fixo (Global) | {custo_fixo_global:.2f} | {(custo_fixo_global/faturamento_bruto*100 if faturamento_bruto else 0):.1f}% |
    | **= Resultado** | **{lucro_liquido:.2f}** | **{margem_lucro:.1f}%** |
    """
    with st.container():
        st.markdown(tabela_md)
    st.divider()

    st.markdown("##### 📉 Visualização Gráfica")
    dados_grafico = {
        'Categoria': ['Comissão', 'Impostos', 'Taxa Cartão', 'Prod/Lavagem', 'Custo Fixo', 'Lucro Líquido'],
        # Usamos custo_fixo_global aqui também
        'Valor': [val_comissao, val_imposto, val_cartao, custo_produtos, custo_fixo_global, lucro_liquido]
    }
    df_grafico = pd.DataFrame(dados_grafico)
    colors = ['#EF553B' if (row['Categoria'] == 'Lucro Líquido' and row['Valor'] < 0) else '#636EFA' for index, row in df_grafico.iterrows()]
    fig = px.bar(df_grafico, x='Categoria', y='Valor', text_auto='.2f')
    fig.update_traces(texttemplate='R$ %{y:.2f}', textposition='outside', marker_color=colors)
    fig.update_layout(yaxis_title=None, xaxis_title=None, margin=dict(l=0, r=0, t=20, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)