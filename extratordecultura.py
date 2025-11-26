import streamlit as st
import pandas as pd
# Importar a classe CorporateScraper definida acima

st.set_page_config(page_title="Extrator Corporativo IA", layout="wide")

st.title("🕵️‍♂️ Extrator de Missão, Visão e Valores")
st.markdown("Faça upload de uma lista de empresas e a IA buscará os dados estratégicos automaticamente.")

uploaded_file = st.file_uploader("Escolha um arquivo Excel/CSV", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Leitura do arquivo
    try:
        df_input = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        if "Nome da Empresa" not in df_input.columns:
            st.error("O arquivo deve conter uma coluna chamada 'Nome da Empresa'.")
        else:
            empresas = df_input["Nome da Empresa"].tolist()
            st.info(f"{len(empresas)} empresas identificadas.")

            if st.button("Iniciar Processamento"):
                scraper = CorporateScraper()
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, empresa in enumerate(empresas):
                    status_text.text(f"Processando: {empresa}...")
                    try:
                        data = scraper.process_company(empresa)
                        results.append(data)
                    except Exception as e:
                        st.error(f"Erro ao processar {empresa}: {e}")
                    
                    # Atualiza barra
                    progress_bar.progress((i + 1) / len(empresas))

                df_final = pd.DataFrame(results)
                
                st.success("Processamento concluído!")
                st.dataframe(df_final)

                # Botão de Download
                # Converter para Excel em memória
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False)
                processed_data = output.getvalue()

                st.download_button(
                    label="📥 Baixar Excel Completo",
                    data=processed_data,
                    file_name="dados_corporativos_completos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")