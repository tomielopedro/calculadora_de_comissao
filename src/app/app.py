import streamlit as st
import pandas as pd
import plotly.express as px
from avec_api.avec import Avec
from avec_api.models import Servico
import os 
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de Lucro - Salão de Beleza",
    page_icon="💇‍♀️",
    layout="wide"
)

# --- Funções de Carregamento ---
@st.cache_data(ttl=3600)
def carregar_dados_avec():
    try:
        authorization = os.getenv('AUTHORIZATION_RT')
        if not authorization:
            return []
        avec = Avec(authorization)
        raw_services = avec.rel_0033_all()
        return [Servico(**servico) for servico in raw_services]
    except Exception as e:
        st.error(f"Erro ao carregar dados da API: {e}")
        return []

# --- Inicialização do Estado ---
if 'servicos' not in st.session_state:
    with st.spinner('Carregando serviços da Avec...'):
        st.session_state['servicos'] = carregar_dados_avec()

# --- Processamento do DataFrame ---
if st.session_state['servicos']:
    df = pd.DataFrame([s.model_dump() for s in st.session_state['servicos']])
    df = df.astype({
        "servico": "string",
        "tempo": "int64",
        "valor": "float64",
        "categoria": "string"
    })
else:
    df = pd.DataFrame(columns=["servico", "tempo", "valor", "categoria"])

st.title("💇‍♀️ Calculadora de Rentabilidade por Procedimento")

# --- Seção 1: Visualização dos Dados ---
with st.expander("Ver Tabela de Serviços Completa", expanded=False):
    st.data_editor(df, use_container_width=True)

st.divider()

# --- Seção 2: A Calculadora ---

col_config, col_grafico = st.columns([1, 1.5])

with col_config:
    st.subheader("🛠️ Simulação Financeira")
    
    # Seleção do serviço
    lista_servicos = df['servico'].unique().tolist()
    servico_selecionado = st.selectbox("Escolha um serviço base:", options=lista_servicos)
    
    # Busca dados do serviço para default
    dados_servico = df[df['servico'] == servico_selecionado].iloc[0] if not df.empty else None
    valor_padrao = float(dados_servico['valor']) if dados_servico is not None else 0.0

    # --- INPUTS ---
    with st.form("form_calculadora"):
        valor_procedimento = st.number_input(
            "💰 Valor do Procedimento (R$)", 
            min_value=0.0, 
            value=valor_padrao, 
            step=5.0
        )

        col1, col2 = st.columns(2)
        with col1:
            perc_comissao = st.number_input("Perc. Comissão (%)", min_value=0.0, max_value=100.0, value=30.0, step=1.0)
            perc_imposto = st.number_input("Impostos (%)", min_value=0.0, max_value=100.0, value=6.0, step=0.5)
            perc_cartao = st.number_input("Taxa Maquininha (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
        
        with col2:
            custo_produtos = st.number_input("Custo Produtos (R$)", min_value=0.0, value=15.0, step=1.0)
            custo_fixo = st.number_input("Custo Fixo Rateado (R$)", min_value=0.0, value=10.0, step=1.0)
        
        submitted = st.form_submit_button("Calcular Lucro", type="primary")

# --- Lógica de Cálculo ---
faturamento_bruto = valor_procedimento

val_comissao = faturamento_bruto * (perc_comissao / 100)
val_imposto = faturamento_bruto * (perc_imposto / 100)
val_cartao = faturamento_bruto * (perc_cartao / 100)
total_custos_variaveis = val_comissao + val_imposto + val_cartao + custo_produtos

lucro_bruto = faturamento_bruto - total_custos_variaveis
lucro_liquido = lucro_bruto - custo_fixo

margem_lucro = (lucro_liquido / faturamento_bruto * 100) if faturamento_bruto > 0 else 0

# --- Exibição dos Resultados (Coluna da Direita) ---
with col_grafico:
    st.subheader("📊 Resultados Financeiros")

    # 1. Métricas Principais (Topo)
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor Final", f"R$ {faturamento_bruto:,.2f}")
    c2.metric("Comissão", f"R$ {val_comissao:,.2f}", f"{perc_comissao}%")
    
    delta_color = "normal" if lucro_liquido >= 0 else "inverse"
    c3.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}", f"{margem_lucro:.1f}%", delta_color=delta_color)

  

    # 2. Tabela Detalhada (Movida para cima)
    st.markdown("##### 📝 Extrato Detalhado")
    
    tabela_md = f"""
    | Item | Valor (R$) | % do Total |
    | :--- | :--- | :--- |
    | **Faturamento** | **{faturamento_bruto:.2f}** | **100%** |
    | (-) Comissão | {val_comissao:.2f} | {perc_comissao}% |
    | (-) Impostos | {val_imposto:.2f} | {perc_imposto}% |
    | (-) Taxa Cartão | {val_cartao:.2f} | {perc_cartao}% |
    | (-) Custo Produtos | {custo_produtos:.2f} | {(custo_produtos/faturamento_bruto*100 if faturamento_bruto else 0):.1f}% |
    | (-) Custo Fixo | {custo_fixo:.2f} | {(custo_fixo/faturamento_bruto*100 if faturamento_bruto else 0):.1f}% |
    | **= Resultado** | **{lucro_liquido:.2f}** | **{margem_lucro:.1f}%** |
    """
    
    with st.container():
        st.markdown(tabela_md)

    st.divider()

    # 3. Gráfico de Barras (Movido para baixo)
st.markdown("##### 📉 Visualização Gráfica")

dados_grafico = {
    'Categoria': ['Comissão', 'Impostos', 'Taxa Cartão', 'Produtos', 'Custo Fixo', 'Lucro Líquido'],
    'Valor': [val_comissao, val_imposto, val_cartao, custo_produtos, custo_fixo, lucro_liquido]
}
df_grafico = pd.DataFrame(dados_grafico)
colors = ['#EF553B' if (row['Categoria'] == 'Lucro Líquido' and row['Valor'] < 0) else '#636EFA' for index, row in df_grafico.iterrows()]
fig = px.bar(
    df_grafico, 
    x='Categoria', 
    y='Valor',
    text_auto='.2f',
)

fig.update_traces(
    texttemplate='R$ %{y:.2f}', 
    textposition='outside',
    marker_color=colors
)
# Remove títulos dos eixos para limpar o visual
fig.update_layout(
    yaxis_title=None, 
    xaxis_title=None,
    margin=dict(l=0, r=0, t=20, b=0), # Remove margens excessivas
    height=300 # Ajusta altura para caber melhor após a tabela
)

st.plotly_chart(fig, use_container_width=True)