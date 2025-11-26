import pandas as pd
import requests
from bs4 import BeautifulSoup
from googlesearch import search  # Para fins didáticos. Em prod, usar SerpApi.
import openai
import time
from urllib.parse import urlparse

# Configurações (Simuladas)
OPENAI_API_KEY = "sk-..." 
openai.api_key = OPENAI_API_KEY

class CorporateScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def search_google(self, query, num_results=3):
        """Busca URLs no Google."""
        try:
            # Em produção, substitua por request para SerpApi ou Google Custom Search
            results = list(search(query, num_results=num_results, lang="pt"))
            return results
        except Exception as e:
            print(f"Erro na busca: {e}")
            return []

    def get_page_content(self, url):
        """Baixa o HTML e extrai texto limpo."""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove scripts e estilos
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator=' ')
                # Limpeza básica
                lines = (line.strip() for line in text.splitlines())
                clean_text = ' '.join(line for line in lines if line)
                return clean_text[:8000] # Limita caracteres para não estourar token da LLM
        except:
            return None
        return None

    def find_official_site(self, company_name):
        """Descobre o site oficial."""
        results = self.search_google(f"{company_name} site oficial")
        # Heurística simples: o primeiro resultado geralmente é o oficial
        # Em prod, ignorar linkedin/facebook/glassdoor aqui
        for url in results:
            if "linkedin" not in url and "glassdoor" not in url and "instagram" not in url:
                return url
        return None

    def analyze_text_with_llm(self, text_chunk):
        """Usa IA para extrair MVV do texto bruto."""
        prompt = f"""
        Analise o texto abaixo de um site corporativo.
        Extraia estritamente: Missão, Visão e Valores.
        Se não encontrar explicitamente, retorne "null".
        Retorne em formato JSON: {{ "missao": "...", "visao": "...", "valores": "..." }}
        
        Texto:
        {text_chunk}
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini", # Modelo rápido e barato
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return response.choices[0].message.content
        except:
            return '{"missao": null, "visao": null, "valores": null}'

    def process_company(self, company_name):
        data = {
            "nome_empresa": company_name,
            "site_oficial": None,
            "status": "Não encontrado",
            "missão": None, "link_missão": None,
            "valores": None, "link_valores": None,
            "visão": None, "link_visao": None
        }

        # 1. Descoberta
        official_url = self.find_official_site(company_name)
        data["site_oficial"] = official_url

        found_flags = {"missao": False, "visao": False, "valores": False}
        sources_official = {"missao": False, "visao": False, "valores": False}

        # 2. Extração Primária (Site Oficial)
        if official_url:
            # Tenta Home e Páginas chave (Sobre, Institucional)
            # Simplificação: Vamos olhar apenas a Home e tentar achar link "Sobre"
            # (Em prod: crawler recursivo de 1 nível)
            content = self.get_page_content(official_url)
            if content:
                import json
                extracted = json.loads(self.analyze_text_with_llm(content))
                
                for key in ["missao", "visao", "valores"]:
                    if extracted.get(key) and extracted[key] != "null":
                        data[key] = extracted[key]
                        data[f"link_{key}"] = official_url # Link aproximado
                        found_flags[key] = True
                        sources_official[key] = True

        # 3. Fallback (Se faltar algo)
        missing_keys = [k for k, found in found_flags.items() if not found]
        
        if missing_keys:
            for key in missing_keys:
                # Busca específica: "Empresa X missão"
                query = f"{company_name} {key}"
                fallback_urls = self.search_google(query, num_results=2)
                
                for url in fallback_urls:
                    content = self.get_page_content(url)
                    if content:
                        import json
                        extracted = json.loads(self.analyze_text_with_llm(content))
                        if extracted.get(key) and extracted[key] != "null":
                            data[key] = extracted[key] # Mapeia nome correto
                            data[f"link_{key}"] = url
                            found_flags[key] = True
                            # Verifica se o fallback caiu no domínio oficial ou externo
                            if official_url and urlparse(url).netloc == urlparse(official_url).netloc:
                                sources_official[key] = True
                            else:
                                sources_official[key] = False
                            break # Achou, para de buscar fallback para este item

        # 4. Lógica de Status
        has_all = all(found_flags.values())
        has_any = any(found_flags.values())
        is_all_official = all(sources_official[k] for k in sources_official if found_flags[k])
        is_all_unofficial = all(not sources_official[k] for k in sources_official if found_flags[k])

        if has_all and is_all_official:
            data["status"] = "Completo"
        elif not has_any:
            data["status"] = "Não encontrado"
        elif has_any and is_all_unofficial:
            data["status"] = "Não-oficial"
        else:
            # Caso misto ou faltando algum item (Parcial)
            data["status"] = "Parcial"

        return data

# Exemplo de Execução
if __name__ == "__main__":
    # Simulação de Input
    empresas = ["Petrobras", "Padaria do Zé (Fictícia)"]
    scraper = CorporateScraper()
    
    results = []
    for emp in empresas:
        print(f"Processando: {emp}...")
        results.append(scraper.process_company(emp))
        time.sleep(2) # Respeito às APIs
    
    df = pd.DataFrame(results)
    print(df)
    # df.to_excel("resultado_empresas.xlsx", index=False)