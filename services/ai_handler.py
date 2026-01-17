import os
import json
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from utils.prompts import (
    get_expense_classification_prompt,
    get_reimbursement_prompt,
    get_past_edit_prompt,
    get_tag_intent_prompt,
    get_query_intent_prompt,
    get_intent_router_prompt
)

load_dotenv()

class AIService:
    def __init__(self):
        # Pega a chave do seu .env
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no .env")
        
        # Inicializa o novo cliente do SDK v1
        self.client = genai.Client(api_key=api_key)
        
        # Lista de modelos para fallback em caso de 429
        # Priorizamos os verificados como ativos no teste
        self.models_to_try = [
            'gemini-2.5-flash-lite',      # 1º: O rei do custo-benefício (ultra barato e preciso)
            'gemini-3-flash-preview',     # 2º: O mais moderno e rápido (melhor inteligência)
            'gemini-2.5-flash',           # 3º: Mais robusto que o Lite, caso a IA precise de mais "raciocínio"
            'gemini-flash-latest',        # 4º: Versão estável (fallback seguro se os novos oscilarem)
            'gemini-2.0-flash',           # 5º: Tecnologia madura, excelente estabilidade
            'gemini-2.0-flash-lite'       # 6º: Opção de baixo custo da geração anterior
        ]

    async def _generate_content_with_fallback(self, prompt):
        """Tenta gerar conteúdo com fallback usando o novo SDK v1."""
        last_error = None
        for model_name in self.models_to_try:
            try:
                # No novo SDK, usamos o client.models.generate_content
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "max_output_tokens": 500,
                        "temperature": 0.1
                    }
                )
                return response.text
            except Exception as e:
                last_error = e
                erro_str = str(e).lower()
                if "429" in erro_str or "quota" in erro_str:
                    print(f"⚠️ Quota excedida para o modelo {model_name}. Tentando próximo...")
                    continue
                else:
                    # Erros que não são de quota a gente interrompe
                    print(f"❌ Erro no modelo {model_name}: {e}")
                    break
        
        # Se chegou aqui, todos falharam ou houve um erro crítico
        if last_error:
            print(f"🚨 Todos os modelos falharam. Último erro: {last_error}")
        return None

    async def detect_intent(self, text: str):
        """Identifica a intenção principal do usuário (Roteamento)."""
        prompt = get_intent_router_prompt(text)
        try:
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return {"intent": "other"}
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao detectar intenção: {e}")
            return {"intent": "other"}

    async def parse_expense(self, text: str, expense_tags: list, income_tags: list):
        current_date = datetime.now().strftime('%d/%m/%Y')
        prompt = get_expense_classification_prompt(text, expense_tags, income_tags, current_date)
        
        try:
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return None
            
            # Remove blocos de código markdown se o modelo insistir em colocar
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao processar JSON da IA: {e}")
            return None

    async def parse_reimbursement(self, text: str):
        """Detecta se a mensagem é sobre reembolso e extrai informações."""
        current_date = datetime.now().strftime('%d/%m/%Y')
        prompt = get_reimbursement_prompt(text, current_date)
        
        try:
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return None
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao processar JSON da IA: {e}")
            return None

    async def parse_past_edit(self, text: str, all_tags: list, metodo_options: list):
        """
        Analisa se a mensagem é um pedido para editar uma transação passada.
        Extrai critérios de busca (para encontrar a transação) e os dados a serem alterados.
        """
        prompt = get_past_edit_prompt(text, all_tags, metodo_options)

        try:
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return None
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
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
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return None
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            return None

    async def parse_query_intent(self, text: str, metodo_options: list):
        """
        Detecta se o usuário está fazendo uma pergunta sobre gastos/ganhos.
        """
        current_date = datetime.now().strftime('%d/%m/%Y')
        prompt = get_query_intent_prompt(text, current_date, metodo_options)
        try:
            response_text = await self._generate_content_with_fallback(prompt)
            if not response_text:
                return None
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Erro ao processar JSON de consulta: {e}")
            return None