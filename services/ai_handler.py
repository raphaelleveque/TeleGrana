import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        # Pega a chave do seu .env
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no .env")
        
        genai.configure(api_key=api_key)
        # Usando gemini-2.0-flash que está disponível na API
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    async def parse_expense(self, text: str):
        prompt = f"""
        Você é um assistente financeiro pessoal. Extraia os dados da frase: "{text}"
        
        REGRAS DE CLASSIFICAÇÃO:
        - tags: Escolha APENAS uma: [Mercado, Viagem, Restaurante, Academia, Compras, Outros]
        - metodo_pagamento: Escolha APENAS uma: [Pix, Crédito, Débito, Caju]
        
        IMPORTANTE:
        - Se a frase mencionar "mercado", "supermercado", "compra no mercado", classifique como tag "Mercado"
        - Se mencionar método de pagamento, extraia corretamente (ex: "paguei no pix" = "Pix")
        - A descricao deve ser uma versão resumida e clara do gasto
        
        Retorne APENAS um JSON:
        {{
            "valor": float,
            "descricao": str,
            "tags": str,
            "metodo_pagamento": str
        }}
        Se não houver valor, retorne null.
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Remove blocos de código markdown se o modelo insistir em colocar
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            erro_str = str(e)
            # Erro de quota excedida
            if "429" in erro_str or "quota" in erro_str.lower() or "rate limit" in erro_str.lower():
                print(f"⚠️ Quota da API excedida. Aguarde alguns minutos e tente novamente.")
            else:
                print(f"Erro ao processar JSON da IA: {e}")
            return None