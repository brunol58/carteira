import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class PortfolioRebalancer:
    def __init__(self, df, pesos, aporte_mensal=2500):
        self.aporte_mensal = aporte_mensal
        self.pesos = pesos
        self.raw_df = df.copy()
        self.initialize_data()
        self.calculate_metrics()

    def initialize_data(self):
        rename_map = {
            'ATIVO': 'Subcategoria',
            'PATRIMÔNIO ATUAL': 'Patrimônio Atual',
            'RENTABILIDADE': 'Rentabilidade',
            'RESULTADO': 'Resultado',
            'PREÇO MÉDIO': 'Preco Medio',
            'PREÇO ATUAL': 'Preco Atual',
            'QUANTIDADE': 'Quantidade'
        }
        self.raw_df = self.raw_df.rename(
            columns={k: v for k, v in rename_map.items() if k in self.raw_df.columns}
        )

        base = pd.DataFrame({
            'Categoria': [
                'Renda Fixa', 'Renda Fixa',
                'Ações', 'Ações', 'Ações', 'Ações',
                'Exterior', 'Exterior'
            ],
            'Subcategoria': list(self.pesos.keys()),
            '% Alvo Subcat': list(self.pesos.values())
        })

        self.data = base.merge(self.raw_df, on='Subcategoria', how='left')
        self.data['Patrimônio Atual'] = self.data['Patrimônio Atual'].fillna(0)

    def calculate_metrics(self):
        total = self.data['Patrimônio Atual'].sum()
        self.data['% Atual'] = self.data['Patrimônio Atual'] / total
        self.data['Gap'] = ((total + self.aporte_mensal) * self.data['% Alvo Subcat'] -
                            self.data['Patrimônio Atual'])

        positivos = self.data[self.data['Gap'] > 0]['Gap']
        if not positivos.empty:
            soma = positivos.sum()
            self.data['Aporte'] = self.data.apply(
                lambda r: r['Gap'] / soma * self.aporte_mensal if r['Gap'] > 0 else 0,
                axis=1
            )
        else:
            self.data['Aporte'] = 0

    # =========================
    # MÉTRICAS REAIS
    # =========================
    def resumo(self):
        cols = st.columns(5)
        cols[0].metric("Aporte Mensal", f"R$ {self.aporte_mensal:,.2f}")
        cols[1].metric("Patrimônio Atual", f"R$ {self.data['Patrimônio Atual'].sum():,.2f}")

        if 'Resultado' in self.data:
            cols[2].metric("Resultado Total", f"R$ {self.data['Resultado'].sum():,.2f}")

        if 'Rentabilidade' in self.data:
            rent_med = (self.data['Rentabilidade'] * self.data['% Atual']).sum()
            cols[3].metric("Rentabilidade Média", f"{rent_med:.2%}")

        top3 = self.data.sort_values('Patrimônio Atual', ascending=False).head(3)
        cols[4].metric("Top 3 Concentração", f"{top3['% Atual'].sum():.2%}")

    # =========================
    # GRÁFICOS
    # =========================
    def graficos(self):
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                "Distribuição da Carteira",
                "Aporte por Ativo",
                "Resultado por Ativo (R$)",
                "Rentabilidade x Peso"
            ],
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )

        fig.add_trace(
            go.Pie(labels=self.data['Subcategoria'], values=self.data['Patrimônio Atual'], hole=0.45),
            1, 1
        )
        fig.add_trace(
            go.Bar(x=self.data['Subcategoria'], y=self.data['Aporte'], marker_color=self.data['Aporte']),
            1, 2
        )
        if 'Resultado' in self.data:
            fig.add_trace(
                go.Bar(x=self.data['Subcategoria'], y=self.data['Resultado'], marker_color=self.data['Resultado']),
                2, 1
            )
        if 'Rentabilidade' in self.data:
            fig.add_trace(
                go.Scatter(
                    x=self.data['% Atual'],
                    y=self.data['Rentabilidade'],
                    mode='markers+text',
                    text=self.data['Subcategoria'],
                    textposition="top center"
                ),
                2, 2
            )

        fig.update_layout(height=850, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    def tabela(self):
        st.dataframe(
            self.data.style
                .background_gradient(subset=['Aporte'], cmap='Greens')
                .background_gradient(subset=['Gap'], cmap='Reds')
                .background_gradient(subset=['Rentabilidade'], cmap='Blues', axis=0)
                if 'Rentabilidade' in self.data else self.data,
            use_container_width=True,
            height=420
        )


# =========================
# APP
# =========================
st.set_page_config("Rebalanceamento Profissional", layout="wide")
st.title("📊 Rebalanceamento com Performance Real")

with st.sidebar:
    arquivo = st.file_uploader("Planilha da Carteira", type="xlsx")
    aporte = st.number_input("Aporte Mensal (R$)", value=2500.0, step=250.0)

    st.markdown("### Pesos (% Alvo)")
    pesos_raw = {
        'B5P211': st.number_input("B5P211", 0.0, 1.0, 0.30),
        'IB5M11': st.number_input("IB5M11", 0.0, 1.0, 0.10),
        'DIVO11': st.number_input("DIVO11", 0.0, 1.0, 0.075),
        'charles-river-fia': st.number_input("Charles River", 0.0, 1.0, 0.075),
        'guepardo-institucional-fic-fia': st.number_input("Guepardo", 0.0, 1.0, 0.075),
        'real-investor-fia-bdr-nivel-i': st.number_input("Real Investor", 0.0, 1.0, 0.075),
        'IVVB11': st.number_input("IVVB11", 0.0, 1.0, 0.15),
        'WRLD11': st.number_input("WRLD11", 0.0, 1.0, 0.15),
    }
    soma = sum(pesos_raw.values())
    pesos = {k: v / soma for k, v in pesos_raw.items()}

if arquivo:
    df0 = pd.read_excel(arquivo, sheet_name=0)
    df1 = pd.read_excel(arquivo, sheet_name=1)
    df = pd.concat([df0, df1], ignore_index=True)

    reb = PortfolioRebalancer(df, pesos, aporte)
    reb.resumo()

    st.markdown("## Visão Analítica")
    reb.graficos()

    st.markdown("## Detalhamento")
    reb.tabela()
else:
    st.info("Envie a planilha para iniciar a análise.")
