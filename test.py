import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
    print('=== MODELOS TENTADOS E ERROS ===\n')
    
    modelos_para_testar = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-pro',
        'gemini-1.5-pro',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-3-flash-preview'
    ]
    
    for modelo in modelos_para_testar:
        try:
            m = genai.GenerativeModel(modelo)
            # Tenta gerar algo pequeno para testar
            response = m.generate_content('teste')
            print(f'✅ {modelo} - FUNCIONOU')
        except Exception as e:
            erro = str(e)
            if '404' in erro or 'not found' in erro.lower():
                print(f'❌ {modelo} - ERRO 404 (modelo não encontrado)')
            elif '429' in erro or 'quota' in erro.lower():
                print(f'⚠️  {modelo} - QUOTA EXCEDIDA (mas modelo existe)')
            else:
                print(f'❌ {modelo} - ERRO: {erro[:80]}')
else:
    print('❌ GEMINI_API_KEY não encontrada')