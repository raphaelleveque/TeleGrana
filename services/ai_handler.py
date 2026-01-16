import os
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from utils.prompts import (
    get_expense_classification_prompt,
    get_reimbursement_prompt,
    get_edit_intent_prompt,
    get_past_edit_prompt,
    get_tag_intent_prompt
)

load_dotenv()

class AIService:
    def __init__(self):
        # Pega a chave do seu .env
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no .env")
        
        genai.configure(api_key=api_key)
        # Usando gemini-3-flash-preview que está disponível na API
        self.model = genai.GenerativeModel('gemini-flash-latest')

    async def parse_expense(self, text: str, expense_tags: list, income_tags: list):
        prompt = get_expense_classification_prompt(text, expense_tags, income_tags)
        
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

    async def parse_reimbursement(self, text: str):
        """Detecta se a mensagem é sobre reembolso e extrai informações."""
        current_date = datetime.now().strftime('%d/%m/%Y')
        prompt = get_reimbursement_prompt(text, current_date)
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str or "quota" in erro_str.lower() or "rate limit" in erro_str.lower():
                print(f"⚠️ Quota da API excedida. Aguarde alguns minutos e tente novamente.")
            else:
                print(f"Erro ao processar JSON da IA: {e}")
            return None

    async def parse_edit_intent(self, text: str, all_tags: list, metodo_options: list):
        """
        Detecta se o usuário quer editar a última transação e extrai o campo e o novo valor.
        """
        prompt = get_edit_intent_prompt(text, all_tags, metodo_options)
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao processar JSON da IA para edição: {e}")
            return None

    async def parse_past_edit(self, text: str, all_tags: list, metodo_options: list):
        """
        Analisa se a mensagem é um pedido para editar uma transação passada.
        Extrai critérios de busca (para encontrar a transação) e os dados a serem alterados.
        """
        prompt = get_past_edit_prompt(text, all_tags, metodo_options)

        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao processar JSON de edição passada: {e}")
            return None

    async def parse_tag_intent(self, text: str):
        """
        Analisa se o usuário quer gerenciar tags (criar ou listar).
        """
        prompt = get_tag_intent_prompt(text)
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            return None