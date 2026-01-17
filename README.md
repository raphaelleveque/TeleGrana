# 💰 TeleGrana - Seu Assistente Financeiro Inteligente no Telegram

Transforme suas mensagens de texto em registros financeiros organizados e inteligentes diretamente em uma planilha do Google Sheets. O TeleGrana utiliza a inteligência artificial do Google Gemini para entender o que você escreve, gerenciar reembolsos e responder perguntas sobre sua saúde financeira.

---

## ✨ Funcionalidades Incríveis

- **Conversão de Linguagem Natural**: Diga apenas "Gastei 50 no mercado hoje no crédito" e o bot faz o resto.
- **Extração Inteligente**: Detecta automaticamente valor, descrição, categoria (tags), método de pagamento e datas.
- **Gestão de Reembolsos**: Processa reembolsos parciais ou totais, ajustando o custo líquido das despesas.
- **Consultas em Tempo Real**: Pergunte "Quanto eu gastei ontem?" ou "Quanto gastei na semana passada sem contar Caju?" e receba um resumo detalhado.
- **IA de Ponta (Gemini)**: Utiliza modelos de última geração com sistema de fallback (reserva) para garantir que você nunca fique sem resposta.
- **Segurança Total**: Travado para responder apenas ao seu ID de usuário, impedindo que outros acessem seus dados.

---

## 🚀 Guia de Configuração (Passo a Passo)

### 1. Preparando o Ambiente
Clone o repositório e crie seu ambiente virtual:

```bash
git clone https://github.com/seu-usuario/TeleGrana.git
cd TeleGrana

# Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Criando seu Bot no Telegram
1. No Telegram, procure pelo **[@BotFather](https://t.me/botfather)**.
2. Mande o comando `/newbot` e siga as instruções para dar nome e username ao bot.
3. Copie o **HTTP API Token** (será algo como `8472683292:AAGv...`).
4. Procure pelo **[@userinfobot](https://t.me/userinfobot)** e mande um "Oi" para descobrir seu **Numeric ID** (ex: `1373680652`).

### 3. Configurando a Inteligência Artificial (Gemini)
1. Acesse o **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Clique em **"Create API Key"**.
3. Copie a chave gerada.

### 4. Configurando o Google Sheets (Planilha)
1. Crie uma nova planilha no seu [Google Sheets](https://sheets.new).
2. Pegue o **ID da Planilha** na URL (é a parte longa entre `/d/` e `/edit`).
   - Ex: `https://docs.google.com/spreadsheets/d/ID_DA_PLANILHA/edit`
3. Vá ao [Google Cloud Console](https://console.cloud.google.com/):
   - Ative as APIs: **Google Drive API** e **Google Sheets API**.
   - Crie uma **Service Account** (Conta de Serviço) em "APIs e Serviços > Credenciais".
   - Clique na conta criada, vá em **Keys > Add Key > Create New Key (JSON)**.
   - O arquivo será baixado. Renomeie-o para `credentials.json` e coloque na pasta raiz do projeto.
4. **IMPORTANTE**: Abra sua planilha no navegador, clique em "Compartilhar" e adicione o email da sua Service Account (encontrado no `credentials.json`) como **Editor**.

### 5. Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto com o seguinte conteúdo:

```env
TELEGRAM_TOKEN=seu_token_do_botfather
GOOGLE_SHEET_ID=id_da_sua_planilha
MY_USER_ID=seu_id_numerico_do_telegram
GEMINI_API_KEY=sua_chave_do_gemini
```

---

## 🛠️ Como Usar

### Iniciando o Bot
Basta rodar:
```bash
python main.py
```
O bot irá configurar automaticamente os cabeçalhos na sua planilha se eles ainda não existirem.

### Exemplos de Comandos
- **Registrar Gasto**: "Gastei 45 reais no almoço hoje no crédito"
- **Registrar Ganho**: "Recebi 1000 reais de presente da minha mãe no Pix"
- **Registrar Reembolso**: "Recebi o reembolso de 350 reais da gasolina de ontem"
- **Consultas**: 
  - "Quanto eu gastei ontem?"
  - "Quanto gastei na semana passada sem contar o método Caju?"
  - "Quanto eu ganhei este mês?"

### Lógica de Cálculos
O bot trabalha com o conceito de **Gasto Líquido**:
> `Gasto Líquido = Valor Gasto + Valor Reembolsado`

Se você gastou R$ 100 e foi reembolsado em R$ 40, seu gasto real foi R$ 60. Se o reembolso for TOTAL, o gasto vira zero nos resumos.

---

## 📁 Estrutura do Projeto
- `main.py`: Inicia o bot.
- `bot/handlers.py`: Toda a lógica de conversa e captura de mensagens.
- `services/ai_handler.py`: Interface com o Google Gemini.
- `services/google_sheets.py`: Interface direta com a planilha.
- `services/transaction_service.py`: Lógica de negócio e cálculos financeiros.
- `utils/prompts.py`: Os "cérebros" da IA, onde as instruções para o Gemini estão guardadas.
